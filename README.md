# Shared agent skills

Private source of truth for Surge's 18 enabled personal skills and coding defaults on the
MacBook Pro and Mac mini. Codex and Claude use links to the same checkout.

## Current setup

Both devices use `~/.agents/skill-config` as their checkout. The table below
describes the current manifest after installation; new skills reach another
device only after publication and a successful sync:

| Device | Codex | Claude Code |
| --- | --- | --- |
| MacBook Pro | 18 enabled personal skills | The same 18 personal skills |
| Mac mini | 18 enabled personal skills | The same 18 personal skills |

Codex, Claude Code, and an existing Claude Alt home share `surge-defaults.md`.
Credentials and provider login/configuration are never synced. An Alt home is
included only when it already exists on that Mac.

Changes reach another device after publication and a successful sync. Enable the
existing five-minute sync on each Mac with:

```sh
python3 ~/.agents/skill-config/scripts/skills.py enable-auto-sync
```

It pulls with `--ff-only` and installs from the pulled revision. Dirty checkouts
stop without overwriting work. The checker reports the last install/sync state;
failures remain in `~/.agents/skill-sync-status.json` and
`~/Library/Logs/agent-skills/sync-error.log`. A new provider session is needed to
reload a changed discovery list. In-flight sessions may still hold earlier skill
text, so installed hashes do not prove which text a running agent already read.

### Enabled and synced

- `architect` — design ownership and module boundaries
- `arena` — compare independent candidates
- `benchmark-checklist` — qualify performance and reliability measurements
- `breakdown` — concise change summaries
- `create-verification` — verify supported Defuse changes
- `grill-to-goal` — clarify goals and decisions
- `improve-codebase-architecture` — find architectural improvements
- `how` — explain subsystem flow and ownership from evidence
- `interrogate` — adversarial review
- `karpathy-guidelines` — simple, focused coding
- `reflect` — examine and improve skills and tooling
- `remote-session` — move worktree state and context to remote T3
- `retro` — learn from completed work
- `review-guide` — Capy-style guided review page for a change
- `ship` — commit, push and follow PR work
- `surge-mode` — apply Surge's working style
- `swarm` — parallel independent work
- `thermo-nuclear-code-quality-review` — intensive code quality review

### Previously disabled, now excluded

These 14 skills were disabled in Codex. They have been removed from the current
repository and are no longer synced to either provider:

- `develop-web-game`
- `frontend-code-review`
- `grill-to-issue`
- `investigate`
- `one-pager`
- `presentation`
- `react-doctor`
- `refactor-pass`
- `show-me`
- `takeover-pr`
- `test-defuse`
- `triple-review`
- `write-essay`
- `worktree-dev` — Git/T3 setup now follows the task and managed server owner

## Sync an existing device

Run this on **each Mac** whenever you want its latest configuration:

```sh
python3 ~/.agents/skill-config/scripts/skills.py sync
python3 ~/.agents/check-skills.py
```

The first command pulls GitHub's latest commit with `--ff-only`, then installs
the shared links and Codex discovery settings. The second checks the installation;
its output should show `"status": "PASS"` with an empty `errors` list.

Start a **new Codex or Claude Code session** after syncing so it reloads its
skill list. The automatic job uses the same safe sync command; manual sync remains available.

To sync the Mac mini from the MacBook Pro, with Tailscale connected and SSH access:

```sh
ssh surge@100.108.123.39 \
  'export PATH=/opt/homebrew/bin:/usr/local/bin:$PATH; python3 ~/.agents/skill-config/scripts/skills.py sync && python3 ~/.agents/check-skills.py'
```

Run the local sync command on the MacBook Pro as well to update both devices.

## Install on a new Mac

Requires Git, Python 3.9 or newer, and GitHub access to this private repository.

```sh
gh auth status
mkdir -p ~/.agents
gh repo clone silent-shipper/agent-skills ~/.agents/skill-config
python3 ~/.agents/skill-config/scripts/skills.py install
python3 ~/.agents/check-skills.py
```

If GitHub authentication is missing, run `gh auth login` using an account with
access to `silent-shipper/agent-skills`, then retry. For a device that already has
the checkout, use the sync command above instead of cloning again.

The installer creates links in `~/.agents/skills`, `~/.codex/skills` and
`~/.claude/skills`. Coding defaults appear at `~/.codex/AGENTS.md` and
`~/.claude/CLAUDE.md`. Existing files are moved into a dated directory under
`~/.agents/skill-backups` before replacement. Running installation twice leaves
the same files and links in place.

`manifest.json` lists only the enabled skills to sync, with `codex_enabled: true`
for each entry. Both providers receive the same set. Installation changes only
the managed personal skill entries in Codex's config and preserves other settings.
When a skill is removed from the manifest and repository, the installer backs up
and removes its old repo-managed links and its Codex discovery entry. Unrelated
local skills are preserved.
Credentials, MCP configuration, provider plugin caches and app-managed `synced`
skills are outside this repository.

## Publish changes from either Mac

Sync before you start editing. Change skills under
`~/.agents/skill-config/skills/<skill-name>/`, edit `surge-defaults.md` for shared
coding defaults, or edit `manifest.json` for the managed skill list. Provider
skill paths are links to these same files. To stop syncing a skill, remove its
manifest entry and its `skills/<skill-name>/` directory, then publish the change.

Apply and check your edits, review the diff, then commit and push:

```sh
cd ~/.agents/skill-config
python3 scripts/skills.py install
python3 scripts/skills.py check
git diff
git add -- <changed-paths>
git commit -m "Update personal skills"
git push
```

Then run the sync command on **every device**, including the Mac where you made
the changes:

```sh
python3 ~/.agents/skill-config/scripts/skills.py sync
```

Check that each device has the same commit with:

```sh
git -C ~/.agents/skill-config rev-parse HEAD
```

## If sync stops

- **Local edits exist:** inspect `git -C ~/.agents/skill-config status` and
  `git -C ~/.agents/skill-config diff`. Commit and push the edits you want to keep
  before syncing, or stash them and restore them after syncing.
- **History has diverged:** reconcile the local and GitHub commits in the checkout,
  resolve any conflicts, and push the result before retrying. Sync never resets
  or automatically overwrites your work.
- **GitHub authentication fails:** run `gh auth status`, then `gh auth login` if
  needed. Each Mac needs its own access to this private repository.
- **A skill is missing in an existing session:** start a new provider session,
  then rerun the checker. Only the enabled skills listed above are synced.

## Verify

```sh
python3 ~/.agents/check-skills.py
cd ~/.agents/skill-config
python3 -m unittest discover -s tests
```

The checker verifies names/descriptions, local body references outside examples,
managed links and Codex discovery. It reports Git HEAD, dirty files, manifest, complete source and
skill SHA-256 hashes, host-local toolkit resolution, and the last sync receipt.
Compare the content hashes as well as HEAD across Macs. Existing Claude Alt homes
are included; the number of managed links therefore depends on installed homes. Tests cover repeat installation, backups,
cleanup of removed skills, preservation of unrelated configuration and refusal
to pull over local edits.

## Host-local verification toolkit

Shared skills contain no personal toolkit path. Resolve the existing installation:

```sh
python3 ~/.agents/skill-config/scripts/skills.py toolkit-root
```

It validates the `queue` and `verify:app` package scripts and prompt guide. It
checks the two existing Mac locations; an explicit `METAMASK_E2E_ROOT` selects a
nonstandard checkout or resolves ambiguity. Nothing is cloned or copied. This
proves local installation only; toolkit doctor and the live runner establish
external login/account readiness.

`how` and `benchmark-checklist` are focused adaptations of Lauren Tan's pstack at
commit `1dcc2bacde73ddd284803b7af28164d0436198fc`. Each includes the original MIT
license. Routing and structural correction ideas also inform `surge-mode` and
`retro`; the full pstack orchestration is not installed.
