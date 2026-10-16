#!/usr/bin/env python3
"""Claude Code PreToolUse guard for PR evidence and push targets."""
import json
import os
import re
import shlex
import subprocess
import sys
from pathlib import Path

PLACEHOLDER = re.compile(r"<[a-z][^<>\n]*>")


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
    section = re.search(r"(?ms)^## Evidence\s*$(.*?)(?=^## |\Z)", body)
    if not section:
        return ["missing `## Evidence` section"]
    text = section[1]
    errors = []
    if not re.search(r"\*\*After:\*\*\s*\S", text):
        errors.append("no `**After:**` result")
    if not re.search(r"\*\*Checks:\*\*\s*\S", text):
        errors.append("no `**Checks:**` line")
    if not re.search(r"\*\*Browser:\*\*\s*(verified|not run|n/a)\b", text, re.I):
        errors.append("no `**Browser:** verified <link> | not run: <reason> | n/a` line")
    if PLACEHOLDER.search(text):
        errors.append("unfilled template placeholder " + PLACEHOLDER.search(text)[0])
    return errors


def decide(payload):
    if payload.get("tool_name") != "Bash":
        return None
    command = payload.get("tool_input", {}).get("command", "")
    cwd = Path(payload.get("cwd") or os.getcwd())
    project = Path(os.environ.get("CLAUDE_PROJECT_DIR") or cwd)
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
                            + ". Fill Evidence per the ship skill before opening or updating the PR.")
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
