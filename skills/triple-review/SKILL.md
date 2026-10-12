---
name: triple-review
description: Use when the user wants a high-signal PR or branch review using codex, claude, and gemini CLIs in parallel one-shot read-only mode from an isolated local worktree. Triggers on "triple review", "review with all three", "multi-model review", or any request to combine codex+claude+gemini opinions on a PR/branch with reduced false positives. Output is a single triaged action plan, saved as a durable markdown artifact, with model-verified, consensus-calibrated, falsifiable findings.
---

# Triple Review

Create an isolated local worktree for the PR or branch, fan the same review brief out to three reviewers (codex, claude, gemini) in parallel, then keep only what survives model-level verification plus a consensus-or-strong-evidence filter. Output is one durable report on disk, organized as a tiered action plan, with each finding falsifiable.

## When to use

- User says "triple review", "review this PR with all three", "multi-model review"
- User wants a staff-engineer-level review with minimal noise
- A PR is large enough that one model's review would be too noisy or miss things

## When NOT to use

- Tiny diffs (< ~50 lines) — one model is plenty, this just burns tokens
- The user wants their own Claude session to do the review interactively
- No `gh` access AND no clean `origin/main` to diff against

## Inputs

Accept any of:
- PR number → create a local review worktree from `pull/<num>/head`
- PR URL → extract number, then create a local review worktree from `pull/<num>/head`
- Nothing → create a detached review worktree from current `HEAD` and compare against `origin/main`

If the diff comes back empty, stop and tell the user.

## Workflow

### Step 0 — Pre-flight (skip the wasted-run failure mode)

Run all three checks **in parallel** before anything else. If any fail, stop and surface the exact remediation:

```bash
# codex authed?
node "/Users/surge/.claude/plugins/cache/openai-codex/codex/1.0.2/scripts/codex-companion.mjs" setup --json | grep -q '"loggedIn": true' || echo "codex not authed: run !codex login"

# gh authed?
gh auth status >/dev/null 2>&1 || echo "gh not authed: run !gh auth login"

# gemini available?
which gemini >/dev/null 2>&1 || echo "gemini missing: install gemini-cli"
```

This step exists because subagent-style runs have failed mid-flight when codex was unauthenticated. ~10 seconds up front saves a wasted dispatch.

### Step 1 — Create an isolated review worktree

Prefer reviewing a local worktree over pasting a giant diff into reviewer prompts. The reviewers should have full read-only repo context, while the orchestrating model keeps control of checkout, branch state, synthesis, and final judgment.

For a PR number:

```bash
repo_name="$(basename "$(git rev-parse --show-toplevel)")"
review_root="$(dirname "$(git rev-parse --show-toplevel)")/${repo_name}-pr<num>-review"
git fetch origin "pull/<num>/head:triple-review-pr-<num>"
git worktree add "$review_root" "triple-review-pr-<num>"
```

If the branch already exists or the worktree path already exists, inspect it before choosing a new path. Do not overwrite user files. Use a suffix like `-review-2` if needed.

For current-branch review with no PR, create a detached worktree from `HEAD`:

```bash
repo_name="$(basename "$(git rev-parse --show-toplevel)")"
branch_name="$(git branch --show-current | tr '/ ' '--')"
review_root="$(dirname "$(git rev-parse --show-toplevel)")/${repo_name}-${branch_name}-review"
git worktree add --detach "$review_root" HEAD
```

All reviewer commands should run with `cwd="$review_root"` and read-only permissions. The orchestrating model may inspect the original checkout as needed, but should write the final artifact into the review worktree.

### Step 2 — Get the diff and PR body

```bash
cd "$review_root"
gh pr diff <num> --repo <owner/repo> > /tmp/triple-review-diff.patch
gh pr view <num> --repo <owner/repo> --json body,title,baseRefName,headRefName,url > /tmp/triple-review-pr.json
gh pr view <num> --repo <owner/repo> --json body,title -q '.body' > /tmp/triple-review-pr-body.md
```

If the diff is > ~3000 lines, **warn the user** before proceeding (cost + signal both degrade). If the PR body lists known issues, planned follow-ups, or "deviations from plan with reasoning" — capture them: those are the **author-acknowledged** items reviewers should not re-flag.

### Step 3 — Write the shared prompt

Same prompt for all three CLIs. That's what makes consensus meaningful. Template is in the next section. Replace all placeholders before writing `/tmp/triple-review-prompt.txt`. Do NOT paste the whole diff into the prompt — reviewers should inspect the worktree with read-only commands. Reviewers may use `gh pr view` themselves, but the orchestrating model must still dedup against `/tmp/triple-review-pr-body.md` during synthesis.

### Step 4 — Run all three in parallel

Single message, three Bash tool calls. Sequential costs 3× wall time for zero benefit. The exact flags below have been validated against real failure modes — do not edit them lightly:

```bash
# codex: --skip-git-repo-check is REQUIRED if cwd may not be a git repo.
# -o writes ONLY the final agent message to the review file (clean output).
# codex prints its read-only exec exploration to stdout — discard it; the
# last-message file is what we synthesize from.
codex exec --sandbox read-only --skip-git-repo-check \
  -o /tmp/triple-review-codex.md \
  "$(cat /tmp/triple-review-prompt.txt)" > /tmp/triple-review-codex.trace 2>&1
```

```bash
# claude: do NOT use --bare. It disables OAuth keychain reads and breaks
# auth for users who log in via `claude /login` (most users).
claude -p --permission-mode plan --no-session-persistence "$(cat /tmp/triple-review-prompt.txt)" > /tmp/triple-review-claude.md 2>&1
```

```bash
# Also: -p must be the LAST flag so yargs doesn't consume the next flag.
gemini --approval-mode plan -p "$(cat /tmp/triple-review-prompt.txt)" > /tmp/triple-review-gemini.md 2>&1
```

Each is one-shot and read-only by construction. If one fails, surface the error but proceed with the other two.

Run these commands from the review worktree. Do not give reviewers write permissions. Do not ask reviewers to post comments, approve, push, install packages, checkout branches, or mutate repository state.

### Step 5 — Synthesize and verify

Read all three output files. Cluster semantically identical findings. For each candidate finding that might survive, inspect the cited code in the review worktree and verify the claim yourself before including it. Consensus is evidence, not proof. Apply the synthesis rules below (model verification + consensus + PR-body dedup). Build the tiered action plan.

### Step 6 — Save the artifact

Write the final report to a durable location, **in this order of preference**:
1. If a review worktree path was used (e.g. `~/Desktop/Projects/<repo>-pr<num>-review/`), write to `REVIEW.md` there.
2. Otherwise, write to the cwd as `REVIEW-PR<num>.md`.
3. Always also leave the raw outputs at `/tmp/triple-review-{codex,claude,gemini}.md` for debugging.

Tell the user the artifact path so they can `cat` it, attach it to the PR, or paste into Slack.

### Step 7 — (Optional) Post inline PR comments

If the user asked to "post the findings on the PR" or supplied an `--inline` flag, post each Block-merge finding as a GitHub review comment via `gh api repos/<owner>/<repo>/pulls/<num>/comments` (NOT in-code edits). Otherwise skip.

## Shared prompt template

Write this to `/tmp/triple-review-prompt.txt`, replacing `<PR number>`, `<base>`, `<head>`, `<review_root>`, and `<owner/repo>` with concrete values. For current-branch reviews with no PR, replace PR-specific commands with the current branch name and base commit.

```
You are a staff engineer reviewing a pull request. Your reputation is for an
extremely high signal-to-noise ratio. You would rather miss a small issue than
report a false positive.

Review PR <PR number> in <owner/repo>.
Local worktree: <review_root>
Base: <base>
Head: <head>

Report ONLY findings you are highly confident about
(at least 85% sure). If you are not sure, omit it. Silence is a valid answer.

You may inspect the repository and PR using read-only access only. Use
whichever your environment provides — shell OR native file tools:

Shell (codex, claude):
- gh pr view <PR number> --json body,title,baseRefName,headRefName,url
- gh pr diff <PR number>
- git diff <base>...HEAD
- git show
- rg
- sed
- cat

Native file tools (use these if your environment lacks shell, e.g. gemini
plan mode):
- read_file, list_directory, glob, grep_search

Pre-fetched artifacts are also on disk if shell/`gh` is unavailable:
- /tmp/triple-review-diff.patch (full PR diff)
- /tmp/triple-review-pr-body.md (PR body for known-issue dedup)

Do not edit files, post comments, approve/request changes, push, install
packages, checkout branches, or mutate repository state.

CAP: at most 5 findings PER SECTION. If you have more than 5, drop the
weakest. The cap exists to force prioritization — a list of 12 findings is
indistinguishable from noise.

Output exactly these three markdown sections, in order, using these headers
verbatim. If a section has nothing high-confidence, write
"Nothing high-confidence." under that header — do not pad.

## 1. Bugs & Vulnerabilities
Logic errors, race conditions, null/undefined hazards, broken invariants,
concurrency issues, injection, auth/authz holes, secret leakage, SSRF/XSS, etc.

## 2. Architecture
Design choices that will create real pain at scale or during change.
Misplaced abstractions, leaky boundaries, coupling that matters, wrong layer.

## 3. Cleaner Code
Dead code, unnecessary complexity, premature abstractions, naming/structure a
staff engineer would push back on in review.

Required shape for EVERY finding (drop the finding if you can't supply all 4):
- `path/to/file:LINE` — one-sentence statement of what breaks
- **Repro:** one-sentence trigger ("open in 2 tabs and click X")
- **Impact:** what a real user/operator notices ("stale data for 5 minutes")
- **Verify:** one bash command or grep that confirms it ("`grep attemptedForRef src/.../*.tsx`")
- **Severity:** high / med / low

Hard rules:
- Cite `file:LINE` for every finding. No anchor, no finding.
- No nitpicks. No "consider..." style musings. No taste-only comments.
- Only comment on lines in the PR diff (or directly affected by the diff).
- One short paragraph max per finding. Be terse.

Output format rules (strict — your output is parsed):
- Your response must START with the literal line `## 1. Bugs & Vulnerabilities`.
- Output ONLY the three sections in order. Nothing before, nothing after.
- No preamble ("Here's my review..."), no closing notes ("Let me know if..."),
  no Insight blocks, no plan-mode disclaimers, no token-usage stats.
- If you have nothing for a section, write exactly: `Nothing high-confidence.`
```

## Synthesis rules

When merging the three outputs, apply each filter in order:

**1. PR-body dedup.** Drop any finding that is acknowledged in `/tmp/triple-review-pr-body.md` as a known issue, an intentional deviation, or a planned follow-up. The author already triaged these — surfacing them again is noise.

**2. Model verification.** Before keeping a finding, the orchestrating model must inspect the cited code in the review worktree. Drop claims that cannot be verified from the local code, diff, or PR metadata. Do not accept a claim only because multiple reviewers repeated it.

**3. Consensus or strong evidence — KEEP if:**
- ≥2 of the three reviewers flagged it (independent foundation models converging = high confidence), OR
- 1 reviewer flagged it AND it has a concrete `file:line` AND a reproducible trigger AND non-trivial impact

**4. DROP if:**
- Only one reviewer flagged it and the evidence is vague (no anchor, no repro)
- It's a style preference without concrete justification
- It's about code outside the diff and not clearly affected by it
- Two reviewers contradict each other and the third is silent

**5. Cross-Claude convergence ≠ independence.** If two findings agree but both came from Claude variants (e.g. an earlier session and the triple-review claude), treat as a single source. Only multi-FAMILY agreement (codex/GPT + claude + gemini, in any pair) counts as consensus. This is the lesson from a prior false positive where two Claude agents asserted an `unstable_cache` cross-user leak that didn't actually exist.

**6. Attribute every surviving finding** ("Cited by: codex, gemini"). Attribution is the user's calibration tool — they learn over time which model is reliable on which axis.

## Final output format

Save to the artifact location AND return the same content to the user. Use this exact structure:

```
# Triple Review — <PR number / branch name>

Reviewers: codex · claude · gemini    Filter: model verification + consensus + PR-body dedup
Saved: <path to REVIEW.md>

## Summary

<one paragraph: shippable as-is / shippable after N fixes / needs rework, plus
the single most important finding>

## Block merge

| # | Conf | File:Line | Issue | Repro | Fix | Effort |
|---|---|---|---|---|---|---|
| 1 | 🟢🟢🟢 | path:line | one-line | one-line | one-line | 5/30/60 min |
| ... |

## Follow-up (next PR)

| # | Conf | File:Line | Issue | Fix |
|---|---|---|---|---|
| ... |

## Nice-to-have

- bullet — file:line — one-line fix
- ...

## Verified false positives (if any reviewer raised one and it didn't survive)

| Claim | Why dropped |
|---|---|

## Reviewer attribution

For each surviving finding: which models agreed.

---

Confidence legend:
- 🟢🟢🟢 = consensus across multiple foundation model families (codex + claude + gemini)
- 🟢🟢 = two model families agreed
- 🟡 = single reviewer, but concrete file:line + repro + non-trivial impact
- ⚪ = uncertain — flagged for human review

Raw outputs: /tmp/triple-review-{codex,claude,gemini}.md
```

## Common mistakes

- **Skipping pre-flight.** ~10 seconds checking codex/gh/gemini auth saves a wasted dispatch.
- **Reviewing pasted diffs by default.** Prefer an isolated local worktree so reviewers can inspect surrounding code while staying away from the user's active checkout.
- **Letting reviewer agents mutate state.** The orchestrating model creates the worktree. Reviewers inspect only.
- **Running serially.** All three CLIs in one parallel batch — same message, three Bash calls.
- **Reporting every single-reviewer finding.** That's exactly the noise the consensus filter is designed to drop.
- **Treating consensus as proof.** Always verify surviving candidates against the local code before reporting them.
- **Treating cross-Claude agreement as independence.** Only multi-family convergence counts.
- **Letting reviewers wander outside the diff.** The prompt says "lines in the diff (or directly affected)" — keep it strict at synthesis too.
- **Skipping `Nothing high-confidence.`** when a section is empty. An empty section is a real signal — show it.
- **Forgetting attribution.** "Cited by: ..." is what makes the report trustworthy and improvable over time.
- **Forgetting the PR-body dedup.** Authors often document known issues in the PR description — re-flagging them is noise.
- **Re-running on a 5000-line diff without warning.** Warn first, let the user split or proceed.
- **Leaving the report only in chat scroll.** Save to `REVIEW.md` so it survives compaction, attaches to PRs, and can be diffed against the next iteration.
- **Static-only review.** If the project has a fast `bun typecheck` / `next build --no-lint` / `bun test` step, mention to the user that running it once and pasting the output into the prompt would catch a class of false positives (e.g. "this types as `any`" claims).
