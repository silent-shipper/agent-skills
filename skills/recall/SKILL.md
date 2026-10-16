---
name: recall
description: "Reconstruct working context or steering patterns from the user's past Claude Code/Codex transcripts, live git/gh state and the shared record, then return a tight cited brief. Use for 'recall my work on X', 'catch me up', 'where did I leave off', or 'learn how I steer agents'."
---

# Recall

Adapted from pstack `recall` (MIT, Lauren Tan).

Rebuild the user's recent context and hand back a capsule of where things stand
and what to do next. Read only what in-scope threads need, then stop.

## Where transcripts live

- Claude Code: `~/.claude/projects/<slug>/*.jsonl`. The slug is the cwd with `/`
  and `.` replaced by `-`. One repo spans many slugs: the main checkout,
  `-.t3-worktrees-<repo>-*` task worktrees and `-.t3-scratch-*` folders.
- Codex: `~/.codex/sessions/**.jsonl`.
- Extract user text with `jq`; skip tool results, sidechain/subagent messages and
  the current session.

## Steps

1. Lock scope: window (default 7 days), topic, and repos. State it back. Never
   quietly shrink "all" to "recent N". Don't read unrelated projects unasked.
2. Order candidates by real mtime, grep the topic first, then read only matching
   regions. For more than a few files, fan out cheap subagents per slice; each
   returns per chat: goal, decisions, corrections, open threads, artifacts
   (PR/branch), citing the file uuid.
3. When a feature, file or bug is named, also sweep PRs, review comments, reverts
   and follow-up fixes with `git`/`gh`: what was tried and didn't hold.
4. Verify surfaced PRs and branches against live `git`/`gh` state.

For steering analysis ("how do I steer agents"), classify user corrections,
count them, quote 2–4 examples per class, and mark which are already captured in
`surge-defaults.md` or `surge-mode`.

## Output

- **Capsule.** At most 5 bullets.
- **Threads.** One line each with one tag: `[merged #N]`, `[open PR #N]`,
  `[in flight <branch>]`, `[verified, uncommitted]`, `[reverted #N]`,
  `[planned, not started]`.
- **Problems.** At most 5 recurring ones, including reverted fixes.
- **Next move.** The single most useful concrete action.
