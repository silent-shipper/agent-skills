#!/usr/bin/env python3
"""Claude Code PreToolUse guard for PR evidence, push targets, merge checks and the shared browser-test queue."""
import json
import os
import re
import shlex
import subprocess
import sys
from pathlib import Path

PLACEHOLDER = re.compile(r"<[a-z][^<>\n]*>")
QUEUE = 'npm --prefix "$(python3 ~/.agents/skill-config/scripts/skills.py toolkit-root)" run queue -- run -- '
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


def evidence_errors(body):
    section = re.search(r"(?ms)^## Verified in browser\s*$(.*?)(?=^## |\Z)", body)
    if not section:
        return ["missing `## Verified in browser` section"]
    errors = []
    if not re.search(r"(?m)^\s*[-*]\s+\S", section[1]):
        errors.append("no bullet under `## Verified in browser`")
    for heading in ("Screenshots", "Verified in browser"):
        part = re.search(rf"(?ms)^## {heading}\s*$(.*?)(?=^## |\Z)", body)
        if part and PLACEHOLDER.search(part[1]):
            errors.append("unfilled template placeholder " + PLACEHOLDER.search(part[1])[0])
    return errors


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
