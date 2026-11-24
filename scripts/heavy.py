#!/usr/bin/env python3
"""Run heavy commands through this Mac's queue, and shut down iOS simulators nothing is using.

  heavy [--browser] -- COMMAND...  Wait for a slot in COMMAND's lane and for a calm Mac, then run COMMAND here and exit
                                   with its code. Browser, simulator and shell-script work runs one at a time; builds,
                                   test suites and typechecks run two at a time.
  heavy status                     Running and waiting jobs in each lane, and the Mac's load.
  heavy idle-sim                   Shut down every booted simulator once nothing has used one for 30 minutes
                                   (launchd runs this every 5 minutes).

HEAVY_MAX_WAIT_SECONDS sets how long a job waits for a calm Mac before starting anyway (default 300).
"""
import argparse
import json
import os
import re
import shlex
import signal
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

STATE = Path.home() / ".local/state/heavy"
LANES = {"browser": 1, "work": 2}
LOAD_LIMIT_PER_CPU = 1.25
CALM_WAIT_SECONDS = 300
POLL_SECONDS = 5
SIM_IDLE_SECONDS = 30 * 60
SHELLS = {"sh", "bash", "zsh", "dash"}
SCRIPT_HOSTS = {"node", "bun", "tsx", "deno"}
BROWSER_WORK = re.compile(r"playwright|puppeteer|chrom|e2e|simctl|xcodebuild|maestro|detox|appium|run-ios|run:ios", re.I)
BROWSER_IMPORT = re.compile(r"""(?:from\s*|require\(\s*|import\(\s*)['"](?:@playwright/test|playwright(?:-core)?|"""
                            r"""puppeteer(?:-core)?|chrome-launcher|selenium-webdriver)['"]|chrome-headless-shell""")
SHELL_SHEBANG = re.compile(r"^#!.*\b(?:ba|z|da)?sh\b")
# Processes that drive a simulator. A near-verify worker (test-job) may be running an iOS journey.
SIM_USERS = re.compile(r"(?:^|[\s/])(?:xcodebuild|simctl|maestro|detox|appium)(?:\s|$)|\bexpo(?:/bin/cli)?\s+(?:start|run:ios)\b"
                       r"|\brun-ios\b|/test-job\.(?:mjs|ts)\b")
SIMULATOR_APP = "com.apple.iphonesimulator"


def script_file(words, cwd):
    """The file a command runs as a script (`sh x.sh`, `./x.sh`, `node x.mjs`), or None."""
    while words and re.match(r"^\w+=", words[0]):
        words = words[1:]
    if not words:
        return None
    name = os.path.basename(words[0])
    if name in SHELLS | SCRIPT_HOSTS:
        if name in SHELLS and "-c" in words:
            return None
        target = next((w for w in words[1:] if not w.startswith("-")), None)
    elif "/" in words[0]:
        target = words[0]
    else:
        return None
    path = Path(cwd) / os.path.expanduser(target) if target else None
    return path if path and path.is_file() else None


def read_script(path):
    try:
        with open(path, errors="ignore") as handle:
            return handle.read(1 << 20)
    except OSError:
        return ""


def is_shell_script(path):
    return path.suffix == ".sh" or bool(SHELL_SHEBANG.match(read_script(path)))


def loads_browser(path):
    """Whether a script file starts a browser itself (Playwright, Puppeteer, headless Chrome)."""
    return bool(BROWSER_IMPORT.search(read_script(path)))


def lane(command, cwd):
    """`browser` for anything that drives a browser or simulator, and for shell scripts, whose contents can change;
    `work` for builds, test suites and typechecks."""
    if BROWSER_WORK.search(" ".join(command)):
        return "browser"
    script = script_file(command, cwd)
    if os.path.basename(command[0]) in SHELLS or script and (is_shell_script(script) or loads_browser(script)):
        return "browser"
    return "work"


def lane_environment(name):
    return {**os.environ, "TS_SOCKET": str(STATE / f"{name}.socket"), "TS_MAXFINISHED": "50"}


def host_load():
    """The 1-minute load, the CPU count and free memory in MiB as macOS's memory pressure level reports it."""
    total = os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES")
    try:
        level = int(subprocess.run(["/usr/sbin/sysctl", "-n", "kern.memorystatus_level"], capture_output=True,
                                   text=True, timeout=2).stdout)
    except (OSError, ValueError, subprocess.SubprocessError):
        level = 100
    return os.getloadavg()[0], os.cpu_count() or 1, total * level // 100 >> 20


def memory_floor_mib():
    return os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES") // 4 >> 20


def wait_for_calm(sample=host_load, sleep=time.sleep, clock=time.monotonic, floor=None, say=None, max_wait=None):
    """Hold a job while load per CPU is over the limit or free memory is under a quarter of RAM, for at most 5 minutes
    so a busy Mac slows work down instead of stopping it. Returns the seconds waited."""
    floor = memory_floor_mib() if floor is None else floor
    max_wait = float(os.environ.get("HEAVY_MAX_WAIT_SECONDS", CALM_WAIT_SECONDS)) if max_wait is None else max_wait
    say = say or (lambda text: print(text, file=sys.stderr, flush=True))
    started, noted = clock(), None
    while True:
        load, cpus, free = sample()
        waited = clock() - started
        if load / cpus <= LOAD_LIMIT_PER_CPU and free >= floor:
            return waited
        if waited >= max_wait:
            if max_wait:
                say(f"[heavy] the Mac is still busy after {waited / 60:.0f} minutes; starting anyway")
            return waited
        if noted is None or waited - noted >= 60:
            say(f"[heavy] waiting for a calm Mac: load {load:.1f} on {cpus} cores, {free} MiB free")
            noted = waited
        sleep(POLL_SECONDS)


def lane_jobs(name):
    """(state, label) of each queued or running job in a lane; empty when the lane has never run."""
    if not (STATE / f"{name}.socket").exists():
        return []
    try:
        listing = subprocess.run(["ts", "-l"], env=lane_environment(name), capture_output=True, text=True,
                                 timeout=5).stdout
    except (OSError, subprocess.SubprocessError):
        return []
    return re.findall(r"(?m)^\s*\d+\s+(queued|running)\s.*?\[([^\]]*)\]", listing)


def run(command, browser=False):
    if os.environ.get("HEAVY_JOB"):
        # Already inside a queued job, which holds the slot: waiting for another would deadlock the browser lane.
        os.execvp(command[0], command)
    chosen = "browser" if browser else lane(command, os.getcwd())
    env = {**lane_environment(chosen), "HEAVY_JOB": chosen}
    STATE.mkdir(parents=True, exist_ok=True)
    try:
        subprocess.run(["ts", "-S", str(LANES[chosen])], env=env, check=True, capture_output=True, timeout=10)
    except FileNotFoundError:
        raise SystemExit("heavy needs Task Spooler: brew install task-spooler")
    label = re.sub(r"[\[\]\n]", "", f"{Path.cwd().name}: {shlex.join(command)}")[:100]
    waiting = len(lane_jobs(chosen))
    print(f"[heavy] {chosen} lane ({LANES[chosen]} at a time, {waiting} ahead or running): {shlex.join(command)}",
          file=sys.stderr, flush=True)
    os.execvpe("ts", ["ts", "-nf", "-L", label, sys.executable, str(Path(__file__).resolve()), "start", "--",
                      *command], env)


def start(command, poll=0.5):
    """Runs inside the lane slot: wait for a calm Mac, then run the command and supervise it. Task Spooler gives the job
    its own process group, so a Ctrl-C or timeout that stops `heavy` never reaches it; once the `ts` client that queued
    it is gone, this stops the job's group so the freed slot is really free."""
    client = os.getppid()

    def orphaned():
        return os.getppid() != client

    def sleep(seconds):
        if orphaned():
            raise SystemExit(130)
        time.sleep(seconds)

    wait_for_calm(sleep=sleep)
    try:
        job = subprocess.Popen(command)
    except FileNotFoundError:
        raise SystemExit(f"[heavy] command not found: {command[0]}")
    for sig in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
        signal.signal(sig, lambda number, _frame: job.send_signal(number))
    while job.poll() is None:
        if orphaned():
            stop_group(job)
            break
        try:
            job.wait(poll)
        except subprocess.TimeoutExpired:
            pass
    code = job.wait()
    raise SystemExit(128 - code if code < 0 else code)


def stop_group(job, grace=5):
    """SIGTERM the job's process group (this supervisor ignores it), then SIGKILL whatever outlives the grace period."""
    signal.signal(signal.SIGTERM, signal.SIG_IGN)
    os.killpg(os.getpgrp(), signal.SIGTERM)
    try:
        job.wait(grace)
    except subprocess.TimeoutExpired:
        pass
    for row in subprocess.run(["pgrep", "-g", str(os.getpgrp())], capture_output=True, text=True).stdout.split():
        if int(row) != os.getpid():
            try:
                os.kill(int(row), signal.SIGKILL)
            except ProcessLookupError:
                pass


def status():
    load, cpus, free = host_load()
    print(f"load {load:.1f} on {cpus} cores (jobs wait above {LOAD_LIMIT_PER_CPU * cpus:.0f}), {free} MiB free "
          f"(jobs wait below {memory_floor_mib()})")
    for name, slots in LANES.items():
        rows = lane_jobs(name)
        print(f"{name} lane, {slots} at a time: {'idle' if not rows else ''}")
        for state, label in rows:
            print(f"  {state:8} {label}")


def booted_simulators():
    try:
        listing = json.loads(subprocess.run(["xcrun", "simctl", "list", "-j", "devices", "booted"], capture_output=True,
                                            text=True, timeout=60).stdout)
    except (OSError, ValueError, subprocess.SubprocessError):
        return []
    return [(device["udid"], device["name"]) for devices in listing.get("devices", {}).values() for device in devices
            if device.get("state") == "Booted"]


def simulator_in_front():
    try:
        front = subprocess.run(["lsappinfo", "front"], capture_output=True, text=True, timeout=5).stdout.strip()
        info = subprocess.run(["lsappinfo", "info", "-only", "bundleid", front], capture_output=True, text=True,
                              timeout=5).stdout
    except (OSError, subprocess.SubprocessError):
        return False
    return f'"{SIMULATOR_APP}"' in info


def simulator_users():
    rows = subprocess.run(["ps", "-Ao", "pid=,args="], capture_output=True, text=True, timeout=10).stdout.splitlines()
    return [row.strip() for row in rows if SIM_USERS.search(row) and row.split(None, 1)[0] != str(os.getpid())]


def simulator_in_use():
    return bool(lane_jobs("browser")) or bool(simulator_users()) or simulator_in_front()


def idle_action(booted, in_use, last_busy, now):
    """What one idle check does: `clear` the clock when nothing is booted, `mark` the simulator busy now (also the
    first time a booted one is seen), `wait`, or `shutdown` once it has been idle for 30 minutes."""
    if not booted:
        return "clear"
    if in_use or last_busy is None:
        return "mark"
    return "shutdown" if now - last_busy >= SIM_IDLE_SECONDS else "wait"


def idle_sim(now=time.time):
    marker = STATE / "sim-last-busy"
    booted = booted_simulators()
    try:
        last_busy = float(marker.read_text())
    except (OSError, ValueError):
        last_busy = None
    action = idle_action(bool(booted), bool(booted) and simulator_in_use(), last_busy, now())
    if action == "clear" and marker.exists():
        marker.unlink()
    elif action == "mark":
        STATE.mkdir(parents=True, exist_ok=True)
        marker.write_text(str(now()))
    elif action == "shutdown":
        for udid, _ in booted:
            subprocess.run(["xcrun", "simctl", "shutdown", udid], capture_output=True, timeout=120)
        marker.unlink()
        idle = round((now() - last_busy) / 60)
        print(f"{datetime.now().isoformat(timespec='seconds')} shut down {', '.join(n for _, n in booted)} "
              f"after {idle} idle minutes", flush=True)


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if argv[:1] == ["start"] and argv[1:2] == ["--"]:
        return start(argv[2:])
    parser = argparse.ArgumentParser(prog="heavy", description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("--browser", action="store_true", help="run in the one-at-a-time lane")
    parser.add_argument("action", nargs="?", choices=("status", "idle-sim"))
    if "--" in argv:
        split = argv.index("--")
        args = parser.parse_args(argv[:split])
        if args.action or not argv[split + 1:]:
            parser.error("usage: heavy [--browser] -- COMMAND...")
        return run(argv[split + 1:], browser=args.browser)
    args = parser.parse_args(argv)
    if args.action == "status":
        return status()
    if args.action == "idle-sim":
        return idle_sim()
    parser.error("usage: heavy [--browser] -- COMMAND...   |   heavy status   |   heavy idle-sim")


if __name__ == "__main__":
    main()
