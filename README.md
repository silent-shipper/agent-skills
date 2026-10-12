# Shared agent skills

Private source of truth for Surge's 16 enabled personal skills and coding defaults on the
MacBook Pro and Mac mini. Codex and Claude use links to the same checkout.

## Current setup

Both devices use `~/.agents/skill-config` as their checkout:

| Device | Codex | Claude Code |
| --- | --- | --- |
| MacBook Pro | 16 enabled personal skills | The same 16 personal skills |
| Mac mini | 16 enabled personal skills | The same 16 personal skills |

Both providers also share `surge-defaults.md`. Sync is manual: changes reach
another device after you push them to GitHub and run the sync command there.

### Enabled and synced

- `architect` — design ownership and module boundaries
- `arena` — compare independent candidates
- `breakdown` — concise change summaries
- `create-verification` — verify supported Defuse changes
- `grill-to-goal` — clarify goals and decisions
- `improve-codebase-architecture` — find architectural improvements
- `interrogate` — adversarial review
- `karpathy-guidelines` — simple, focused coding
- `reflect` — examine and improve skills and tooling
- `retro` — learn from completed work
- `review-guide` — Capy-style guided review page for a change
- `ship` — commit, push and follow PR work
- `surge-mode` — apply Surge's working style
- `swarm` — parallel independent work
- `thermo-nuclear-code-quality-review` — intensive code quality review
- `worktree-dev` — create an isolated worktree

### Previously disabled, now excluded

These 13 skills were disabled in Codex. They have been removed from the current
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
skill list. There is no automatic pull job installed on either Mac.

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
git add .
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

The checker verifies skill names/descriptions, all 52 managed links and every
managed Codex discovery setting. Tests cover repeat installation, backups,
cleanup of removed skills, preservation of unrelated configuration and refusal
to pull over local edits.
