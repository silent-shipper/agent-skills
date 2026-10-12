# Shared agent skills

Private source of truth for Surge's 28 personal skills and coding defaults on the
MacBook Pro and Mac mini. Codex and Claude use links to the same checkout.

## Install

Requires Git, Python 3.9 or newer, and GitHub access to this private repository.

```sh
gh repo clone silent-shipper/agent-skills ~/.agents/skill-config
python3 ~/.agents/skill-config/scripts/skills.py install
python3 ~/.agents/check-skills.py
```

The installer creates links in `~/.agents/skills`, `~/.codex/skills` and
`~/.claude/skills`. Coding defaults appear at `~/.codex/AGENTS.md` and
`~/.claude/CLAUDE.md`. Existing files are moved into a dated directory under
`~/.agents/skill-backups` before replacement. Running installation twice leaves
the same files and links in place.

`manifest.json` records each personal skill's Codex enabled/disabled choice from
the MacBook Pro. Claude receives all personal skills. Installation changes only
the managed personal skill entries in Codex's config and preserves other settings.
Credentials, MCP configuration, provider plugin caches and app-managed `synced`
skills are outside this repository.

## Update both Macs

Edit the checkout on either Mac, verify, commit and push:

```sh
cd ~/.agents/skill-config
python3 scripts/skills.py check
git add .
git commit -m "Update personal skills"
git push
```

Pull and apply on the other Mac:

```sh
python3 ~/.agents/skill-config/scripts/skills.py sync
```

Sync refuses local edits and diverged history. Resolve and push those edits before
retrying; it never automatically commits or overwrites them. Start a new Codex or
Claude session after updates so the provider reloads its skill list.

Optional automatic pulls use a per-user macOS LaunchAgent every five minutes:

```sh
python3 ~/.agents/skill-config/scripts/skills.py enable-auto-sync
```

Logs are in `~/Library/Logs/agent-skills`. To stop automatic pulls:

```sh
launchctl bootout gui/$(id -u)/com.silent-shipper.agent-skills
rm ~/Library/LaunchAgents/com.silent-shipper.agent-skills.plist
```

## Verify

```sh
python3 ~/.agents/check-skills.py
python3 -m unittest discover -s tests
```

The checker verifies skill names/descriptions, all 88 managed links and every
managed Codex discovery setting. Tests cover repeat installation, backups,
preservation of unrelated configuration and refusal to pull over local edits.
