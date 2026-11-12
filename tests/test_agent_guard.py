import importlib.util
import json
import shlex
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location("agent_guard", Path(__file__).resolve().parents[1] / "scripts/agent-guard.py")
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)

PROVEN = """## Summary

Fix.

## Screenshots

![Swap settled](https://github.com/org/repo/blob/pr-assets/fix/after.png?raw=true)

## Verified in browser

- Swap settles on the preview.
<!-- verification-job: 7d9d27f1-a61f-430a-9ad3-f7190c6ada68 -->

## Merge Danger
"""
JOB = "7d9d27f1-a61f-430a-9ad3-f7190c6ada68"

# The direct full suite and typecheck that overlapped a queued browser run before the 2026-10-26 overload and restart.
FULL_SUITE = "HEADLESS=true bun run test --run > /tmp/nightly-921-unit.log 2>&1"
FULL_TYPECHECK = "NODE_OPTIONS=--max-old-space-size=4096 bun run typecheck 2>&1 | tail -8"
FOCUSED_RERUN = ("HEADLESS=true bun run test --run --maxWorkers=2 --minWorkers=1 src/features/tradingSigner/index.test.ts "
                 "src/shared/utils/compareNullableNumber.test.ts 2>&1 | head -20")

# The unqueued run that preceded the Mac mini running out of memory and rebooting.
CRASH_RUN = "bun run test:e2e:local accountPasskeys --reporter=line > /tmp/pr804-runs/baseline-7dc603bee.log"
FAKE_GH = """#!/bin/sh
printf '%s\\n' "$*" >> "$FAKE_GH_LOG"
case "$FAKE_GH_MODE" in
  hang) exec sleep 5 ;;
  fail) echo "GraphQL: Could not resolve to a PullRequest with the number of 803." >&2; exit 1 ;;
esac
printf '%s' "$FAKE_GH_CHECKS"
"""

# Body of #784, merged-ready while swaps were broken in the preview.
UNPROVEN = """Stacked on #768.

On success, the status card collapses its steps into "Swap complete".

- Adds `summarizeOnSuccess` to `ProgressSteps`.
"""


class AgentGuardTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.e2e = self.repo("e2e", "git@github.com:silent-shipper/metamask-e2e.git")
        self.app = self.repo("app", "https://github.com/defuse-protocol/defuse-frontend-monorepos.git")
        (self.app / "apps/defuse-near").mkdir(parents=True)
        self.base = self.head = None

    def repo(self, name, url):
        path = self.root / name
        path.mkdir()
        subprocess.run(["git", "init", "-q", str(path)], check=True)
        subprocess.run(["git", "-C", str(path), "remote", "add", "origin", url], check=True)
        return path

    def decide(self, command, project):
        with patch.dict(os.environ, {"CLAUDE_PROJECT_DIR": str(project)}):
            return guard.decide({"tool_name": "Bash", "cwd": str(project), "tool_input": {"command": command}})

    def test_push_to_another_repo_asks(self):
        result = self.decide(f"cd {self.app} && git push origin HEAD", self.e2e)
        self.assertEqual(result[0], "ask")
        self.assertIn("defuse-protocol/defuse-frontend-monorepos", result[1])
        self.assertEqual(self.decide(f"git -C {self.app} push", self.e2e)[0], "ask")
        self.assertEqual(self.decide("gh pr merge 5 --repo defuse-protocol/defuse-frontend-monorepos", self.e2e)[0], "ask")

    def test_push_to_session_repo_is_allowed(self):
        self.assertIsNone(self.decide("git push origin main", self.e2e))

    def commit_as(self, repo, email):
        env = {**os.environ, "GIT_AUTHOR_NAME": "a", "GIT_AUTHOR_EMAIL": email,
               "GIT_COMMITTER_NAME": "a", "GIT_COMMITTER_EMAIL": email}
        subprocess.run(["git", "-C", str(repo), "commit", "-q", "--allow-empty", "-m", "x"], check=True, env=env)
        return subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()

    def test_commit_with_the_conflict_resolver_identity_is_denied(self):
        # The repo-local identity that made Vercel reject preview deployments on two PRs.
        subprocess.run(["git", "-C", str(self.app), "config", "user.email", "conflict-resolver@localhost"], check=True)
        result = self.decide("git commit -m 'fix: thing'", self.app)
        self.assertEqual(result[0], "deny")
        self.assertIn("git config --local --unset user.email", result[1])
        self.assertEqual(self.decide(f"git -C {self.app} commit -m x", self.e2e)[0], "deny")
        self.assertEqual(self.decide("git commit -m x", self.app)[0], "deny")

    def test_commit_with_a_host_derived_email_is_denied(self):
        subprocess.run(["git", "-C", str(self.e2e), "config", "user.email", "surge@Surges-Mac-Mini.local"], check=True)
        self.assertEqual(self.decide("git commit -m x", self.e2e)[0], "deny")

    def test_commit_with_a_real_or_per_command_identity_is_allowed(self):
        subprocess.run(["git", "-C", str(self.app), "config", "user.email", "1+dev@users.noreply.github.com"], check=True)
        self.assertIsNone(self.decide("git commit -m x", self.app))
        subprocess.run(["git", "-C", str(self.e2e), "config", "user.email", "conflict-resolver@localhost"], check=True)
        self.assertIsNone(self.decide("git -c user.email=bot@users.noreply.github.com commit -m x", self.e2e))
        self.assertIsNone(self.decide("GIT_AUTHOR_EMAIL=bot@users.noreply.github.com git commit -m x", self.e2e))
        self.assertIsNone(self.decide("git log --grep commit", self.e2e))

    def test_push_with_an_unpushed_local_identity_commit_is_denied(self):
        self.commit_as(self.e2e, "1+dev@users.noreply.github.com")
        bad = self.commit_as(self.e2e, "conflict-resolver@localhost")
        result = self.decide("git push origin HEAD", self.e2e)
        self.assertEqual(result[0], "deny")
        self.assertIn(bad[:7], result[1])
        self.assertIn("--reset-author", result[1])

    def test_push_of_clean_or_already_pushed_commits_is_allowed(self):
        bad = self.commit_as(self.e2e, "conflict-resolver@localhost")
        subprocess.run(["git", "-C", str(self.e2e), "update-ref", "refs/remotes/origin/main", bad], check=True)
        self.commit_as(self.e2e, "1+dev@users.noreply.github.com")
        self.assertIsNone(self.decide("git push origin HEAD", self.e2e))

    def test_pr_without_evidence_is_denied(self):
        body = self.root / "body.md"
        body.write_text(UNPROVEN)
        result = self.decide(f"gh pr edit 784 --body-file {body}", self.app)
        self.assertEqual(result[0], "deny")
        self.assertIn("## Verified in browser", result[1])

    def test_unfilled_template_is_denied(self):
        body = PROVEN.replace("- Swap settles on the preview.", "- <one behavior checked in a real browser>")
        self.assertIn("placeholder", self.decide("gh pr create --body " + shlex.quote(body), self.app)[1])

    def test_empty_browser_section_is_denied(self):
        body = PROVEN.replace("- Swap settles on the preview.\n", "")
        self.assertIn("no bullet", self.decide("gh pr create --body " + shlex.quote(body), self.app)[1])

    def commit(self, message):
        subprocess.run(["git", "-C", str(self.app), "-c", "user.name=t", "-c", "user.email=t@example.invalid",
                        "commit", "-q", "--allow-empty", "-m", message], check=True)
        return subprocess.run(["git", "-C", str(self.app), "rev-parse", "HEAD"], capture_output=True, text=True,
                              check=True).stdout.strip()

    def coverage(self, not_exercised=(), base=None, features=()):
        """A PR branch one commit past origin/main, with the receipt `coverage --base origin/main` writes for its head."""
        if not self.base:
            self.base = self.commit("base")
            subprocess.run(["git", "-C", str(self.app), "update-ref", "refs/remotes/origin/main", self.base], check=True)
            self.head = self.commit("feature")
        receipt = self.app / ".git/near-verify/coverage" / self.head / "0123456789abcdef.json"
        receipt.parent.mkdir(parents=True, exist_ok=True)
        app = str(self.app / "apps/defuse-near")
        receipt.write_text(json.dumps({"head": self.head, "app": app, "base": base or self.base,
                                       "status": "not-exercised" if not_exercised or features else "exercised",
                                       "files": [{"path": "src/swap.tsx", "exercised": [{"testId": "swap-submit", "jobs": [JOB]}],
                                                  "notExercised": list(not_exercised), "waived": []}],
                                       "features": {"changed": [], "withoutPassingRun": list(features), "waived": []}}))
        return receipt

    def receipts(self, command, accepted):
        if not self.base:
            self.coverage()
        calls = []

        def queue(args, cwd):
            calls.append(args)
            return {"cwd": str(self.app / "apps/defuse-near")} if args[0] == "inspect" else accepted

        self.fake_gh()
        env = {"PATH": f"{self.root / 'bin'}:{os.environ['PATH']}", "FAKE_GH_LOG": str(self.root / "gh.log"),
               "FAKE_GH_MODE": "", "FAKE_GH_CHECKS": json.dumps({"headRefOid": self.head, "baseRefName": "main"})}
        with patch.object(guard, "queue_json", queue), patch.dict(os.environ, env):
            return self.decide(command, self.app), calls

    def test_proven_pr_is_allowed(self):
        body = self.root / "body.md"
        body.write_text(PROVEN)
        result, calls = self.receipts(f"gh pr create --body-file {body}", {"status": "passed", "code": "VERIFIED"})
        self.assertIsNone(result)
        self.assertEqual(calls, [["inspect", JOB], ["accept", JOB, "--app", str(self.app / "apps/defuse-near")]])
        self.assertIsNone(self.decide("gh pr edit 5 --add-label bug", self.app))

    def test_browser_claim_without_receipt_is_denied(self):
        body = PROVEN.replace(f"<!-- verification-job: {JOB} -->\n", "")
        result = self.decide("gh pr create --body " + shlex.quote(body), self.app)
        self.assertEqual(result[0], "deny")
        self.assertIn("verification-job", result[1])

    def test_browser_claim_with_an_unexercised_changed_control_is_denied(self):
        # Each of the escaped defects shipped behind a VERIFIED run whose outcomes never read the changed control.
        self.coverage(not_exercised=["swap-flip"], features=["swap.slippage"])
        result, calls = self.receipts("gh pr create --body " + shlex.quote(PROVEN), {"status": "passed"})
        self.assertEqual(result[0], "deny")
        self.assertIn("exercise or `--waive ID=REASON` these changed controls: swap-flip, swap.slippage", result[1])
        self.assertEqual(calls, [], "the gate denies before spending a queue call on the receipt")

    def test_browser_claim_without_a_coverage_receipt_for_the_head_is_denied(self):
        self.coverage()
        self.head = self.commit("later fix")
        result, _ = self.receipts("gh pr create --body " + shlex.quote(PROVEN), {"status": "passed"})
        self.assertEqual(result[0], "deny")
        self.assertIn(f"no coverage receipt for head {self.head[:12]}", result[1])
        self.assertIn("run queue -- coverage --base origin/main", result[1])

    def test_coverage_against_a_later_base_is_denied(self):
        # `--base HEAD` lists no changed controls, so it cannot stand in for the PR's own base.
        self.coverage()
        self.coverage(base=self.head)
        result, _ = self.receipts("gh pr create --body " + shlex.quote(PROVEN), {"status": "passed"})
        self.assertEqual(result[0], "deny")
        self.assertIn("not the PR's base origin/main", result[1])

    def test_pr_edit_checks_the_receipt_for_the_pr_head(self):
        self.coverage(not_exercised=["swap-flip"])
        result, _ = self.receipts("gh pr edit 5 --body " + shlex.quote(PROVEN), {"status": "passed"})
        self.assertEqual(result[0], "deny")
        self.assertIn("swap-flip", result[1])
        self.assertEqual((self.root / "gh.log").read_text().strip(), "pr view 5 --json headRefOid,baseRefName")

    def test_stale_or_failed_receipt_asks(self):
        stale = {"status": "blocked", "code": "SOURCE_VERIFICATION_MISMATCH",
                 "acceptance": {"status": "blocked", "code": "SOURCE_VERIFICATION_MISMATCH"}}
        result, _ = self.receipts("gh pr edit 5 --body " + shlex.quote(PROVEN), stale)
        self.assertEqual(result[0], "ask")
        self.assertIn(f"{JOB}: blocked (SOURCE_VERIFICATION_MISMATCH)", result[1])
        result, _ = self.receipts("gh pr edit 5 --body " + shlex.quote(PROVEN), {"status": "failed", "code": "ASSERTION_FAILED"})
        self.assertIn("failed (ASSERTION_FAILED)", result[1])

    def test_truthful_unverified_pr_needs_no_receipt(self):
        body = PROVEN.replace("- Swap settles on the preview.", "- Not verified in browser: 1Click auth is down.")
        body = body.replace(f"<!-- verification-job: {JOB} -->\n", "")
        self.assertIsNone(self.decide("gh pr create --body " + shlex.quote(body), self.app))
        no_ui = body.replace("- Not verified in browser: 1Click auth is down.", "- n/a: no UI or user flow changed")
        self.assertIsNone(self.decide("gh pr create --body " + shlex.quote(no_ui), self.app))
        self.coverage(not_exercised=["swap-flip"])
        stated = body.replace("- Not verified in browser: 1Click auth is down.", "- Not browser-verified: CI-only toolkit change.")
        self.assertIsNone(self.decide("gh pr create --body " + shlex.quote(stated), self.app))

    def test_screenshots_need_an_image_or_capture_failure(self):
        body = PROVEN.replace("![Swap settled](https://github.com/org/repo/blob/pr-assets/fix/after.png?raw=true)",
                              "Screenshots attached in the thread.")
        result, _ = self.receipts("gh pr create --body " + shlex.quote(body), {"status": "passed"})
        self.assertEqual(result[0], "deny")
        self.assertIn("no image", result[1])
        failed = body.replace("Screenshots attached in the thread.", "Capture failed: the dev server would not start.")
        self.assertIsNone(self.receipts("gh pr create --body " + shlex.quote(failed), {"status": "passed"})[0])

    def test_unqueued_full_suites_in_the_monorepo_are_denied(self):
        result = self.decide(f"cd {self.app}/apps/defuse-near && {FULL_SUITE}", self.app)
        self.assertEqual(result[0], "deny")
        self.assertIn("HEADLESS=true " + guard.WORK_QUEUE + "bun run test --run", result[1])
        result = self.decide(FULL_TYPECHECK, self.app)
        self.assertIn("NODE_OPTIONS=--max-old-space-size=4096 " + guard.WORK_QUEUE + "bun run typecheck", result[1])
        for command in ("bun run build", "npx tsc --noEmit", "bunx --bun vitest run", "turbo test", "turbo run typecheck",
                        "pnpm exec next build", "bun test", "npm test", "bash -c 'cd apps/defuse-near && bun run test --run'"):
            self.assertEqual((self.decide(command, self.app) or ("allow",))[0], "deny", command)

    def test_focused_queued_and_other_repo_checks_are_allowed(self):
        for command in (FOCUSED_RERUN, "bunx vitest run src/features/swap/machine.test.ts", "bun run lint", "bun install",
                        "bunx tsc --version", "bun run test:e2e:local --list", "git log --grep 'bun run build'",
                        guard.WORK_QUEUE + "bun run test --run",
                        "cat > /tmp/notes.md <<'EOF'\nbun run test --run\nEOF\ngit status"):
            self.assertIsNone(self.decide(command, self.app), command)
        self.assertIsNone(self.decide(FULL_SUITE, self.e2e))


    def test_unqueued_browser_tests_are_denied(self):
        result = self.decide(f"cd {self.app} && {CRASH_RUN}", self.app)
        self.assertEqual(result[0], "deny")
        self.assertIn(guard.QUEUE + "bun run test:e2e:local accountPasskeys --reporter=line", result[1])
        self.assertTrue(guard.QUEUE.startswith('npm --prefix "$(python3 ~/.agents/skill-config/scripts/skills.py toolkit-root)" run queue -- run -- '))
        for command in ("bunx playwright test e2e/swap.spec.ts", "./node_modules/.bin/playwright test",
                        "node node_modules/@playwright/test/cli.js test", "CI=1 pnpm test:e2e",
                        "turbo run test:e2e --filter=defuse-near", "CI=1 timeout 900 pnpm exec playwright test",
                        "env PWDEBUG=0 bunx --bun playwright test e2e", "pnpm --filter defuse-near test:e2e:local", "bash -c 'cd apps/defuse-near && bun run test:e2e:local'",
                        "git status; npx playwright test --project=chromium | tee run.log"):
            self.assertEqual(self.decide(command, self.app)[0], "deny", command)

    def test_queued_or_listing_browser_tests_are_allowed(self):
        root = '"$(python3 ~/.agents/skill-config/scripts/skills.py toolkit-root)"'
        for command in (f"cd {self.app} && npm --prefix {root} run queue -- run -- {CRASH_RUN}",
                        'npm --prefix "$VERIFY_TOOLKIT_ROOT" run queue -- run -- bunx playwright test e2e/swap.spec.ts',
                        'npm --prefix "$VERIFY_TOOLKIT_ROOT" run verify:app -- --feature swap.basic',
                        "bunx playwright test --list", "bunx playwright show-report",
                        'git commit -m "test:e2e: fix flake"', "grep -rn playwright test", "rg -l playwright test e2e",
                        "timeout 900 npm --prefix \"$VERIFY_TOOLKIT_ROOT\" run queue -- run -- npx playwright test",
                        "cat > /tmp/body.md <<'EOF'\n- bun run test:e2e:local accountPasskeys\nEOF\ngit status"):
            self.assertIsNone(self.decide(command, self.app), command)

    def fake_gh(self):
        bin_dir = self.root / "bin"
        bin_dir.mkdir(exist_ok=True)
        (bin_dir / "gh").write_text(FAKE_GH)
        (bin_dir / "gh").chmod(0o755)
        return bin_dir

    def checks(self, command, checks=(), mode=""):
        timeout = 0.5 if mode == "hang" else 10
        bin_dir = self.fake_gh()
        log = self.root / "gh.log"
        env = {"PATH": f"{bin_dir}:{os.environ['PATH']}", "FAKE_GH_LOG": str(log), "FAKE_GH_MODE": mode,
               "FAKE_GH_CHECKS": json.dumps(list(checks))}
        with patch.dict(os.environ, env), patch.object(guard, "CHECKS_TIMEOUT", timeout):
            result = self.decide(command, self.app)
        return result, log.read_text() if log.exists() else ""

    def test_merge_with_unfinished_checks_asks(self):
        result, calls = self.checks("gh pr merge 803 --squash --repo defuse-protocol/defuse-frontend-monorepos",
                                    [{"name": "Lint", "bucket": "pass"}, {"name": "Swap / Playwright", "bucket": "pending"}])
        self.assertEqual(result[0], "ask")
        self.assertIn("pending: Swap / Playwright", result[1])
        self.assertEqual(calls.strip(), "pr checks 803 --json name,bucket --repo defuse-protocol/defuse-frontend-monorepos")
        # #803 merged with a failing non-required check.
        result, _ = self.checks("gh pr merge --auto -s 803", [{"name": "Vercel Preview Comments", "bucket": "fail"},
                                                              {"name": "Build", "bucket": "cancel"}])
        self.assertEqual(result[0], "ask")
        self.assertIn("failed: Vercel Preview Comments; cancelled: Build", result[1])

    def test_merge_with_green_checks_is_allowed(self):
        result, calls = self.checks("gh pr merge --squash", [{"name": "Lint", "bucket": "pass"}, {"name": "Preview", "bucket": "skipping"}])
        self.assertIsNone(result)
        self.assertEqual(calls.strip(), "pr checks --json name,bucket")
        self.assertIsNone(self.checks("gh pr merge 803 --disable-auto")[0])

    def test_unreadable_checks_ask(self):
        for mode, reason in (("fail", "Could not resolve"), ("hang", "timed out"), ("", "no checks")):
            result, _ = self.checks("gh pr merge 803 --squash", mode=mode)
            self.assertEqual(result[0], "ask", mode)
            self.assertIn(reason, result[1])


if __name__ == "__main__":
    unittest.main()
