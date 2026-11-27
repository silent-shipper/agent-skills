import contextlib
import importlib.util
import io
import json
from datetime import datetime, timezone
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location("slow_turn_retro", Path(__file__).resolve().parents[1] / "scripts/slow-turn-retro.py")
retro = importlib.util.module_from_spec(spec)
spec.loader.exec_module(retro)

T0 = 1_800_000_000.0
ANSWER = ("The checkout migration is finished: orders now write through the ledger service, the nightly reconciliation "
          "job passes against production snapshots, and rollback instructions live beside the deployment runbook.")


def iso(offset):
    return datetime.fromtimestamp(T0 + offset, timezone.utc).isoformat().replace("+00:00", "Z")


class Claude:
    """Builds a Claude Code transcript: one prompt, then tool calls placed at explicit second offsets."""

    def __init__(self, prompt="fix the build", entrypoint="t3-code", prompt_id="p1"):
        self.lines, self.calls, self.prompt_id, self.entrypoint = [], 0, prompt_id, entrypoint
        self.add({"type": "user", "promptId": prompt_id, "promptSource": "sdk", "turnOrigin": "sdk",
                  "message": {"role": "user", "content": prompt}}, 0)

    def add(self, record, offset):
        record.update(timestamp=iso(offset), entrypoint=self.entrypoint)
        self.lines.append(json.dumps(record, separators=(",", ":")))

    def tool(self, name, start, end, command=None):
        self.calls += 1
        call = "toolu_%d" % self.calls
        block = {"type": "tool_use", "id": call, "name": name, "input": {"command": command} if command else {}}
        self.add({"type": "assistant", "message": {"id": "m%d" % self.calls, "content": [block]}}, start)
        self.add({"type": "user", "promptId": self.prompt_id,
                  "message": {"role": "user", "content": [{"type": "tool_result", "tool_use_id": call, "content": "ok"}]}}, end)
        return self

    def say(self, text, offset):
        self.add({"type": "assistant", "message": {"id": "say", "content": [{"type": "text", "text": text}]}}, offset)
        return self

    def turn(self):
        return list(retro.claude_turns([line.encode() for line in self.lines]))[-1]

    def write(self, directory):
        path = Path(directory) / "session.jsonl"
        path.write_text("\n".join(self.lines) + "\n")
        return str(path)


def slow_turn(**options):
    """Twelve active minutes with a four-minute test run and steady short model steps."""
    session = Claude(**options).tool("Bash", 5, 245, "npm run test")
    for index in range(40):
        session.tool("Bash", 250 + index * 12, 258 + index * 12, "git status")
    return session.say(ANSWER, 730)


class Timing(unittest.TestCase):
    def test_active_time_excludes_user_timer_and_subagent_waits(self):
        turn = (Claude().tool("Bash", 10, 110, "npm run build").tool("AskUserQuestion", 120, 420)
                .tool("Bash", 430, 730, "sleep 300").tool("Agent", 740, 940).say("done", 1000).turn())
        metrics = retro.measure(turn)
        self.assertEqual((metrics["wall_s"], metrics["active_s"]), (1000, 200))
        self.assertEqual((metrics["user_wait_s"], metrics["timer_wait_s"], metrics["agent_wait_s"]), (300, 300, 200))
        self.assertEqual((metrics["tool_s"], metrics["model_s"], metrics["max_tool_s"], metrics["tool_calls"]), (100, 100, 100, 4))
        self.assertEqual(metrics["slow_tools"], [["npm run build", 100]])

    def test_overlapping_watches_are_subtracted_once(self):
        turn = (Claude().tool("Bash", 0, 600, "gh run watch 123").tool("Bash", 100, 700, "gh pr checks 9 --watch")
                .say("done", 800).turn())
        metrics = retro.measure(turn)
        self.assertEqual((metrics["timer_wait_s"], metrics["active_s"]), (700, 100))

    def test_idle_wait_for_a_background_task_is_not_active(self):
        session = Claude().say("started the build in the background", 20)
        session.add({"type": "user", "promptSource": "system", "turnOrigin": "task_notification",
                     "message": {"role": "user", "content": "<task-notification>done</task-notification>"}}, 920)
        metrics = retro.measure(session.say("build passed", 940).turn())
        self.assertEqual((metrics["timer_wait_s"], metrics["active_s"]), (900, 40))

    def test_file_tools_never_count_as_slow_tools(self):
        turn = Claude().tool("Edit", 0, 400).tool("Write", 0, 400).tool("Bash", 410, 430, "bun test").say("done", 440).turn()
        metrics = retro.measure(turn)
        self.assertEqual((metrics["max_tool_s"], metrics["slow_tools"]), (20, [["bun test", 20]]))

    def test_hook_feedback_and_notifications_do_not_start_a_turn(self):
        session = Claude().tool("Bash", 5, 50, "npm run test")
        session.add({"type": "user", "isMeta": True, "message": {"role": "user", "content": "Stop hook feedback:\nretro"}}, 60)
        session.add({"type": "user", "message": {"role": "user", "content": "<system-reminder>note</system-reminder>"}}, 70)
        turn = session.say("done", 80).turn()
        self.assertEqual((turn.key, turn.start, turn.end), ("p1", T0, T0 + 80))


class Commands(unittest.TestCase):
    def kind(self, command, seconds=600):
        return retro.classify("Bash", command, seconds)[0]

    def test_ci_watchers_match_only_at_command_position(self):
        for command in ("gh run watch 42", "cd app && gh pr checks 7 --watch", "FOO=1 timeout 900 gh run watch",
                        "tail -f build.log", "tail -n 50 -F out.log", "kubectl logs pod --follow"):
            self.assertEqual(self.kind(command), "timer", command)
        for command in ('echo "next: gh run watch 42"', "git commit -m 'run gh pr checks --watch later'",
                        "cat > notes.md <<'EOF'\ngh run watch 42\ntail -f build.log\nEOF\nnpm run build",
                        "tail -n 50 build.log", "gh pr view 7"):
            self.assertEqual(self.kind(command), "shell", command)

    def test_sleep_is_a_wait_only_when_it_dominates_or_loops(self):
        self.assertEqual(self.kind("sleep 300", 301), "timer")
        self.assertEqual(self.kind("until gh run view 5 --json status | grep -q completed; do sleep 30; done", 900), "timer")
        self.assertEqual(self.kind("npm run build && sleep 2 && curl -s localhost:3000", 240), "shell")

    def test_signatures_name_repeatable_commands_and_drop_one_offs(self):
        name = lambda command: retro.classify("Bash", command, 60)[1]
        self.assertEqual(name("cd /repo/app && CI=1 npm run test -- --watch=false"), "npm run test")
        self.assertEqual(name("heavy --browser -- bunx playwright test e2e/login.spec.ts"), "playwright test login.spec.ts")
        self.assertEqual(name("mkdir -p out; python3 scripts/report.py --days 7"), "python3 report.py")
        self.assertEqual(name("cd app || exit 1; npm --prefix web run lint 2>&1 | tail -20"), "npm run lint")
        self.assertEqual(name("bun run lint && bun run typecheck > out.log 2>&1"), "bun run lint + bun run typecheck")
        self.assertEqual(name("grep -rn TODO src packages"), "grep")
        self.assertEqual(name("npm run queue -- swap | grep -c passed"), "npm run queue")
        self.assertIsNone(name("a.sh && b.sh && c.sh && d.sh"))
        self.assertIsNone(name("python3 - <<'EOF'\nprint(1)\nEOF"))
        self.assertIsNone(name("cat > /tmp/x.py <<'EOF'\nprint(1)\nEOF\npython3 /tmp/x.py"))


class Gates(unittest.TestCase):
    def reason(self, session):
        turn = session.turn()
        return retro.gate(turn, retro.measure(turn))

    def test_short_turn(self):
        self.assertEqual(self.reason(Claude().tool("Bash", 5, 400, "npm run test").say("done", 590)), "under_10_min")

    def test_headless_and_automated_turns(self):
        self.assertEqual(self.reason(slow_turn(entrypoint="sdk-cli")), "not_interactive")
        self.assertEqual(self.reason(slow_turn(prompt='[T3 Code: scheduled task "x" sent this prompt] check prices')), "not_interactive")

    def test_thinking_only_turn_even_with_a_question_answered(self):
        session = Claude().tool("AskUserQuestion", 10, 200)
        for index in range(50):
            session.tool("Bash", 210 + index * 16, 220 + index * 16, "git status")
        self.assertEqual(self.reason(session.say("done", 1020)), "thinking_only")

    def test_timer_polled_remote_job_is_not_thinking_only(self):
        session = Claude().tool("Bash", 10, 100, "sleep 90")
        for index in range(60):
            session.tool("Bash", 110 + index * 12, 118 + index * 12, "git status")
        self.assertIsNone(self.reason(session.say("done", 840)))

    def test_provider_latency(self):
        session = Claude()
        for index in range(12):
            session.tool("Bash", 60 + index * 100, 100 + index * 100, "npm run test")
        self.assertEqual(self.reason(session.say("done", 1300)), "provider_latency")

    def test_slow_tool_turn_passes(self):
        self.assertIsNone(self.reason(slow_turn()))


class Hook(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.home = Path(directory.name)
        for patcher in (patch.object(retro, "HOME", self.home), patch.object(retro, "launched_by_agent", lambda: False)):
            patcher.start()
            self.addCleanup(patcher.stop)

    def stop(self, session, at, message=ANSWER, active=False, **payload):
        payload.update(session_id="s1", transcript_path=session.write(self.home), stop_hook_active=active, last_assistant_message=message)
        output = io.StringIO()
        with patch("sys.stdin", io.StringIO(json.dumps(payload))), patch("time.time", lambda: T0 + at), contextlib.redirect_stdout(output):
            retro.hook()
        return json.loads(output.getvalue()) if output.getvalue() else None

    def log(self):
        return [json.loads(line) for line in (self.home / "log.jsonl").read_text().splitlines()]

    def seed(self, command="npm run test", turns=2):
        with retro.State() as data:
            data["commands"][command] = {"old:%d" % index: [T0 - retro.DAY, 200] for index in range(turns)}

    def test_first_sightings_only_log(self):
        self.assertIsNone(self.stop(slow_turn(), 731))
        self.assertEqual((self.log()[0]["decision"], self.log()[0]["reason"]), ("skip", "no_repeat_offender"))

    def test_repeat_offender_fires_once_then_logs_retro_seconds(self):
        self.seed()
        session = slow_turn()
        fired = self.stop(session, 731)
        self.assertEqual(fired["decision"], "block")
        self.assertIn("`npm run test` was a slow call in 3 turns", fired["reason"])
        self.assertIn("12m11s of active work", fired["reason"])
        session.say(ANSWER + "\n\nSpeedup retro: nothing safe to speed up.", 850)
        self.assertIsNone(self.stop(session, 851, ANSWER + "\n\nSpeedup retro: nothing safe to speed up.", active=True))
        self.assertIsNone(self.stop(session, 900, "ok"))
        entries = self.log()
        self.assertEqual([entry["decision"] for entry in entries], ["fire", "complete", "skip"])
        self.assertEqual((entries[1]["retro_s"], entries[1]["rescued"], entries[2]["reason"]), (120, False, "already_fired"))
        self.assertEqual(entries[1]["note"], "nothing safe to speed up.")

    def test_dropped_answer_is_rescued_once(self):
        self.seed()
        session = slow_turn()
        self.stop(session, 731)
        rescue = self.stop(session, 800, "Speedup retro: cached the test database.", active=True)
        self.assertIn("dropped the answer", rescue["reason"])
        self.assertIsNone(self.stop(session, 860, "Speedup retro: cached the test database.", active=True))
        entries = self.log()
        self.assertEqual([entry["decision"] for entry in entries], ["fire", "rescue", "complete"])
        self.assertEqual((entries[2]["retro_s"], entries[2]["rescued"]), (129, True))

    def test_closing_stop_waits_for_background_tasks(self):
        self.seed()
        session = slow_turn()
        self.stop(session, 731)
        self.assertIsNone(self.stop(session, 800, active=True, background_tasks=[{"id": "b1"}]))
        self.stop(session, 900, active=True)
        self.assertEqual([entry["reason"] for entry in self.log()], ["repeat_offender", "retro_pending", "retro_finished"])

    def test_continuation_with_a_new_turn_id_still_closes_the_retro(self):
        self.seed()
        self.stop(slow_turn(), 731)
        self.stop(Claude(prompt="continue", prompt_id="p2").say(ANSWER, 5), 760, active=True)
        self.assertEqual(self.log()[-1]["decision"], "complete")

    def test_cooldown_daily_cap_and_nested_runs_do_not_fire(self):
        self.seed()
        self.assertIsNotNone(self.stop(slow_turn(), 731))
        self.assertIsNone(self.stop(slow_turn(prompt_id="p2"), 731, session_id="s2"))
        self.seed("npm run lint", 3)
        with retro.State() as data:
            data["fires"] = [T0 + 700] * retro.MAX_FIRES_PER_DAY
        lint = Claude(prompt_id="p3").tool("Bash", 5, 245, "npm run lint")
        for index in range(40):
            lint.tool("Bash", 250 + index * 12, 258 + index * 12, "git status")
        self.assertIsNone(self.stop(lint.say(ANSWER, 730), 731))
        with retro.State() as data:
            data["fires"] = []
        with patch.object(retro, "launched_by_agent", lambda: True):
            self.assertIsNone(self.stop(lint, 731))
        self.assertEqual([entry["reason"] for entry in self.log()], ["repeat_offender", "no_repeat_offender", "daily_cap", "not_interactive"])

    def test_broken_input_fails_open_and_off_switch_silences_the_hook(self):
        with patch("sys.stdin", io.StringIO("not json")), contextlib.redirect_stdout(io.StringIO()) as output:
            retro.hook()
        self.assertEqual((output.getvalue(), self.log()[0]["decision"]), ("", "error"))
        self.seed()
        (self.home / "off").touch()
        self.assertIsNone(self.stop(slow_turn(), 731))
        self.assertEqual(len(self.log()), 1)


class Codex(unittest.TestCase):
    def lines(self, source="vscode", prompt="fix the build", trigger=None):
        row = lambda offset, kind, payload: json.dumps({"timestamp": iso(offset), "type": kind, "payload": payload}, separators=(",", ":")).encode()
        item = lambda start, end, body: row(end, "event_msg", {"type": "item_completed", "started_at_ms": (T0 + start) * 1000,
                                                               "completed_at_ms": (T0 + end) * 1000, "item": body})
        return [
            row(-5, "session_meta", {"source": source}),
            row(0, "event_msg", {"type": "task_started", "turn_id": "t1", "turn_attribution": {"turn_trigger": trigger}}),
            row(1, "response_item", {"type": "message", "role": "user", "content": [{"type": "input_text", "text": prompt}]}),
            item(10, 310, {"type": "CommandExecution", "command": ["/bin/zsh", "-lc", "cd app && bun run build"]}),
            item(320, 330, {"type": "FileChange", "changes": {}}),
            item(340, 400, {"type": "McpToolCall", "server": "t3-code", "tool": "preview_act"}),
            row(410, "response_item", {"type": "function_call", "name": "wait", "call_id": "c1"}),
            row(710, "response_item", {"type": "function_call_output", "call_id": "c1"}),
            row(1000, "event_msg", {"type": "task_complete", "turn_id": "t1"}),
        ]

    def test_turn_timing_and_slow_tools(self):
        turn = list(retro.codex_turns(self.lines()))[-1]
        metrics = retro.measure(turn)
        self.assertEqual((turn.tool, turn.key, turn.interactive), ("codex", "t1", True))
        self.assertEqual((metrics["wall_s"], metrics["agent_wait_s"], metrics["active_s"], metrics["max_tool_s"]), (1000, 300, 700, 300))
        self.assertEqual(metrics["slow_tools"], [["bun run build", 300], ["mcp__t3-code__preview_act", 60]])
        self.assertEqual(metrics["slow_commands"], [["bun run build", 300]])

    def test_exec_subagent_and_agent_sent_turns_are_not_interactive(self):
        for options in ({"source": "exec"}, {"source": {"subagent": {"other": "guardian"}}}, {"trigger": "guardian_review"},
                        {"prompt": '[T3 Code: the agent in T3 thread "x" sent this message, not the user] go'}):
            self.assertFalse(list(retro.codex_turns(self.lines(**options)))[-1].interactive, options)

    def test_tail_read_keeps_the_session_header(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "rollout.jsonl"
            padding = json.dumps({"timestamp": iso(-3), "type": "response_item", "payload": {"type": "reasoning", "x": "y" * 2000}}).encode()
            lines = self.lines()
            path.write_bytes(b"\n".join(lines[:1] + [padding] * 400 + lines[1:]) + b"\n")
            turn = retro.last_turn(str(path))
            self.assertEqual((turn.key, turn.interactive, len(turn.spans)), ("t1", True, 4))


if __name__ == "__main__":
    unittest.main()
