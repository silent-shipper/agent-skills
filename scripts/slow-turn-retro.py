#!/usr/bin/env python3
"""Stop hook for Claude Code and Codex. After an interactive turn with 10+ minutes of active work it asks the agent for
a short speedup retro, but only when a slow command in that turn keeps recurring, and logs every Stop so the return can
be audited. `--dry-run TRANSCRIPT` prints the timing and decision for a transcript's last turn; `--report` judges a week."""
import fcntl
import glob
import json
import os
import re
import statistics
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

HOME = Path.home() / ".local/state/slow-turn-retro"
MIN_ACTIVE_S = 600
MIN_TOOL_S = 30
MIN_TIMER_S = 60
MAX_STEP_LATENCY_S = 45
SLOW_TOOL_S = 15
SEEN_TURNS = 400
RECUR_TURNS = 3
RECUR_DAYS = 14
COOLDOWN_DAYS = 7
MAX_FIRES_PER_DAY = 3
DAY = 86400

INTERACTIVE_ENTRYPOINTS = {"cli", "t3-code", "sdk-ts"}
INTERACTIVE_CODEX_SOURCES = ("vscode", "cli")
AUTOMATED = ("[T3 Code:", "Context handoff (")
NOISE = ("<task-notification", "<system-reminder", "<local-command", "<command-name>", "[Request interrupted",
         "Stop hook feedback", "This session is being continued from a previous conversation")
FILE_TOOLS = {"Read", "Edit", "Write", "MultiEdit", "NotebookEdit", "FileChange", "ImageView"}
USER_TOOL = re.compile(r"^(AskUserQuestion|ExitPlanMode)$|request_secret|request_user_input")
AGENT_TOOL = re.compile(r"^(Agent|Task|wait)$|thread_wait|wait_agent|delegate_task")
TIMER_TOOL = re.compile(r"^(ScheduleWakeup|Monitor|TaskOutput|BashOutput)$|background_wait")
HEREDOC = re.compile(r"<<-?\s*(['\"]?)(\w+)\1([^\n]*)\n.*?^\s*\2\s*$", re.S | re.M)
QUOTED = re.compile(r"'[^']*'|\"(?:\\.|[^\"\\])*\"")
REDIRECT = re.compile(r"\d*>&\d*-?|\d*>>?\s*[^\s;|&()]+|(?<!<)<(?!<)\s*[^\s;|&()]+")
SPLIT = re.compile(r"\|\||&&|[;|&\n(){}]|\b(?:then|do|else)\b")
WRAPPERS = {"time", "nohup", "exec", "command", "sudo", "npx", "bunx", "pnpx", "caffeinate", "!"}
PLUMBING = {"cd", "export", "source", ".", ":", "set", "echo", "printf", "mkdir", "rm", "cat", "ls", "true", "false", "pushd",
            "popd", "if", "[", "[[", "test", "for", "while", "until", "done", "fi", "case", "esac", "sleep", "wait", "Q", "tee",
            "head", "tail", "exit", "return", "pkill", "kill", "killall", "date", "lsof", "ps", "which", "touch", "cp", "mv",
            "chmod", "ln", "wc", "sort", "uniq", "cut", "tr", "xargs", "read", "local", "unset", "trap", "break", "continue",
            "shift", "sed", "awk", "jq"}
SEARCHERS = {"grep", "rg", "find", "fd", "ag"}
VALUE_FLAGS = {"--prefix", "-C", "--cwd", "--dir", "--filter", "-w", "--workspace", "-F", "-p", "--project"}
INTERPRETERS = {"python", "python3", "node", "bun", "deno", "tsx", "bash", "sh", "zsh", "ruby", "perl"}
SCRATCH = ("/tmp/", "/private/tmp/", "/var/folders/")

RETRO = """slow-turn-retro: this turn took {active} of active work ({tools} in tool calls, {model} in model steps; \
excluded waits: {user} on the user, {timer} on timers and watchers, {agent} on subagents). Slowest calls: {slowest}.
Repeat offender: {offenders}.

Before you finish, spend at most about 3 minutes on a speedup retro for the repeat offender:
1. Diagnose why it was slow in this turn (wrong target, cold cache, serial work, a hang, queue wait, rerun after a \
preventable failure).
2. If a safe, reversible fix exists in the default path (the command, script, config, cache, parallel runner or test \
target everyone runs without passing a flag) and it sits inside the repository and scope this thread is already \
authorized to change, make it now, keep it as its own change, and verify it is faster. No opt-in flags nobody passes \
and no doc-only notes for fixable slowness.
3. If the fix belongs to shared tooling, another repository or global config, or is costly, outward-facing or risky, \
do not make it. Put the cause and the exact proposed change in your `Speedup retro:` line; this hook records that \
line for the weekly review.
4. Skip one-off scripts, finished migrations, superseded experiments and waits nobody controls. Never trade away \
accuracy, verification or scope the user asked for.
5. If a fix is not green within about 3 minutes, or it hangs or cascades, revert it and finish.

Then send ONE final message. Lead with your complete answer to the user again, because the app collapses everything \
sent before it, and end with a single line: `Speedup retro: <what got faster and by how much | proposed: cause and exact change | \
nothing safe to speed up>`."""
RESCUE = ("slow-turn-retro: your last message dropped the answer you gave before the retro, and the app has collapsed "
          "that earlier message. Send one final message that leads with that complete answer, updated for anything "
          "the retro changed, and ends with the `Speedup retro:` line.")


class Turn:
    def __init__(self, tool, key, start, interactive):
        self.tool, self.key, self.start, self.end, self.interactive = tool, key, start, start, interactive
        self.spans = []


def stamp(value):
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()
    except (AttributeError, ValueError):
        return None


def merged(spans):
    out = []
    for start, end in sorted(spans):
        if out and start <= out[-1][1]:
            out[-1][1] = max(out[-1][1], end)
        else:
            out.append([start, end])
    return out


def total(spans):
    return sum(end - start for start, end in merged(spans))


def segments(command):
    """Yield each simple command's words at command position, with heredoc bodies and quoted text removed."""
    text = REDIRECT.sub(" ", QUOTED.sub("Q", HEREDOC.sub(r"\3", command)))
    for part in SPLIT.split(text):
        words = part.split()
        while words:
            if re.match(r"^\w+=", words[0]) or words[0] in WRAPPERS:
                words = words[1:]
            elif os.path.basename(words[0]) == "heavy":
                words = words[words.index("--") + 1:] if "--" in words else []
            elif words[0] == "timeout":
                words = [w for i, w in enumerate(words[1:]) if i > 0 or not re.match(r"^[\d.]+[smhd]?$", w)]
            else:
                break
        if words:
            yield words


def watcher(words):
    head = os.path.basename(words[0])
    if head == "gh":
        return "watch" in words[1:4] or "--watch" in words
    if head == "tail":
        return any(re.match(r"^(-\w*[fF]\w*|--follow(=.*)?)$", word) for word in words[1:])
    return "--follow" in words


def signature(parts):
    """Name a shell call by the commands that could be slow in it, each as program plus two plain arguments. None for
    inline or scratch one-offs and for scripts chaining more than three commands, where the slow part is unknowable."""
    names, searcher = [], None
    for words in parts:
        program = os.path.basename(words[0])
        if program in SEARCHERS:
            searcher = searcher or program
        if program in PLUMBING or program in SEARCHERS:
            continue
        plain = [word for index, word in enumerate(words[1:]) if not word.startswith("-") and word != "Q" and words[index] not in VALUE_FLAGS]
        if any(word.startswith(SCRATCH) for word in words) or (program in INTERPRETERS and (not plain or words[1] in ("-c", "-e", "-p"))):
            return None
        script = program in INTERPRETERS and re.search(r"[/.]", plain[0])
        name = " ".join([program] + [part for part in (os.path.basename(word.rstrip("/")) for word in plain[:1 if script else 2]) if part])
        if name not in names:
            names.append(name)
    return " + ".join(names) if 0 < len(names) <= 3 else None if names else searcher


def classify(name, command, seconds):
    if name in FILE_TOOLS:
        return "file", name
    if USER_TOOL.search(name):
        return "user", name
    if AGENT_TOOL.search(name):
        return "agent", name
    if TIMER_TOOL.search(name):
        return "timer", name
    if command is None:
        return "tool", name
    parts = list(segments(command))
    if any(watcher(words) for words in parts):
        return "timer", "watch"
    sleeps = [words for words in parts if words[0] == "sleep"]
    if sleeps:
        literal = 0.0
        for words in sleeps:
            match = re.match(r"^([\d.]+)([smh]?)$", words[1]) if len(words) > 1 else None
            literal += float(match[1]) * {"": 1, "s": 1, "m": 60, "h": 3600}[match[2]] if match else 0
        if any(words[0] in ("while", "until", "for") for words in parts) or literal >= seconds / 2:
            return "timer", "sleep"
    return "shell", signature(parts)


def add_span(turn, start, end, name, command):
    kind, label = classify(name, command, end - start)
    turn.spans.append((start, end, kind, label))


def claude_prompt(record):
    """Text of a prompt that starts a turn, or None for tool results, hook feedback, notifications and local commands."""
    if record.get("isMeta") or record.get("promptSource") == "system" or record.get("turnOrigin") in ("task_notification", "peer"):
        return None
    content = (record.get("message") or {}).get("content")
    if isinstance(content, list):
        if any(isinstance(block, dict) and block.get("type") == "tool_result" for block in content):
            return None
        content = " ".join(block.get("text", "") for block in content if isinstance(block, dict))
    if not isinstance(content, str) or content.lstrip().startswith(NOISE):
        return None
    return content.lstrip()


def claude_turns(lines):
    turn, pending = None, {}
    for raw in lines:
        if raw.startswith(b'{"type":"api-request') or (b'"type":"user"' not in raw and b'"type":"assistant"' not in raw):
            continue
        try:
            record = json.loads(raw)
        except ValueError:
            continue
        kind, at = record.get("type"), stamp(record.get("timestamp"))
        if kind not in ("user", "assistant") or record.get("isSidechain") or at is None:
            continue
        text = claude_prompt(record) if kind == "user" else None
        if text is not None:
            if turn:
                yield turn
            interactive = record.get("entrypoint") in INTERACTIVE_ENTRYPOINTS and not text.startswith(AUTOMATED)
            turn, pending = Turn("claude", record.get("promptId") or record.get("uuid"), at, interactive), {}
            continue
        if not turn:
            continue
        content = (record.get("message") or {}).get("content")
        blocks = [block for block in content if isinstance(block, dict)] if isinstance(content, list) else []
        if kind == "assistant":
            for block in blocks:
                if block.get("type") == "tool_use":
                    call = block.get("input") if isinstance(block.get("input"), dict) else {}
                    pending[block.get("id")] = (at, block.get("name") or "", call.get("command") if block.get("name") == "Bash" else None)
        else:
            results = [block for block in blocks if block.get("type") == "tool_result"]
            for block in results:
                call = pending.pop(block.get("tool_use_id"), None)
                if call:
                    add_span(turn, call[0], at, call[1], call[2])
            if not results and (record.get("promptSource") == "system" or record.get("turnOrigin") in ("task_notification", "peer")):
                turn.spans.append((turn.end, at, "agent" if record.get("turnOrigin") == "peer" else "timer", "idle"))
        turn.end = max(turn.end, at)
    if turn:
        yield turn


CODEX_MARKS = (b'"session_meta"', b'"task_started"', b'"item_completed"', b'"function_call', b'"role":"user"', b'"task_complete"')


def codex_turns(lines):
    source, turn, waits = None, None, {}
    for raw in lines:
        if not any(mark in raw for mark in CODEX_MARKS):
            continue
        try:
            record = json.loads(raw)
        except ValueError:
            continue
        payload = record.get("payload") if isinstance(record.get("payload"), dict) else {}
        kind, at = payload.get("type"), stamp(record.get("timestamp"))
        if record.get("type") == "session_meta":
            source = payload.get("source")
            continue
        if at is None:
            continue
        if kind == "task_started":
            if turn:
                yield turn
            trigger = (payload.get("turn_attribution") or {}).get("turn_trigger")
            turn, waits = Turn("codex", payload.get("turn_id"), at, source in INTERACTIVE_CODEX_SOURCES and trigger in (None, "user")), {}
            continue
        if not turn:
            continue
        turn.end = max(turn.end, at)
        if kind == "message" and payload.get("role") == "user":
            parts = payload.get("content") if isinstance(payload.get("content"), list) else []
            if " ".join(part.get("text", "") for part in parts if isinstance(part, dict)).lstrip().startswith(AUTOMATED):
                turn.interactive = False
        elif kind == "item_completed":
            item = payload.get("item") or {}
            start, end = payload.get("started_at_ms"), payload.get("completed_at_ms")
            if not isinstance(start, (int, float)) or not isinstance(end, (int, float)):
                continue
            if item.get("type") == "CommandExecution":
                command = item.get("command")
                add_span(turn, start / 1000, end / 1000, "exec", command[-1] if isinstance(command, list) and command else str(command or ""))
            elif item.get("type") == "McpToolCall":
                add_span(turn, start / 1000, end / 1000, "mcp__%s__%s" % (item.get("server"), item.get("tool")), None)
            elif item.get("type") in FILE_TOOLS:
                add_span(turn, start / 1000, end / 1000, item.get("type"), None)
        elif kind == "function_call" and (AGENT_TOOL.search(payload.get("name") or "") or USER_TOOL.search(payload.get("name") or "")):
            waits[payload.get("call_id")] = (at, payload.get("name"))
        elif kind == "function_call_output" and payload.get("call_id") in waits:
            start, name = waits.pop(payload.get("call_id"))
            add_span(turn, start, at, name, None)
    if turn:
        yield turn


def parser_for(first_line):
    return codex_turns if b'"session_meta"' in first_line[:600] or first_line.startswith(b'{"timestamp"') else claude_turns


def all_turns(path):
    with open(path, "rb") as handle:
        lines = handle.read().split(b"\n")
    return list(parser_for(lines[0])(lines)) if lines else []


def last_turn(path):
    """Parse only as much of the file's tail as holds the latest turn."""
    with open(path, "rb") as handle:
        first = handle.readline()
        size, chunk = os.fstat(handle.fileno()).st_size, 1 << 18
        while True:
            start = max(0, size - chunk)
            handle.seek(start)
            lines = handle.read().split(b"\n")
            turns = list(parser_for(first)(lines if not start else [first] + lines[1:]))
            if turns or not start:
                return turns[-1] if turns else None
            chunk *= 4


def measure(turn, now=None):
    end = max(turn.end, now or 0)
    pick = lambda *kinds: [(start, stop) for start, stop, kind, _ in turn.spans if kind in kinds]
    active = max(0.0, end - turn.start - total(pick("user", "timer", "agent")))
    tools = sorted(((stop - start, label, kind) for start, stop, kind, label in turn.spans if kind in ("tool", "shell")), key=lambda t: -t[0])
    busy = merged(pick("tool", "shell", "file", "user", "timer", "agent"))
    gaps = [after - before for before, after in zip([turn.start] + [b[1] for b in busy], [b[0] for b in busy] + [end]) if after > before]
    tool_s = min(total(pick("tool", "shell")), active)
    return {
        "wall_s": round(end - turn.start, 1), "active_s": round(active, 1), "user_wait_s": round(total(pick("user")), 1),
        "timer_wait_s": round(total(pick("timer")), 1), "agent_wait_s": round(total(pick("agent")), 1),
        "tool_s": round(tool_s, 1), "model_s": round(active - tool_s, 1), "max_tool_s": round(tools[0][0], 1) if tools else 0,
        "tool_calls": sum(1 for span in turn.spans if span[3] != "idle"), "median_step_latency_s": round(statistics.median(gaps), 1) if gaps else 0,
        "slow_tools": [[label, round(seconds, 1)] for seconds, label, _ in tools[:3] if seconds >= SLOW_TOOL_S],
        "slow_commands": list(dict((label, [label, round(seconds, 1)]) for seconds, label, kind in reversed(tools)
                                   if kind == "shell" and label and seconds >= SLOW_TOOL_S).values())[::-1][:3],
    }


def gate(turn, metrics):
    if metrics["active_s"] < MIN_ACTIVE_S:
        return "under_10_min"
    if not turn.interactive:
        return "not_interactive"
    if metrics["max_tool_s"] < MIN_TOOL_S and metrics["timer_wait_s"] < MIN_TIMER_S:
        return "thinking_only"
    if metrics["median_step_latency_s"] >= MAX_STEP_LATENCY_S:
        return "provider_latency"
    return None


def launched_by_agent():
    """True when another coding agent sits above this session's own agent process, as in `claude -p` run by a thread."""
    rows = subprocess.run(["ps", "-axo", "pid=,ppid=,comm="], capture_output=True, text=True, timeout=3).stdout.splitlines()
    table = {}
    for row in rows:
        parts = row.split(None, 2)
        if len(parts) == 3 and parts[0].isdigit() and parts[1].isdigit():
            table[int(parts[0])] = (int(parts[1]), os.path.basename(parts[2].strip()))
    pid, agents = os.getppid(), 0
    while pid in table and pid > 1:
        pid, name = table[pid]
        agents += name.startswith(("claude", "codex"))
    return agents > 1


def words(text):
    return sorted(set(re.findall(r"[a-z0-9]{4,}", (text or "").lower())))[:400]


def answer_dropped(before, final):
    kept = set(words(final))
    return len(before) >= 12 and sum(word in kept for word in before) < 0.6 * len(before)


class State:
    """Fired turns, slow-command history and fire times, read and written under one lock."""

    def __enter__(self):
        HOME.mkdir(parents=True, exist_ok=True)
        self.handle = open(HOME / "state.json", "a+")
        fcntl.flock(self.handle, fcntl.LOCK_EX)
        self.handle.seek(0)
        try:
            self.data = json.loads(self.handle.read() or "{}")
        except ValueError:
            self.data = {}
        for name, empty in (("turns", {}), ("commands", {}), ("retros", {}), ("fires", [])):
            self.data.setdefault(name, empty)
        self.before = json.dumps(self.data, sort_keys=True)
        return self.data

    def __exit__(self, *error):
        data = self.data
        for key in list(data["turns"])[:-SEEN_TURNS]:
            del data["turns"][key]
        if json.dumps(data, sort_keys=True) != self.before:
            self.handle.seek(0)
            self.handle.truncate()
            self.handle.write(json.dumps(data))
        self.handle.close()


def remember_commands(data, key, metrics, now):
    for label, seconds in reversed(metrics["slow_commands"]):
        data["commands"].setdefault(label, {})[key] = [now, seconds]
    for label in list(data["commands"]):
        runs = {k: v for k, v in data["commands"][label].items() if v[0] > now - RECUR_DAYS * DAY}
        if runs:
            data["commands"][label] = runs
        else:
            del data["commands"][label]


def offenders(data, metrics, now):
    out = []
    for label, seconds in metrics["slow_commands"]:
        runs = data["commands"].get(label, {})
        if seconds >= MIN_TOOL_S and len(runs) >= RECUR_TURNS and data["retros"].get(label, 0) < now - COOLDOWN_DAYS * DAY:
            out.append([label, len(runs), round(statistics.median(run[1] for run in runs.values()))])
    return out


def clock(seconds):
    return "%dm%02ds" % divmod(int(seconds), 60)


def retro_prompt(metrics, repeat):
    slowest = ", ".join("`%s` %s" % (label or "one-off script", clock(seconds)) for label, seconds in metrics["slow_tools"]) or "none over 15s"
    names = "; ".join("`%s` was a slow call in %d turns over the last %d days (median %s)" % (label, count, RECUR_DAYS, clock(median))
                      for label, count, median in repeat)
    return RETRO.format(active=clock(metrics["active_s"]), tools=clock(metrics["tool_s"]), model=clock(metrics["model_s"]),
                        user=clock(metrics["user_wait_s"]), timer=clock(metrics["timer_wait_s"]), agent=clock(metrics["agent_wait_s"]),
                        slowest=slowest, offenders=names)


def decide(payload, turn, metrics, now):
    """Return (decision, reason, extra log fields, text to continue the turn with or None)."""
    session = str(payload.get("session_id"))
    key = "%s:%s" % (session, turn.key)
    with State() as data:
        record = data["turns"].get(key)
        if not record and payload.get("stop_hook_active"):
            open_keys = [k for k, v in data["turns"].items() if k.startswith(session + ":") and not v.get("done")]
            key, record = (open_keys[-1], data["turns"][open_keys[-1]]) if open_keys else (key, None)
        if record and record.get("done"):
            return "skip", "already_fired", {}, None
        if record:
            if payload.get("background_tasks"):
                return "skip", "retro_pending", {}, None
            if not record.get("rescued") and answer_dropped(record.get("answer", []), payload.get("last_assistant_message")):
                record["rescued"] = True
                return "rescue", "answer_dropped", {}, RESCUE
            record["done"] = True
            note = (payload.get("last_assistant_message") or "").rpartition("Speedup retro:")
            return "complete", "retro_finished", {"retro_s": round(now - record["fired"], 1), "rescued": bool(record.get("rescued")),
                                                  "offenders": record.get("offenders", []), "note": note[2].strip()[:600] if note[1] else ""}, None
        if turn.interactive:
            remember_commands(data, key, metrics, now)
        reason = gate(turn, metrics)
        if reason:
            return "skip", reason, {}, None
        repeat = offenders(data, metrics, now)
        if not repeat:
            return "skip", "no_repeat_offender", {}, None
        data["fires"] = [at for at in data["fires"] if at > now - DAY]
        if len(data["fires"]) >= MAX_FIRES_PER_DAY:
            return "skip", "daily_cap", {}, None
        if launched_by_agent():
            return "skip", "not_interactive", {}, None
        data["fires"].append(now)
        for label, _, _ in repeat:
            data["retros"][label] = now
        data["turns"][key] = {"fired": now, "answer": words(payload.get("last_assistant_message")), "offenders": [r[0] for r in repeat]}
        return "fire", "repeat_offender", {"offenders": repeat}, retro_prompt(metrics, repeat)


def log(entry):
    HOME.mkdir(parents=True, exist_ok=True)
    with open(HOME / "log.jsonl", "a") as handle:
        handle.write(json.dumps(entry) + "\n")


def hook():
    began = time.perf_counter()
    payload = {}
    try:
        payload = json.loads(sys.stdin.read() or "{}")
        if (HOME / "off").exists() or not payload.get("transcript_path"):
            return
        turn = last_turn(payload["transcript_path"])
        if not turn:
            return
        now = time.time()
        metrics = measure(turn, now)
        decision, reason, extra, text = decide(payload, turn, metrics, now)
        entry = {"ts": round(now, 1), "tool": turn.tool, "session": payload.get("session_id"), "turn": turn.key,
                 "decision": decision, "reason": reason, "cwd": payload.get("cwd")}
        entry.update(metrics)
        entry.update(extra)
        entry["hook_ms"] = round((time.perf_counter() - began) * 1000, 1)
        log(entry)
        if text:
            print(json.dumps({"decision": "block", "reason": text}))
    except Exception as error:  # a broken retro must never hold a turn open
        try:
            log({"ts": round(time.time(), 1), "decision": "error", "reason": repr(error)[:300], "session": payload.get("session_id")})
        except Exception:
            pass


def dry_run(path):
    turn = last_turn(path)
    if not turn:
        print(json.dumps({"decision": "skip", "reason": "no_turn"}))
        return
    metrics = measure(turn)
    reason = gate(turn, metrics)
    if not reason:
        with State() as data:
            reason = None if offenders(data, metrics, turn.end) else "no_repeat_offender"
    metrics.update({"tool": turn.tool, "interactive": turn.interactive, "decision": "skip" if reason else "fire", "reason": reason or "repeat_offender"})
    print(json.dumps(metrics))


def transcripts(since):
    paths = glob.glob(str(Path.home() / ".claude/projects/*/*.jsonl")) + glob.glob(str(Path.home() / ".codex/sessions/*/*/*/*.jsonl"))
    return [path for path in paths if os.path.getmtime(path) >= since]


def report(days):
    """Compare each retro'd command's run time before and after its retro, against the time the retros cost."""
    now = time.time()
    since = now - days * DAY
    entries = []
    if (HOME / "log.jsonl").exists():
        for line in (HOME / "log.jsonl").read_text().splitlines():
            try:
                entries.append(json.loads(line))
            except ValueError:
                pass
    window = [entry for entry in entries if entry.get("ts", 0) >= since]
    fires = [entry for entry in window if entry.get("decision") == "fire"]
    done = {(entry.get("session"), entry.get("turn")): entry for entry in window if entry.get("decision") == "complete"}
    runs, slow_days = {}, {}
    installed = min((entry["ts"] for entry in entries if "ts" in entry), default=now)
    for path in transcripts(min(since - RECUR_DAYS * DAY, installed - days * DAY)):
        try:
            turns = all_turns(path)
        except OSError:
            continue
        for turn in turns:
            for start, stop, kind, label in turn.spans:
                if kind == "shell" and label:
                    runs.setdefault(label, []).append((start, stop - start))
            if turn.interactive and turn.start >= installed - days * DAY and measure(turn)["active_s"] >= MIN_ACTIVE_S:
                slow_days.setdefault("after" if turn.start >= installed else "before", []).append(turn.start)
    rows, saved, cost = [], 0.0, 0.0
    for fire in fires:
        finished = done.get((fire.get("session"), fire.get("turn")))
        cost += finished["retro_s"] if finished else 0
        for label, _, _ in fire.get("offenders", []):
            before = [seconds for at, seconds in runs.get(label, []) if fire["ts"] - RECUR_DAYS * DAY <= at < fire["ts"] - fire["wall_s"]]
            after = [seconds for at, seconds in runs.get(label, []) if at > (finished or fire)["ts"]]
            row = {"command": label, "fired": datetime.fromtimestamp(fire["ts"]).strftime("%Y-%m-%d %H:%M"), "retro_s": finished and finished["retro_s"],
                   "before_n": len(before), "after_n": len(after), "before_median_s": before and round(statistics.median(before), 1),
                   "after_median_s": after and round(statistics.median(after), 1), "saved_s": None}
            if len(before) >= 3 and len(after) >= 3:
                change = statistics.median(before) - statistics.median(after)
                row["saved_s"] = round(change * len(after), 1) if abs(change) >= 0.2 * statistics.median(before) else 0.0
                saved += row["saved_s"]
            rows.append(row)
    measured = [row for row in rows if row["saved_s"] is not None]
    if not measured:
        verdict = "inconclusive"
        why = "no retro fired" if not fires else "no retro'd command has 3+ runs both before and after its retro yet"
    else:
        verdict = "effective" if saved > cost else "not_effective"
        why = "measured commands saved %s against %s spent on retros" % (clock(max(saved, 0)), clock(cost))
    timings = sorted(entry["hook_ms"] for entry in window if "hook_ms" in entry)
    skips = {}
    for entry in window:
        if entry.get("decision") == "skip":
            skips[entry["reason"]] = skips.get(entry["reason"], 0) + 1
    span = lambda name, length: round(len(slow_days.get(name, [])) / max(length / DAY, 1e-9), 1)
    print(json.dumps({
        "verdict": verdict, "why": why, "window_days": days, "stops_logged": len(window), "fires": len(fires), "completed": len(done),
        "rescued": sum(1 for entry in done.values() if entry.get("rescued")), "errors": sum(1 for entry in window if entry.get("decision") == "error"),
        "retro_cost_s": round(cost, 1), "saved_s": round(saved, 1), "commands": rows, "skips": skips,
        "hook_ms_median": timings[len(timings) // 2] if timings else None, "hook_ms_p95": timings[int(len(timings) * 0.95)] if timings else None,
        "slow_turns_per_day": {"before": span("before", days * DAY), "after": span("after", now - installed)},
        "retro_notes": [{"commands": entry.get("offenders"), "note": entry.get("note")} for entry in done.values()],
    }, indent=1))


if __name__ == "__main__":
    if sys.argv[1:2] == ["--dry-run"] and len(sys.argv) == 3:
        dry_run(sys.argv[2])
    elif sys.argv[1:2] == ["--report"]:
        report(int(sys.argv[2]) if len(sys.argv) > 2 else 7)
    else:
        hook()
