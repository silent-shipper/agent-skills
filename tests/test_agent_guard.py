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

## Merge Danger
"""

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

    def test_proven_pr_is_allowed(self):
        body = self.root / "body.md"
        body.write_text(PROVEN)
        self.assertIsNone(self.decide(f"gh pr create --body-file {body}", self.app))
        self.assertIsNone(self.decide("gh pr edit 5 --add-label bug", self.app))


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

    def checks(self, command, checks=(), mode=""):
        timeout = 0.5 if mode == "hang" else 10
        bin_dir = self.root / "bin"
        bin_dir.mkdir(exist_ok=True)
        (bin_dir / "gh").write_text(FAKE_GH)
        (bin_dir / "gh").chmod(0o755)
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
