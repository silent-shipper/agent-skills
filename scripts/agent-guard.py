#!/usr/bin/env python3
"""Claude Code PreToolUse guard for PR evidence, push targets, merge checks and the shared test queue."""
import json
import os
import re
import shlex
import subprocess
import sys
from pathlib import Path

PLACEHOLDER = re.compile(r"<[a-z][^<>\n]*>")
TOOLKIT = '"$(python3 ~/.agents/skill-config/scripts/skills.py toolkit-root)"'
QUEUE = f"npm --prefix {TOOLKIT} run queue -- run -- "
WORK_QUEUE = f"npm --prefix {TOOLKIT} run queue -- run --lane work -- "
MONOREPO = "defuse-protocol/defuse-frontend-monorepos"
HEAVY_SCRIPTS = {"test", "build", "typecheck"}
TEST_TOOLS = {"vitest", "jest"}
TEST_FILE = re.compile(r"\.(?:test|spec)\.[cm]?[jt]sx?$")
RECEIPT = re.compile(r"<!--\s*verification-job:\s*([a-f0-9-]{36})\s*-->")
NOT_CLAIMED = re.compile(r"^\s*[-*]\s+(?:not verified in browser|not browser-verified|n/a)\b", re.I | re.M)
IMAGE = re.compile(r"!\[[^\]]*\]\([^)\s]+\)|<img\s[^>]*src=")
CAPTURE_FAILED = re.compile(r"^\s*[-*]?\s*capture failed:", re.I | re.M)
QUEUE_TIMEOUT = 60
SCRIPT_RUNNERS = {"bun", "bunx", "npm", "npx", "pnpm", "yarn", "turbo"}
SHELLS = {"sh", "bash", "zsh", "dash"}
LAUNCHERS = SCRIPT_RUNNERS | {"node", "env", "exec", "x", "timeout", "nohup", "time", "caffeinate", "--"}
PLAYWRIGHT = re.compile(r"(?:^|/)@?playwright(?:/test)?(?:/cli\.js)?$")
HEREDOC = re.compile(r"(<<-?\s*(['\"]?)([A-Za-z_]\w*)\2)([^\n]*)\n.*?^\s*\3\s*$", re.S | re.M)
REDIRECT = re.compile(r"^\d*(?:>>?|<)")
GREEN = {"pass", "skipping"}
CHECKS_TIMEOUT = 20
MERGE_VALUE_OPTIONS = {"-A", "--author-email", "-b", "--body", "-F", "--body-file", "--match-head-commit",
                       "-R", "--repo", "-t", "--subject"}


def remote(path):
    try:
        url = subprocess.run(["git", "-C", str(path), "remote", "get-url", "origin"],
                             capture_output=True, text=True, timeout=5).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return None
    match = re.search(r"[:/]([^/:]+/[^/]+?)(?:\.git)?/?$", url)
    return match[1].lower() if match else None


def segments(command):
    lexer = shlex.shlex(command, posix=True, punctuation_chars=";&|")
    lexer.whitespace_split = True
    words = []
    try:
        for token in lexer:
            if set(token) <= set(";&|"):
                yield words
                words = []
            else:
                words.append(token)
    except ValueError:
        yield command.split()
        return
    yield words


def option(words, *names):
    for index, word in enumerate(words):
        for name in names:
            if word == name and index + 1 < len(words):
                return words[index + 1]
            if word.startswith(name + "="):
                return word.split("=", 1)[1]
    return None


def browser_section(body):
    return re.search(r"(?ms)^## Verified in browser\s*$(.*?)(?=^## |\Z)", body)


def evidence_errors(body):
    section = browser_section(body)
    if not section:
        return ["missing `## Verified in browser` section"]
    errors = []
    if not re.search(r"(?m)^\s*[-*]\s+\S", section[1]):
        errors.append("no bullet under `## Verified in browser`")
    for heading in ("Screenshots", "Verified in browser"):
        part = re.search(rf"(?ms)^## {heading}\s*$(.*?)(?=^## |\Z)", body)
        if part and PLACEHOLDER.search(part[1]):
            errors.append("unfilled template placeholder " + PLACEHOLDER.search(part[1])[0])
    screenshots = re.search(r"(?ms)^## Screenshots\s*$(.*?)(?=^## |\Z)", body)
    if screenshots and not IMAGE.search(screenshots[1]) and not CAPTURE_FAILED.search(screenshots[1]):
        errors.append("`## Screenshots` has no image; attach the capture or write `Capture failed: <reason>`")
    if claimed(section[1]) and not RECEIPT.search(body):
        errors.append("browser bullets need the passing run's hidden receipt `<!-- verification-job: <job-uuid> -->`; "
                      "otherwise write `- Not verified in browser: <reason>`")
    return errors


def claimed(section):
    """Whether the browser section claims proof rather than stating it was not checked."""
    bullets = re.findall(r"(?m)^\s*[-*]\s+\S.*$", section)
    return any(not NOT_CLAIMED.match(bullet) for bullet in bullets)


def git(here, *args):
    result = subprocess.run(["git", "-C", str(here), *args], capture_output=True, text=True, timeout=5)
    return result.stdout.strip() if result.returncode == 0 else None


def pr_target(words, here):
    """The head commit and base branch the PR body will describe."""
    if words[2] == "edit":
        number = words[3:4] if words[3:4] and not words[3].startswith("-") else []
        command = ["gh", "pr", "view", *number, "--json", "headRefOid,baseRefName"]
        repo = option(words, "--repo", "-R")
        try:
            result = subprocess.run(command + (["--repo", repo] if repo else []), cwd=here, capture_output=True,
                                    text=True, timeout=CHECKS_TIMEOUT)
            pr = json.loads(result.stdout)
            return pr["headRefOid"], pr["baseRefName"]
        except (OSError, subprocess.SubprocessError, ValueError, KeyError, TypeError):
            return None, None
    default = (git(here, "symbolic-ref", "--short", "refs/remotes/origin/HEAD") or "origin/main").removeprefix("origin/")
    return git(here, "rev-parse", "HEAD"), option(words, "--base", "-B") or default


def coverage_problems(words, here):
    """Browser bullets need the PR head's coverage receipt with every changed control exercised or waived."""
    head, base = pr_target(words, here)
    if not head:
        return ["could not read the PR's head commit"]
    fix = f"run `cd <app> && npm --prefix {TOOLKIT} run queue -- coverage --base origin/{base}` on {head[:12]}"
    common = git(here, "rev-parse", "--path-format=absolute", "--git-common-dir")
    receipts = sorted(Path(common, "near-verify", "coverage", head).glob("*.json")) if common else []
    if not receipts:
        return [f"no coverage receipt for head {head[:12]}; {fix}"]
    fork = git(here, "merge-base", head, f"origin/{base}")
    if not fork:
        return [f"origin/{base} has no common commit with {head[:12]} here; `git fetch origin {base}`"]
    problems = []
    for file in receipts:
        try:
            receipt = json.loads(file.read_text())
        except (OSError, ValueError):
            problems.append(f"{file} is unreadable; {fix}")
            continue
        app = receipt.get("app", file.stem)
        if git(here, "merge-base", "--is-ancestor", str(receipt.get("base")), fork) is None:
            problems.append(f"{app}: the receipt compares with {str(receipt.get('base'))[:12]}, not the PR's base "
                            f"origin/{base}, so it can miss this PR's changes; {fix}")
            continue
        unexercised = [control for row in receipt.get("files", []) for control in row.get("notExercised", [])]
        unexercised += receipt.get("features", {}).get("withoutPassingRun", [])
        if unexercised:
            problems.append(f"{app}: exercise or `--waive ID=REASON` these changed controls: {', '.join(unexercised)}")
    return problems


def queue_json(args, cwd):
    command = f"npm --prefix {TOOLKIT} run -s queue -- {shlex.join(args)}"
    result = subprocess.run(["sh", "-c", command], cwd=cwd, capture_output=True, text=True, timeout=QUEUE_TIMEOUT)
    try:
        return json.loads(result.stdout)
    except ValueError:
        raise RuntimeError(next(iter(result.stderr.strip().splitlines()), f"exit {result.returncode}")) from None


def receipt_problems(body, here):
    """Each receipt must name a verification that passed and still matches its app checkout's current source."""
    problems = []
    for job in dict.fromkeys(RECEIPT.findall(body)):
        try:
            app = queue_json(["inspect", job], here).get("cwd")
            report = queue_json(["accept", job, "--app", app or "."], here)
        except (OSError, subprocess.SubprocessError, RuntimeError) as error:
            problems.append(f"{job}: could not be checked ({error})")
            continue
        if report.get("status") != "passed":
            code = report.get("acceptance", {}).get("code") or report.get("code") or "not accepted"
            problems.append(f"{job}: {report.get('status', 'unknown')} ({code})")
    return problems


def heavy_check(words):
    """A full unit suite, build or typecheck that runs outside the toolkit queue; focused test files stay direct."""
    words = words[:next((i for i, w in enumerate(words) if REDIRECT.match(w)), len(words))]
    if "--list" in words or {"--help", "--version", "-v"} & set(words):
        return None
    for index, word in enumerate(words):
        if os.path.basename(word) in ("queue", "verify:app", "testq", "testq.mjs"):
            return None
        if os.path.basename(word) in SHELLS and "-c" in words[index:-1]:
            inner = words[words.index("-c", index) + 1]
            return next(filter(None, map(heavy_check, segments(inner))), None)
    start = 0
    while start < len(words) and (re.match(r"^\w+=", words[start]) or os.path.basename(words[start]) in {"env", "exec", "nohup", "time"}):
        start += 1
    rest = words[start:]
    if not rest:
        return None
    tool, args = os.path.basename(rest[0]), rest[1:]
    if tool in {"npx", "bunx"} or rest[:2] == ["pnpm", "exec"]:
        args = args[1:] if tool == "pnpm" else args
        while args and args[0].startswith("-"):
            args = args[1:]
        if not args:
            return None
        tool, args = os.path.basename(args[0]), args[1:]
    focused = any("/" in w or TEST_FILE.search(w) for w in args if not w.startswith("-"))
    if tool in SCRIPT_RUNNERS:
        positional = [w for w in args if not w.startswith("-")]
        script = positional[1] if positional[:1] == ["run"] and len(positional) > 1 else (positional or [""])[0]
        if script not in HEAVY_SCRIPTS:
            return None
        heavy = script != "test" or not focused
    elif tool in TEST_TOOLS:
        heavy = not focused
    elif tool == "tsc":
        heavy = True
    elif tool == "next":
        heavy = args[:1] == ["build"]
    else:
        return None
    return (words[:start], words[start:]) if heavy else None


def browser_test(words):
    """The browser-test command of a segment that runs Playwright or a test:e2e script outside the toolkit queue."""
    if "--list" in words:
        return None
    for index, word in enumerate(words):
        name = os.path.basename(word)
        if name in ("queue", "verify:app", "testq", "testq.mjs"):
            return None
        if name in SHELLS and "-c" in words[index:-1]:
            inner = words[words.index("-c", index) + 1]
            return next(filter(None, map(browser_test, segments(inner))), None)
        launched = all(os.path.basename(w) in LAUNCHERS or w.startswith("-") or re.match(r"^\w+=|^\d+$", w) for w in words[:index])
        playwright = PLAYWRIGHT.search(word) and words[index + 1:index + 2] == ["test"] and launched
        script = re.search(r"(?:^|#)test:e2e", word) and SCRIPT_RUNNERS & {os.path.basename(w) for w in words[:index]}
        if playwright or script:
            end = next((i for i, w in enumerate(words) if REDIRECT.match(w)), len(words))
            return shlex.join(words[:end])
    return None


def merge_target(words):
    rest = iter(words[3:])
    for word in rest:
        if word in MERGE_VALUE_OPTIONS:
            next(rest, None)
        elif not word.startswith("-"):
            return word
    return None


def unfinished_checks(words, here):
    """Every check must finish green before a merge; any other state, or one gh cannot report, needs the user."""
    command = ["gh", "pr", "checks", *filter(None, [merge_target(words)]), "--json", "name,bucket"]
    repo = option(words, "--repo", "-R")
    if repo:
        command += ["--repo", repo]
    shown = shlex.join(command)
    try:
        result = subprocess.run(command, cwd=here, capture_output=True, text=True, timeout=CHECKS_TIMEOUT)
    except subprocess.TimeoutExpired:
        return f"`{shown}` timed out after {CHECKS_TIMEOUT} s, so the check state is unknown"
    except OSError as error:
        return f"`{shown}` could not run ({error.strerror}), so the check state is unknown"
    try:
        checks = json.loads(result.stdout)
    except ValueError:
        reason = next(iter(result.stderr.strip().splitlines()), f"exit {result.returncode}")
        return f"`{shown}` failed ({reason}), so the check state is unknown"
    if not checks:
        return "this PR reports no checks"
    unfinished = {}
    for check in checks:
        if check.get("bucket") not in GREEN:
            unfinished.setdefault(check.get("bucket") or "unknown", []).append(check.get("name") or "unnamed")
    labels = {"fail": "failed", "cancel": "cancelled"}
    return "; ".join(f"{labels.get(bucket, bucket)}: {', '.join(names)}" for bucket, names in unfinished.items()) or None


def decide(payload):
    if payload.get("tool_name") != "Bash":
        return None
    command = payload.get("tool_input", {}).get("command", "")
    cwd = Path(payload.get("cwd") or os.getcwd())
    project = Path(os.environ.get("CLAUDE_PROJECT_DIR") or cwd)
    for words in segments(HEREDOC.sub(r"\1\4", command)):
        test = browser_test(words)
        if test:
            return ("deny", "Browser tests share one queue so this Mac runs one at a time; an unqueued run overloaded "
                            f"it before. Run it through the queue instead: {QUEUE}{test}")
    here = cwd
    for words in segments(HEREDOC.sub(r"\1\4", command)):
        if words[:1] == ["cd"] and len(words) > 1:
            here = (here / os.path.expanduser(words[1])).resolve()
            continue
        heavy = heavy_check(words)
        if heavy and remote(here) == MONOREPO:
            assignments, run = heavy
            prefix = shlex.join(assignments) + " " if assignments else ""
            return ("deny", "Full unit suites, builds and typechecks run in the queue's work lane (two at a time) so they "
                            "cannot overload this Mac beside a browser run; a direct full suite did on 2026-10-26. Name the "
                            f"affected test files to run them directly, or queue it: {prefix}{WORK_QUEUE}{shlex.join(run)}")
    here = cwd
    for words in segments(command):
        if not words:
            continue
        if words[0] == "cd" and len(words) > 1:
            here = (here / os.path.expanduser(words[1])).resolve()
            continue
        target = here
        if words[0] == "git" and option(words, "-C"):
            target = (here / os.path.expanduser(option(words, "-C"))).resolve()
        is_push = words[0] == "git" and "push" in words
        is_pr = words[:3] in (["gh", "pr", "create"], ["gh", "pr", "edit"])
        if is_push or is_pr or words[:3] == ["gh", "pr", "merge"]:
            repo = (option(words, "--repo", "-R") or "").lower() or remote(target)
            home = remote(project)
            if repo and home and repo != home:
                return ("ask", f"This session's repo is {home}, but this command targets {repo}. "
                               "Confirm the user named this repo as the target.")
        if words[:3] == ["gh", "pr", "merge"] and "--disable-auto" not in words:
            unfinished = unfinished_checks(words, here)
            if unfinished:
                return ("ask", f"Not every PR check has finished green ({unfinished}). Wait until all checks pass, "
                               "or confirm the user approved merging in this state.")
        if is_pr:
            body = option(words, "--body")
            body_file = option(words, "--body-file", "-F")
            if body_file and body_file != "-":
                try:
                    body = (here / os.path.expanduser(body_file)).read_text()
                except OSError:
                    body = None
            if body is not None:
                errors = evidence_errors(body)
                if errors:
                    return ("deny", "PR body fails the ship evidence gate: " + "; ".join(errors)
                            + ". Fill Screenshots and Verified in browser per the ship skill before opening or updating the PR.")
                if claimed(browser_section(body)[1]):
                    uncovered = coverage_problems(words, here)
                    if uncovered:
                        return ("deny", "The PR claims browser proof, but no passing run is shown to exercise what it "
                                        "changed: " + "; ".join(uncovered) + ". A VERIFIED run that never touched the "
                                        "changed control let defects ship before. Otherwise write "
                                        "`- Not browser-verified: <reason>`.")
                problems = receipt_problems(body, here)
                if problems:
                    return ("ask", "The PR claims browser proof, but its verification receipt does not show a pass on the "
                                   "current source: " + "; ".join(problems) + ". Rerun or re-accept the verification, or "
                                   "confirm the user approved shipping with this evidence.")
    return None


def main():
    try:
        result = decide(json.load(sys.stdin))
    except ValueError:
        return
    if result:
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse",
                                                 "permissionDecision": result[0],
                                                 "permissionDecisionReason": result[1]}}))


if __name__ == "__main__":
    main()
