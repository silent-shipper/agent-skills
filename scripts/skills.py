#!/usr/bin/env python3
"""Install, verify, or pull Surge's shared personal skills."""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import plistlib
import re
import subprocess
import sys
from datetime import datetime
from urllib.parse import unquote, urlsplit

REPO = Path(__file__).resolve().parent.parent
HOME_DIR = Path.home().resolve()
LABEL = "com.silent-shipper.agent-skills"
ROOTS = (".agents/skills", ".codex/skills", ".claude/skills")


def roots():
    return ROOTS + ((".claude-alt/skills",) if (HOME_DIR / ".claude-alt").is_dir() else ())


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def reference_errors(skills):
    errors = []
    for skill in skills:
        for path in (REPO / "skills" / skill["name"]).rglob("*.md"):
            text = re.sub(r"(?ms)^\s*(`{3,}|~{3,}).*?^\s*\1\s*$", "", path.read_text())
            for target in re.findall(r"\]\(([^)]+)\)", text):
                target = target.strip().split(" ", 1)[0].strip("<>")
                parsed = urlsplit(target)
                if parsed.scheme or not parsed.path or parsed.path.startswith("/") or "$" in target:
                    continue
                if not (path.parent / unquote(parsed.path)).exists():
                    errors.append("Missing reference: " + str(path.relative_to(REPO)) + " -> " + target)
    return errors


def toolkit_root():
    configured = os.environ.get("METAMASK_E2E_ROOT")
    candidates = [Path(configured).expanduser()] if configured else [
        HOME_DIR / "Desktop/Projects/metamask-e2e", HOME_DIR / "Projects/metamask-e2e"]
    valid = []
    for path in candidates:
        try:
            package = json.loads((path / "package.json").read_text())
            scripts = package.get("scripts") if isinstance(package, dict) else None
            if isinstance(scripts, dict) and all(name in scripts for name in ("queue", "verify:app")) and (path / "docs/prompt-verification.md").is_file():
                valid.append(path.resolve())
        except (OSError, ValueError):
            continue
    valid = sorted(set(valid))
    if len(valid) != 1:
        raise ValueError("Set METAMASK_E2E_ROOT to the intended toolkit checkout with queue/verify:app scripts and docs/prompt-verification.md; found " + str(len(valid)) + " valid roots.")
    return valid[0]


def identity():
    try:
        head = run("git", "-C", str(REPO), "rev-parse", "HEAD", quiet=True)
        dirty = run("git", "-C", str(REPO), "status", "--porcelain", quiet=True).splitlines()
    except subprocess.CalledProcessError:
        head, dirty = None, []
    source = hashlib.sha256()
    for path in sorted(REPO.rglob("*")):
        relative = path.relative_to(REPO)
        if not path.is_file() or relative.parts[0] not in ("skills", "scripts", "manifest.json", "surge-defaults.md") or "__pycache__" in relative.parts or path.suffix == ".pyc":
            continue
        source.update(str(relative).encode() + b"\0" + hashlib.sha256(path.read_bytes()).digest())
    return {"repo_head": head, "dirty_files": dirty, "source_sha256": source.hexdigest(), "manifest_sha256": digest(REPO / "manifest.json") if (REPO / "manifest.json").is_file() else None,
            "skill_sha256": {s["name"]: digest(REPO / "skills" / s["name"] / "SKILL.md") for s in (manifest() if (REPO / "manifest.json").is_file() else [])}}


def record_status(status, reason=None):
    path = HOME_DIR / ".agents/skill-sync-status.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {"status": status, "at": datetime.now().astimezone().isoformat(), **identity()}
    if reason:
        data["reason"] = reason
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(data, indent=2) + "\n")
    temporary.replace(path)


def run(*args, quiet=False):
    return subprocess.check_output(args, text=True, timeout=90,
                                   stderr=subprocess.DEVNULL if quiet else None).strip()


def manifest():
    data = json.loads((REPO / "manifest.json").read_text())
    assert data["version"] == 1, "Unsupported manifest version"
    names = set()
    for skill in data["skills"]:
        name = skill["name"]
        assert re.fullmatch(r"[a-z0-9-]+", name) and name not in names, name
        assert skill["codex_enabled"] is True, "Disabled skills must be removed from the synced manifest: " + name
        content = (REPO / "skills" / name / "SKILL.md").read_text()
        front = re.match(r"^---\n(.*?)\n---\n", content, re.S)
        field = re.search(r"^name:\s*(.*?)\s*$", front[1], re.M) if front else None
        assert field and field[1].strip("\"'") == name, name
        assert re.search(r"^description:\s*\S", front[1], re.M), name
        names.add(name)
    return data["skills"]


def retired_links(skills):
    names = {skill["name"] for skill in skills}
    paths = []
    for root in roots():
        directory = HOME_DIR / root
        for path in directory.iterdir() if directory.exists() else ():
            if path.is_symlink() and path.name not in names:
                target = path.resolve()
                if target.parent == REPO / "skills" and target.name == path.name:
                    paths.append(path)
    return paths


def managed_paths(skills):
    paths = {}
    for skill in skills:
        name = skill["name"]
        for root in roots():
            paths[HOME_DIR / root / name] = REPO / "skills" / name
    for path in (".agents/surge-defaults.md", ".codex/AGENTS.md", ".claude/CLAUDE.md"):
        paths[HOME_DIR / path] = REPO / "surge-defaults.md"
    paths[HOME_DIR / ".agents/check-skills.py"] = REPO / "scripts/check-skills.py"
    if (HOME_DIR / ".claude-alt").is_dir():
        paths[HOME_DIR / ".claude-alt/CLAUDE.md"] = REPO / "surge-defaults.md"
    return paths


def configured(text):
    for match in re.finditer(r"(?m)^\[\[skills\.config\]\]\s*\n.*?(?=^\[|\Z)", text, re.S):
        block = match[0]
        path = re.search(r'^path\s*=\s*"([^"]+)"\s*$', block, re.M)
        enabled = re.search(r"^enabled\s*=\s*(true|false)\s*$", block, re.M)
        yield match, Path(path[1]) if path else None, enabled[1] == "true" if enabled else None


def skill_config(text, skills, retired=()):
    names = {s["name"] for s in skills} | {path.name for path in retired}
    known = {str(HOME_DIR / root / name / "SKILL.md") for root in roots() for name in names}
    known.update(str(REPO / "skills" / name / "SKILL.md") for name in names)
    for match, path, _ in reversed(list(configured(text))):
        if str(path) in known:
            text = text[:match.start()] + text[match.end():]
    additions = "\n".join(
        '[[skills.config]]\npath = ' + json.dumps(str(HOME_DIR / ".codex/skills" / s["name"] / "SKILL.md"))
        + '\nenabled = ' + str(s["codex_enabled"]).lower() + '\n' for s in skills
    )
    return text.rstrip() + "\n\n" + additions


def backup(path, directory):
    if path.exists() or path.is_symlink():
        target = directory / path.relative_to(HOME_DIR)
        target.parent.mkdir(parents=True, exist_ok=True)
        path.rename(target)


def install():
    skills = manifest()
    directory = HOME_DIR / ".agents/skill-backups" / datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    config = HOME_DIR / ".codex/config.toml"
    old = config.read_text() if config.exists() else ""
    retired = retired_links(skills)
    new = skill_config(old, skills, retired)
    for path in retired:
        backup(path, directory)
    for path, target in managed_paths(skills).items():
        if path.is_symlink() and path.resolve() == target:
            continue
        backup(path, directory)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.symlink_to(os.path.relpath(target, path.parent.resolve()))
    if old != new:
        backup(config, directory)
        config.parent.mkdir(parents=True, exist_ok=True)
        temporary = config.with_name("config.toml.skill-config-tmp")
        temporary.write_text(new)
        temporary.chmod(0o600)
        temporary.replace(config)
    try:
        check()
    except SystemExit:
        record_status("blocked", "Installed skill checks failed; run check for the exact errors.")
        raise
    record_status("installed")
    if directory.exists():
        print("Backups:", directory)


def check():
    skills = manifest()
    errors = reference_errors(skills) + ["Retired skill still linked: " + str(path) for path in retired_links(skills)]
    for path, target in managed_paths(skills).items():
        if not path.is_symlink() or path.resolve() != target or not target.exists():
            errors.append("Invalid link: " + str(path))
    config = HOME_DIR / ".codex/config.toml"
    entries = list(configured(config.read_text() if config.exists() else ""))
    for skill in skills:
        source = REPO / "skills" / skill["name"] / "SKILL.md"
        values = [enabled for _, path, enabled in entries if path and path.resolve() == source]
        if values != [skill["codex_enabled"]]:
            errors.append("Incorrect Codex discovery setting: " + skill["name"])
    try:
        toolkit = {"status": "ready", "root": str(toolkit_root())}
    except ValueError as error:
        toolkit = {"status": "unconfigured", "remedy": str(error)}
    status_path = HOME_DIR / ".agents/skill-sync-status.json"
    try:
        last_sync = json.loads(status_path.read_text())
    except (OSError, ValueError):
        last_sync = None
    print(json.dumps({"status": "FAIL" if errors else "PASS", "skills_checked": len(skills),
                      "links_checked": len(managed_paths(skills)), "errors": errors, **identity(),
                      "toolkits": {"metamask-e2e": toolkit}, "last_sync": last_sync,
                      "auto_sync_installed": (HOME_DIR / "Library/LaunchAgents" / (LABEL + ".plist")).is_file()}, indent=2))
    if errors:
        raise SystemExit(1)


def sync():
    if run("git", "-C", str(REPO), "status", "--porcelain"):
        record_status("blocked", "Local edits exist; commit and push them before syncing.")
        raise SystemExit("Local edits exist; commit and push them before syncing.")
    try:
        run("git", "-C", str(REPO), "pull", "--ff-only")
    except subprocess.CalledProcessError as error:
        record_status("blocked", "Git pull --ff-only failed; inspect authentication or divergent history.")
        raise SystemExit("Git pull --ff-only failed; local work was not reset.") from error
    os.execv(sys.executable, [sys.executable, str(REPO / "scripts/skills.py"), "install"])


def auto_sync():
    directory = HOME_DIR / "Library/Logs/agent-skills"
    directory.mkdir(parents=True, exist_ok=True)
    path = HOME_DIR / "Library/LaunchAgents" / (LABEL + ".plist")
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {"Label": LABEL, "ProgramArguments": ["/usr/bin/python3", str(REPO / "scripts/skills.py"), "sync"],
            "EnvironmentVariables": {"PATH": "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"},
            "StartInterval": 300, "RunAtLoad": True,
            "StandardOutPath": str(directory / "sync.log"), "StandardErrorPath": str(directory / "sync-error.log")}
    if path.exists() and plistlib.loads(path.read_bytes()) != data:
        raise SystemExit("A different launch agent already exists: " + str(path))
    path.write_bytes(plistlib.dumps(data))
    gui = "gui/" + str(os.getuid())
    domain = gui if subprocess.run(["launchctl", "print", gui], stdout=subprocess.DEVNULL,
                                 stderr=subprocess.DEVNULL).returncode == 0 else "user/" + str(os.getuid())
    if subprocess.run(["launchctl", "print", domain + "/" + LABEL], stdout=subprocess.DEVNULL,
                      stderr=subprocess.DEVNULL).returncode:
        run("launchctl", "bootstrap", domain, str(path))
    print("Automatic sync enabled every 5 minutes:", path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("install", "check", "sync", "enable-auto-sync", "toolkit-root"))
    args = parser.parse_args()
    if args.command == "toolkit-root":
        try:
            print(toolkit_root())
        except ValueError as error:
            raise SystemExit(str(error)) from error
        return
    (HOME_DIR / ".agents").mkdir(parents=True, exist_ok=True)
    with (HOME_DIR / ".agents/.skill-config.lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise SystemExit("Another skill-config operation is running.")
        {"install": install, "check": check, "sync": sync, "enable-auto-sync": auto_sync}[args.command]()


if __name__ == "__main__":
    main()
