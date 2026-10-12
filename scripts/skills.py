#!/usr/bin/env python3
"""Install, verify, or pull Surge's shared personal skills."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import plistlib
import re
import subprocess
import sys
from datetime import datetime

REPO = Path(__file__).resolve().parent.parent
HOME_DIR = Path.home().resolve()
LABEL = "com.silent-shipper.agent-skills"
ROOTS = (".agents/skills", ".codex/skills", ".claude/skills")


def run(*args):
    return subprocess.check_output(args, text=True, timeout=90).strip()


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
    for root in ROOTS:
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
        for root in ROOTS:
            paths[HOME_DIR / root / name] = REPO / "skills" / name
    for path in (".agents/surge-defaults.md", ".codex/AGENTS.md", ".claude/CLAUDE.md"):
        paths[HOME_DIR / path] = REPO / "surge-defaults.md"
    paths[HOME_DIR / ".agents/check-skills.py"] = REPO / "scripts/check-skills.py"
    return paths


def configured(text):
    for match in re.finditer(r"(?m)^\[\[skills\.config\]\]\s*\n.*?(?=^\[|\Z)", text, re.S):
        block = match[0]
        path = re.search(r'^path\s*=\s*"([^"]+)"\s*$', block, re.M)
        enabled = re.search(r"^enabled\s*=\s*(true|false)\s*$", block, re.M)
        yield match, Path(path[1]) if path else None, enabled[1] == "true" if enabled else None


def skill_config(text, skills, retired=()):
    names = {s["name"] for s in skills} | {path.name for path in retired}
    known = {str(HOME_DIR / root / name / "SKILL.md") for root in ROOTS for name in names}
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
    check()
    if directory.exists():
        print("Backups:", directory)


def check():
    skills = manifest()
    errors = ["Retired skill still linked: " + str(path) for path in retired_links(skills)]
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
    print(json.dumps({"status": "FAIL" if errors else "PASS", "skills_checked": len(skills),
                      "links_checked": len(managed_paths(skills)), "errors": errors}, indent=2))
    if errors:
        raise SystemExit(1)


def sync():
    if run("git", "-C", str(REPO), "status", "--porcelain"):
        raise SystemExit("Local edits exist; commit and push them before syncing.")
    run("git", "-C", str(REPO), "pull", "--ff-only")
    install()


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
    domain = "gui/" + str(os.getuid())
    if subprocess.run(["launchctl", "print", domain + "/" + LABEL], stdout=subprocess.DEVNULL,
                      stderr=subprocess.DEVNULL).returncode:
        run("launchctl", "bootstrap", domain, str(path))
    print("Automatic sync enabled every 5 minutes:", path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("install", "check", "sync", "enable-auto-sync"))
    args = parser.parse_args()
    (HOME_DIR / ".agents").mkdir(parents=True, exist_ok=True)
    with (HOME_DIR / ".agents/.skill-config.lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise SystemExit("Another skill-config operation is running.")
        {"install": install, "check": check, "sync": sync, "enable-auto-sync": auto_sync}[args.command]()


if __name__ == "__main__":
    main()
