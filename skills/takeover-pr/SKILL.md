---
name: takeover-pr
description: Use when the user wants to take over an open pull request — investigate, fix issues, resolve merge conflicts, run tests, and push back to the PR branch. Triggers on "takeover PR", "review and fix PR", "investigate and ship PR #N", or similar.
---

# Takeover PR

Drive an open PR to shipworthy state: investigate the diff, fix issues, merge the base branch, verify, and push.

## Workflow

### Step 1 — Fetch PR Info

```bash
gh pr view <number> --repo <owner>/<repo> \
  --json title,headRefName,baseRefName,body,state,url
```

Note: `headRefName` = the branch to check out. `baseRefName` = what to merge in.

### Step 2 — Create Worktree for the PR Branch

```bash
git fetch origin <headRefName>
git worktree add .claude/worktrees/pr-<number> origin/<headRefName>
cd .claude/worktrees/pr-<number>
git checkout -b <headRefName>
cp /path/to/main/repo/.env.local .env.local 2>/dev/null || true
bun install
```

### Step 3 — Get the Diff

```bash
git diff origin/<baseRefName>...HEAD --name-only   # files changed
git diff origin/<baseRefName>...HEAD               # full diff
git log --oneline origin/<baseRefName>..HEAD       # commits
```

### Step 4 — Investigate with Parallel Subagents

Use `/investigate` (the investigate skill). Dispatch one subagent per concern area.

Each subagent prompt must include:
- The specific area (state machine, hook, component, util)
- The symptom or goal ("does this pattern violate CLAUDE.md?")
- Which files to start from
- What to return: `file:line` references + verdict

Typical investigation areas for a PR:
- **Anti-patterns**: `useEffect` for state sync, missing type guards, hardcoded deps
- **Logic correctness**: Does the fix actually solve the root cause?
- **Test quality**: Are tests testing the real behavior, or trivial assertions?
- **Merge readiness**: Does the base branch have conflicting changes that need resolution?

### Step 5 — Fix Issues Found

Fix in order: correctness → anti-patterns → tests.

Rules from CLAUDE.md that come up most often:
- No `useEffect` for state sync → initialize from source directly or use event handlers
- No `console.log` → use `logger`
- Machine owns logic, form owns UI
- Services return `Result` types

Commit each logical fix separately:
```bash
git add <specific-files>
git commit -m "fix: <describe the why>"
```

### Step 6 — High-Value Tests

Before merging, ask: "If this breaks silently in production, would a test have caught it?"

Only add tests that meet ALL of these:
1. Non-obvious behavior that could silently regress
2. Would catch a real bug, not just verify obvious code
3. TypeScript/lint can't catch it alone
4. Tests the boundary, not internal implementation

Skip if nothing qualifies. Commit as `test: description`.

### Step 7 — Merge Base Branch

```bash
git fetch origin <baseRefName>
git merge origin/<baseRefName> --no-edit
```

**When conflicts arise:** For each conflicted file, determine which version is the "superset":
- Take `--theirs` (base branch) if it has your changes PLUS more
- Take `--ours` if your version is strictly more complete
- Manual merge if both have unique valuable changes

After resolving:
```bash
git add <resolved-files>
git commit -m "merge: update with <baseRefName>"
```

### Step 8 — Pre-flight

```bash
bun run check      # lint
bun run typecheck  # types
bun run test       # tests — note any pre-existing failures
```

If tests fail: check if the failure exists on the base branch too. Pre-existing failures from base branch do NOT block the PR.

### Step 9 — Push

```bash
git push origin <headRefName>
```

The PR is already open — pushing updates it automatically.

### Step 10 — Report

Print:
```
PR updated: <url>
Branch: <headRefName>
Commits pushed: N
Issues fixed:
  - <fix 1>
  - <fix 2>
Pre-existing test failures (not from this PR): <list or "none">
```

## Conflict Resolution Cheatsheet

| Situation | Action |
|-----------|--------|
| Base has our changes + more (e.g. analytics on top) | `--theirs` |
| Our version has more (e.g. extra URL params) | `--ours` |
| Both have unique changes | Manual merge, take both |
| Test file conflict | Our version if it's a superset |
| Architecture diverged | Take base arch, apply our logic on top |

## Common Issues Found in PRs

| Pattern | Fix |
|---------|-----|
| `useEffect` syncing state from URL/prop | Initialize `useState`/`useForm` defaultValues directly |
| Only locking UI in create mode, not edit | Change `isConfidentialCreate` guard to `confidentialMode` |
| Missing network guard on confidential routing | Add `&& network === "near_intents"` check |
| `useEffect` deps cause stale closures | Use `actorRef.on()` events instead |

## Rules

- **Worktree always** — never modify the main repo directly for a PR takeover
- **Fix root cause, not symptoms** — ask "WHY" before editing
- **Pre-existing failures are OK** — document them, don't hide them
- **Don't change the PR's base branch** — only push to `headRefName`
- **One commit per concern** — don't bundle unrelated fixes
