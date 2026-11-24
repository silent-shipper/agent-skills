#!/usr/bin/env python3
"""Claude Code PreToolUse guard for PR evidence, push targets, commit identity, merge checks, whole-stack merges and the
test queues: near-verify's in defuse-frontend-monorepos, `heavy` everywhere else."""
import json
import os
import re
import shlex
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import heavy  # noqa: E402

PLACEHOLDER = re.compile(r"<[a-z][^<>\n]*>")
TOOLKIT = '"$(python3 ~/.agents/skill-config/scripts/skills.py toolkit-root)"'
QUEUE = f"npm --prefix {TOOLKIT} run queue -- run -- "
WORK_QUEUE = f"npm --prefix {TOOLKIT} run queue -- run --lane work -- "
HEAVY = "heavy -- "
QUEUED = ("queue", "verify:app", "testq", "testq.mjs", "heavy")
SCRIPT_DEPTH = 2
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
LOCAL_EMAIL = re.compile(r"@(?:localhost|[^@\s]+\.(?:local|localdomain))$", re.I)
OUTGOING_LIMIT = 200
MERGE_VALUE_OPTIONS = {"-A", "--author-email", "-b", "--body", "-F", "--body-file", "--match-head-commit",
                       "-R", "--repo", "-t", "--subject"}
T3_MERGE = "mcp__t3-code__pull_request_merge"
PREFIX_WORDS = {"export", "declare", "local", "readonly", "typeset", "env", "command", "exec", "nohup", "time",
                "then", "do", "else", "!", "{"}
MERGE_ASYNC = re.compile(r"(?:^|/)repos/([\w.-]+/[\w.-]+)/pulls/(\d+)/merge-async/?$")


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
        if os.path.basename(word) in QUEUED:
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
        is_heavy = script != "test" or not focused
    elif tool in TEST_TOOLS:
        is_heavy = not focused
    elif tool == "tsc":
        is_heavy = True
    elif tool == "next":
        is_heavy = args[:1] == ["build"]
    else:
        return None
    return (words[:start], words[start:]) if is_heavy else None


def browser_test(words):
    """The browser-test command of a segment that runs Playwright or a test:e2e script outside the toolkit queue."""
    if "--list" in words:
        return None
    for index, word in enumerate(words):
        name = os.path.basename(word)
        if name in QUEUED:
            return None
        if name in SHELLS and "-c" in words[index:-1]:
            inner = words[words.index("-c", index) + 1]
            return next(filter(None, map(browser_test, segments(inner))), None)
        launched = all(os.path.basename(w) in LAUNCHERS or w.startswith("-") or re.match(r"^\w+=|^\d+$", w) for w in words[:index])
        playwright = PLAYWRIGHT.search(word) and words[index + 1:index + 2] == ["test"] and launched
        script = re.search(r"(?:^|#)test:e2e", word) and SCRIPT_RUNNERS & {os.path.basename(w) for w in words[:index]}
        if playwright or script:
            return until_redirect(words)
    return None


def until_redirect(words):
    return shlex.join(words[:next((i for i, w in enumerate(words) if REDIRECT.match(w)), len(words))])


def command_words(words):
    """The words from the program on: leading assignments and nohup/time/exec/env/timeout N dropped."""
    while words and (re.match(r"^\w+=", words[0]) or os.path.basename(words[0]) in {"nohup", "time", "exec", "env"}):
        words = words[1:]
    if words[:1] == ["timeout"] and len(words) > 2:
        return command_words(words[2:])
    return words


def browser_script(words, here):
    """A `node x.mjs`-style run of a script that starts a browser itself."""
    words = command_words(words)
    if not words or os.path.basename(words[0]) not in heavy.SCRIPT_HOSTS:
        return None
    script = heavy.script_file(words, here)
    return until_redirect(words) if script and heavy.loads_browser(script) else None


def script_work(words, here, depth=0):
    """The first unqueued heavy or browser command inside a local shell script this segment runs."""
    words = command_words(words)
    if depth >= SCRIPT_DEPTH or any(os.path.basename(w) in QUEUED for w in words):
        return None
    script = heavy.script_file(words, here)
    if not script or not heavy.is_shell_script(script):
        return None
    text = "\n".join(line for line in heavy.read_script(script).splitlines() if not line.lstrip().startswith("#"))
    for inner in simple_commands(text):
        for start in range(len(inner)):
            rest = inner[start:]
            run = heavy_check(rest)
            found = (browser_test(rest) or (run and shlex.join(run[1])) or browser_script(rest, here)
                     or script_work(rest, here, depth + 1))
            if found:
                return found
    return None


def queue_decision(command, cwd):
    """Heavy or browser work that skips its queue: near-verify's in defuse-frontend-monorepos, `heavy` everywhere else."""
    background = " It waits for a free slot, so run it in the background when it may take over 10 minutes."
    here = cwd
    for words in segments(HEREDOC.sub(r"\1\4", command)):
        if words[:1] == ["cd"] and len(words) > 1:
            here = (here / os.path.expanduser(words[1])).resolve()
            continue
        test = browser_test(words) or browser_script(words, here)
        run = heavy_check(words)
        script = script_work(words, here)
        if not (test or run or script):
            continue
        team = remote(here) == MONOREPO
        if test:
            return ("deny", "Browser tests share one queue so this Mac runs one at a time; an unqueued run overloaded "
                            f"it before. Run it through the queue instead: {QUEUE if team else HEAVY}{test}"
                            + ("" if team else background))
        if run:
            assignments, run = run
            prefix = shlex.join(assignments) + " " if assignments else ""
            if team:
                return ("deny", "Full unit suites, builds and typechecks run in the queue's work lane (two at a time) so "
                                "they cannot overload this Mac beside a browser run; a direct full suite did on 2026-10-26. "
                                f"Name the affected test files to run them directly, or queue it: {prefix}{WORK_QUEUE}"
                                f"{shlex.join(run)}")
            return ("deny", "Full test suites, builds and typechecks run through this Mac's queue (two at a time, once "
                            "load settles); unqueued builds beside browser runs overloaded it on 2026-11-24. Name the "
                            f"affected test files to run them directly, or queue it: {prefix}{HEAVY}{shlex.join(run)}."
                            + background)
        return ("deny", f"This script runs `{script}` outside a queue; an unqueued script overloaded this Mac on "
                        f"2026-11-24. Queue the whole script: {HEAVY}{until_redirect(command_words(words))}." + background)
    return None


def git_command(words):
    """The subcommand and `-c key=value` overrides of a git invocation, after leading VAR=value assignments."""
    start = 0
    while start < len(words) and re.match(r"^\w+=", words[start]):
        start += 1
    if words[start:start + 1] != ["git"]:
        return None, {}
    overrides = {w.split("=", 1)[0]: w.split("=", 1)[1] for w in words[:start]}
    rest = iter(words[start + 1:])
    for word in rest:
        if word in ("-C", "-c", "--git-dir", "--work-tree"):
            value = next(rest, "")
            if word == "-c" and "=" in value:
                key, val = value.split("=", 1)
                overrides[key.lower()] = val
        elif not word.startswith("-"):
            return word, overrides
    return None, overrides


def commit_identity_problem(overrides, target):
    """A commit authored with an empty or machine-local email, which Vercel rejects for preview deployments."""
    try:
        email = (overrides.get("GIT_AUTHOR_EMAIL") or overrides.get("user.email") or os.environ.get("GIT_AUTHOR_EMAIL")
                 or git(target, "config", "user.email") or "")
        if email and not LOCAL_EMAIL.search(email):
            return None
        origin = (git(target, "config", "--show-origin", "--get", "user.email") or "").split("\t")[0]
    except (OSError, subprocess.SubprocessError):
        return None
    if origin.startswith("file:.git/config") or origin.endswith("/.git/config"):
        fix = ("this repo's .git/config overrides your global identity for every worktree; remove it with "
               "`git config --local --unset user.email` and `git config --local --unset user.name`")
    else:
        fix = "set a real identity with `git config --global user.email <github noreply address>`"
    return (f"This commit would be authored as `{email or 'an auto-detected host address'}`. Vercel rejects such "
            f"commits, which blocked preview deployments on two PRs; {fix}. Automation that needs its own identity "
            "passes it per command with `git -c user.name=... -c user.email=... commit`.")


def outgoing_identity_problem(target):
    """Unpushed commits on HEAD authored or committed with a machine-local email."""
    try:
        log = git(target, "log", f"-n{OUTGOING_LIMIT}", "--format=%h%x09%ae%x09%ce", "HEAD", "--not", "--remotes")
    except (OSError, subprocess.SubprocessError):
        return None
    bad = [line.split("\t") for line in (log or "").splitlines()
           if any(not email or LOCAL_EMAIL.search(email) for email in line.split("\t")[1:])]
    if not bad:
        return None
    emails = sorted({email for _, *pair in bad for email in pair if not email or LOCAL_EMAIL.search(email)})
    return (f"{len(bad)} unpushed commit(s) ({', '.join(sha for sha, *_ in bad[:5])}) use {', '.join(emails)}, which "
            "Vercel rejects for previews. Fix the identity first (`git config --show-origin user.email`), then rewrite "
            f"them: `git rebase -r {bad[-1][0]}^ --exec 'git commit --amend --no-edit --reset-author'`.")


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


def gh_json(args, cwd):
    """Parsed output of a read-only gh call, or None when gh cannot answer."""
    try:
        result = subprocess.run(["gh", *args], cwd=cwd, capture_output=True, text=True, timeout=CHECKS_TIMEOUT)
        return json.loads(result.stdout) if result.returncode == 0 else None
    except (OSError, subprocess.SubprocessError, ValueError):
        return None


def stack_merge_problem(repo, number, whole_stack, cwd):
    """("deny", why) when merging PR `number` would merge part of its GitHub stack, ("ask", why) when gh cannot tell,
    or None when the merge covers no stack or all of one."""
    pr = gh_json(["api", f"repos/{repo}/pulls/{number}"], cwd)
    if not isinstance(pr, dict):
        return ("ask", f"`gh api repos/{repo}/pulls/{number}` failed, so whether this merge splits a stack is unknown. "
                       "Retry, or confirm the user approved this merge.")
    stack = pr.get("stack")
    if not isinstance(stack, dict) or not stack.get("number"):
        return None
    listing = gh_json(["api", f"repos/{repo}/stacks/{stack['number']}"], cwd)
    entries = listing.get("pull_requests") if isinstance(listing, dict) else None
    layers = [layer for layer in entries if isinstance(layer, dict) and layer.get("state") == "open"] if isinstance(entries, list) else []
    top = layers[-1].get("number") if layers else None
    sha = (layers[-1].get("head") or {}).get("sha") if layers and isinstance(layers[-1].get("head"), dict) else None
    position, size = stack.get("position"), stack.get("size")
    known = isinstance(position, int) and isinstance(size, int)
    if whole_stack:
        if not top and not known:
            return ("ask", f"#{number} is in stack #{stack['number']}, but gh could not show which layer is its top. "
                           "Retry, or confirm the user approved this merge.")
        if (str(top) == str(number)) if top else position == size:
            return None
    if top and sha:
        how = (f"pull_request_merge with number: {top}, stack: true, method: \"squash\", expectedHeadSha: \"{sha}\" "
               f"(without T3: `gh api -X PUT repos/{repo}/pulls/{top}/merge-async -f merge_method=squash -f sha={sha}`)")
    else:
        how = (f"pull_request_merge with stack: true on its top PR (`gh api repos/{repo}/stacks/{stack['number']}` "
               "lists the layers bottom first)")
    where = f"layer {position} of {size} in" if known else "a layer of"
    return ("deny", f"#{number} is {where} stack #{stack['number']}, and the user merges stacks as one unit, never a "
                    "layer alone. Once every layer is approved on its live head and its checks are settled, merge the "
                    f"whole stack from its top: {how}.")


def merge_decision(repo, number, whole_stack, here, project):
    """A merge that splits a GitHub stack is denied; one in another repository than the session's needs the user."""
    problem = stack_merge_problem(repo, number, whole_stack, here) if repo and number else None
    if problem and problem[0] == "deny":
        return problem
    home = remote(project)
    if repo and home and repo.lower() != home:
        return ("ask", f"This session's repo is {home}, but this merge targets {repo}. "
                       "Confirm the user named this repo as the target.")
    return problem


def t3_merge_decision(payload):
    tool_input = payload.get("tool_input") or {}
    cwd = Path(payload.get("cwd") or os.getcwd())
    project = Path(os.environ.get("CLAUDE_PROJECT_DIR") or cwd)
    repo = tool_input.get("repository") or remote(cwd)
    branch_pr = gh_json(["pr", "view", "--json", "number"], cwd) if not tool_input.get("number") else None
    number = tool_input.get("number") or (branch_pr.get("number") if isinstance(branch_pr, dict) else None)
    return merge_decision(repo, number, tool_input.get("stack") is True, cwd, project)


def expand(word, variables):
    return re.sub(r"\$\{?(\w+)\}?", lambda m: variables.get(m[1], m[0]), word)


def simple_commands(command):
    """The words of each simple command, split at `;`, `&`, `|` and unquoted newlines; quoted text stays whole."""
    lexer = shlex.shlex(HEREDOC.sub(r"\1\4", command).replace("\\\n", " "), posix=True, punctuation_chars=";&|\n")
    lexer.whitespace, lexer.whitespace_split, lexer.commenters = " \t\r", True, ""
    words = []
    try:
        for token in lexer:
            if set(token) <= set(";&|\n"):
                yield words
                words = []
            else:
                words.append(token)
    except ValueError:
        yield from (line.split() for line in command.splitlines())
        return
    yield words


def merge_async_calls(command):
    """The repository and PR of every `gh api` merge-async request in the command, with variables assigned earlier
    (plainly or through `export` and the like) expanded."""
    variables = {}
    for words in simple_commands(command):
        start = 0
        while start < len(words) and (words[start] in PREFIX_WORDS or re.match(r"^\w+=", words[start])):
            if "=" in words[start]:
                name, value = words[start].split("=", 1)
                variables[name] = value
            start += 1
        if words[start:start + 2] == ["gh", "api"]:
            found = next(filter(None, (MERGE_ASYNC.search(expand(w, variables)) for w in words[start + 2:])), None)
            if found:
                yield found[1], found[2]


def merge_command_decision(command, cwd, project):
    decisions = [merge_decision(repo, number, True, cwd, project) for repo, number in merge_async_calls(command)]
    return next((d for d in decisions if d and d[0] == "deny"), None) or next(filter(None, decisions), None)


def decide(payload):
    if payload.get("tool_name") == T3_MERGE:
        return t3_merge_decision(payload)
    if payload.get("tool_name") != "Bash":
        return None
    command = payload.get("tool_input", {}).get("command", "")
    cwd = Path(payload.get("cwd") or os.getcwd())
    project = Path(os.environ.get("CLAUDE_PROJECT_DIR") or cwd)
    merge = merge_command_decision(command, cwd, project)
    if merge and merge[0] == "deny":
        return merge
    rest = shell_decision(command, cwd, project)
    if rest and rest[0] == "deny" or not merge:
        return rest
    return ("ask", f"{rest[1]} {merge[1]}") if rest else merge


def shell_decision(command, cwd, project):
    queued = queue_decision(command, cwd)
    if queued:
        return queued
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
        subcommand, overrides = git_command(words)
        if subcommand == "commit":
            problem = commit_identity_problem(overrides, target)
            if problem:
                return ("deny", problem)
        is_pr = words[:3] in (["gh", "pr", "create"], ["gh", "pr", "edit"])
        if is_push or is_pr or words[:3] == ["gh", "pr", "merge"]:
            repo = (option(words, "--repo", "-R") or "").lower() or remote(target)
            home = remote(project)
            if repo and home and repo != home:
                return ("ask", f"This session's repo is {home}, but this command targets {repo}. "
                               "Confirm the user named this repo as the target.")
        if subcommand == "push":
            problem = outgoing_identity_problem(target)
            if problem:
                return ("deny", problem)
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
                            + ". Fill Screenshots and Verified in browser per the ship-it skill before opening or updating the PR.")
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
