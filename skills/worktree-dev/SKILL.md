---
name: worktree-dev
description: Use when the user wants to create a worktree and start working, or says "worktree", "new worktree", "create a worktree", "isolated branch", or wants to work on something without touching main. Faster and simpler than the superpowers worktree skill.
---

# Worktree Dev

Create a git worktree from latest main, set it up, and start a dev server. No questions, no ceremony.

## When to Use

- User says "create a worktree", "new worktree", "worktree for X"
- User wants to work on a feature/fix in isolation
- Before any non-trivial code changes

## Workflow

### Step 1 — Create Worktree

Derive a branch name from context. If the user said "worktree for fixing splash screen", use `fix/splash-screen`. If unclear, ask ONE question for the branch name.

```bash
# Fetch latest main
git fetch origin main

# Create worktree with new branch from origin/main
git worktree add .claude/worktrees/<branch-name> -b <branch-name> origin/main
```

**Always branch from `origin/main`** — this prevents the stale-code bugs that happened repeatedly when branching from local HEAD.

### Step 2 — Setup

Run sequentially:

```bash
cd .claude/worktrees/<branch-name>

# Copy env file from main repo
cp /Users/surge/Desktop/Projects/defuse-near/.env.local .env.local 2>/dev/null || true

# Install dependencies
bun install
```

### Step 3 — Start Dev Server

```bash
cd .claude/worktrees/<branch-name> && bun run dev
```

Run this in the background. If port 3000 is taken, Next.js will auto-select the next available port. Read the output to find the actual URL.

### Step 4 — Report

Print exactly:
```
Worktree ready:
  Branch: <branch-name>
  Path: .claude/worktrees/<branch-name>
  Dev server: http://localhost:<port>
```

That's it. Start working.

## Rules

- **No questions** beyond branch name (if not obvious from context)
- **Always fetch + branch from origin/main** — never from local HEAD or current branch
- **Always copy .env.local** — the dev server won't work without it
- **Always bun install** — worktrees don't share node_modules
- **Start dev server in background** — user will want to test
- **If anything fails, fix it** — don't ask the user to debug worktree setup. Common issues:
  - Port in use → let Next.js auto-select
  - Missing .env.local → copy from main repo
  - bun install fails → show error, likely a network issue
  - Worktree already exists → tell user, offer to reuse or delete and recreate

## Cleanup

When the user is done (merged PR, abandoned work, etc.):

```bash
git worktree remove .claude/worktrees/<branch-name>
git branch -d <branch-name>  # only if merged
```

Don't clean up automatically — always ask first.
