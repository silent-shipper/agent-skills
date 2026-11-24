import importlib.util
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/heavy.py"
spec = importlib.util.spec_from_file_location("heavy", SCRIPT)
heavy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(heavy)


class Clock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now

    def sleep(self, seconds):
        self.now += seconds


class LaneTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)

    def test_browser_simulator_and_script_work_runs_one_at_a_time(self):
        (self.root / "check.sh").write_text("bun run build\n")
        (self.root / "check").write_text("#!/usr/bin/env bash\nbun run build\n")
        (self.root / "ux.spec.js").write_text("const puppeteer = require('puppeteer')\n")
        for command in (["bunx", "playwright", "test"], ["bun", "run", "test:e2e"], ["xcodebuild", "test"],
                        ["npx", "expo", "run:ios"], ["./check.sh"], ["./check"], ["bash", "-c", "bun run build"],
                        ["node", "ux.spec.js"]):
            self.assertEqual(heavy.lane(command, self.root), "browser", command)

    def test_builds_suites_and_typechecks_share_the_work_lane(self):
        (self.root / "build.mjs").write_text("import {build} from 'esbuild'\n")
        for command in (["bun", "run", "build"], ["next", "build"], ["bunx", "vitest", "run"], ["tsc", "--noEmit"],
                        ["node", "build.mjs"], ["./node_modules/.bin/vitest", "run"]):
            self.assertEqual(heavy.lane(command, self.root), "work", command)


class CapacityTests(unittest.TestCase):
    def wait(self, samples, floor=4096):
        clock, said = Clock(), []
        samples = iter(samples)
        waited = heavy.wait_for_calm(sample=lambda: next(samples), sleep=clock.sleep, clock=clock, floor=floor,
                                     say=said.append)
        return waited, said

    def test_a_calm_mac_starts_at_once(self):
        self.assertEqual(self.wait([(6.0, 12, 8000)]), (0, []))

    def test_high_load_or_low_memory_waits_until_it_clears(self):
        waited, said = self.wait([(20.0, 12, 8000)] * 3 + [(10.0, 12, 8000)])
        self.assertEqual(waited, 3 * heavy.POLL_SECONDS)
        self.assertIn("load 20.0 on 12 cores", said[0])
        waited, _ = self.wait([(2.0, 12, 1000)] * 2 + [(2.0, 12, 5000)])
        self.assertEqual(waited, 2 * heavy.POLL_SECONDS)

    def test_a_busy_mac_delays_work_for_at_most_five_minutes(self):
        waited, said = self.wait([(40.0, 12, 8000)] * 1000)
        self.assertEqual(waited, heavy.CALM_WAIT_SECONDS)
        self.assertEqual(len(said), heavy.CALM_WAIT_SECONDS // 60 + 1)
        self.assertIn("starting anyway", said[-1])


class IdleSimulatorTests(unittest.TestCase):
    def test_idle_decision(self):
        minute = 60
        self.assertEqual(heavy.idle_action(False, False, 0, 99 * minute), "clear")
        self.assertEqual(heavy.idle_action(True, True, 0, 99 * minute), "mark")
        self.assertEqual(heavy.idle_action(True, False, None, 0), "mark")
        self.assertEqual(heavy.idle_action(True, False, 0, 29 * minute), "wait")
        self.assertEqual(heavy.idle_action(True, False, 0, 31 * minute), "shutdown")

    def test_simulator_users(self):
        users = ["/usr/bin/xcrun simctl spawn booted log stream",
                 "/Applications/Xcode.app/Contents/Developer/usr/bin/xcodebuild test -scheme App",
                 "node /Users/me/.near-verify/toolkit/abc/src/test-job.mjs /Users/me/.near-verify/queue/x.json",
                 "node node_modules/expo/bin/cli start --port 8081", "npx expo run:ios", "maestro test flow.yaml"]
        others = ["/Library/Developer/PrivateFrameworks/CoreSimulator.framework/Versions/A/XPCServices/"
                  "com.apple.CoreSimulator.CoreSimulatorService.xpc/Contents/MacOS/com.apple.CoreSimulator.CoreSimulatorService",
                  "launchd_sim /Users/me/Library/Developer/CoreSimulator/Devices/X/data/var/run/launchd_bootstrap.plist",
                  "node tests/test-jobs.spec.js", "vim simctl-notes.md"]
        for row in users:
            self.assertTrue(heavy.SIM_USERS.search(row), row)
        for row in others:
            self.assertFalse(heavy.SIM_USERS.search(row), row)

    def test_idle_check_marks_busy_then_shuts_down_every_booted_simulator(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        calls = []
        booted = [("A", "near-verify iPhone"), ("B", "nav-experiment iPhone")]

        def fake_run(args, **kwargs):
            calls.append(args)
            return subprocess.CompletedProcess(args, 0, "", "")

        with patch.object(heavy, "STATE", Path(directory.name)), patch.object(heavy, "booted_simulators", lambda: booted), \
                patch.object(heavy.subprocess, "run", fake_run), patch("builtins.print"):
            with patch.object(heavy, "simulator_in_use", lambda: True):
                heavy.idle_sim(now=lambda: 1000.0)
            with patch.object(heavy, "simulator_in_use", lambda: False):
                heavy.idle_sim(now=lambda: 1000.0 + 29 * 60)
                self.assertEqual(calls, [])
                heavy.idle_sim(now=lambda: 1000.0 + 31 * 60)
        self.assertEqual(calls, [["xcrun", "simctl", "shutdown", "A"], ["xcrun", "simctl", "shutdown", "B"]])
        self.assertFalse((Path(directory.name) / "sim-last-busy").exists())


@unittest.skipUnless(shutil.which("ts"), "Task Spooler is not installed")
class QueueTests(unittest.TestCase):
    """Runs real jobs through Task Spooler in a private state directory."""

    def setUp(self):
        self.home = Path(tempfile.mkdtemp(prefix="heavy-", dir="/tmp"))
        self.addCleanup(self.stop_servers)
        self.env = {**os.environ, "HOME": str(self.home), "HEAVY_MAX_WAIT_SECONDS": "0"}
        self.env.pop("HEAVY_JOB", None)

    def stop_servers(self):
        for lane in heavy.LANES:
            socket = self.home / f".local/state/heavy/{lane}.socket"
            if socket.exists():
                subprocess.run(["ts", "-K"], env={**self.env, "TS_SOCKET": str(socket)}, capture_output=True)
        shutil.rmtree(self.home, ignore_errors=True)

    def heavy(self, *args, **kwargs):
        return subprocess.Popen([sys.executable, str(SCRIPT), *args], env=self.env, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, text=True, cwd=self.home, **kwargs)

    def test_runs_here_and_keeps_the_exit_code_and_output(self):
        job = self.heavy("--", "sh", "-c", "echo \"in $PWD as $HEAVY_JOB\"; exit 3")
        out, err = job.communicate(timeout=360)
        self.assertEqual(job.returncode, 3, err)
        self.assertIn(f"in {os.path.realpath(self.home)} as browser", out)

    def test_stopping_heavy_stops_the_job_it_queued(self):
        # Task Spooler runs a job in its own process group, so before the supervisor a Ctrl-C or an agent timeout
        # left the job running while its slot was handed to the next one.
        marker = f"sleep {41 + os.getpid() % 50}"

        def survivors():
            rows = subprocess.run(["ps", "-Ao", "args="], capture_output=True, text=True).stdout.splitlines()
            return [row for row in rows if row.strip() == marker]

        for sig in (signal.SIGINT, signal.SIGKILL):
            job = self.heavy("--", *marker.split(), start_new_session=True)
            deadline = time.monotonic() + 60
            while not survivors() and time.monotonic() < deadline:
                time.sleep(0.2)
            self.assertTrue(survivors(), "the job never started")
            os.killpg(job.pid, sig)
            job.wait(timeout=10)
            deadline = time.monotonic() + 10
            while survivors() and time.monotonic() < deadline:
                time.sleep(0.2)
            self.assertEqual(survivors(), [], sig)

    def test_two_work_jobs_run_while_a_third_waits(self):
        jobs = [self.heavy("--", "sleep", "6") for _ in range(3)]
        deadline = time.monotonic() + 300
        listing = ""
        while time.monotonic() < deadline:
            listing = subprocess.run([sys.executable, str(SCRIPT), "status"], env=self.env, capture_output=True,
                                     text=True).stdout
            if listing.count("running") == 2 and listing.count("queued") == 1:
                break
            time.sleep(0.2)
        for job in jobs:
            job.communicate(timeout=400)
        self.assertEqual((listing.count("running"), listing.count("queued")), (2, 1), listing)
        self.assertTrue(all(job.returncode == 0 for job in jobs))


if __name__ == "__main__":
    unittest.main()
