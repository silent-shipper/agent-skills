---
name: investigate
description: Use when the user reports a bug, unexpected behavior, or asks to "investigate", "debug", "figure out why", "deep dive", or "find the root cause". Also use when deploying subagents to understand a problem before fixing it.
---

# Investigate

Systematic parallel investigation of bugs and unexpected behavior. Decomposes the problem into investigation areas, dispatches subagents, and synthesizes a root-cause report.

## When to Use

- User reports a bug or unexpected behavior
- User says "investigate", "debug", "figure out why", "deep dive", "find the root cause"
- Before attempting any fix for a non-trivial bug
- When you need to understand how multiple parts of the codebase interact

## Workflow

### Step 1 — Clarify the Symptom

If the user hasn't already, confirm:
- **What happens:** The observable behavior
- **What should happen:** The expected behavior
- **When it happens:** Always? First time? After specific action?

Keep this brief — one AskUserQuestion at most. If the user already described the bug clearly, skip straight to Step 2.

### Step 2 — Decompose into Investigation Areas

Based on the symptom, identify 4-6 investigation areas from this map:

| Symptom Category | Areas to Investigate |
|------------------|---------------------|
| **UI not updating / stuck** | Relevant XState machine states + transitions, component rendering logic, provider chain, event handlers |
| **Wrong data displayed** | Data flow from API → service → machine context → component, token type guards, balance computation |
| **Wallet/signing issues** | Wallet verification machine, connect wallet hook, wallet provider, chain-specific signing |
| **Swap/intent failures** | Quote service, 1cs machine, intent status machine, solver relay, abort signal handling |
| **Deposit/withdraw issues** | Chain-specific deposit actors, deposit/withdraw UI machines, bridge service, address generation |
| **Auth/session issues** | Private mode auth hook, wallet verification provider, cookie/storage handling, provider ordering |
| **Performance issues** | Re-render patterns, query invalidation cascading, bundle size, lazy loading boundaries |

**Architecture reference for decomposition:**
- All machines: `src/components/DefuseSDK/features/machines/`
- Services: `src/components/DefuseSDK/services/`
- Hooks: `src/hooks/`
- Providers: `src/providers/`
- Types: `src/components/DefuseSDK/types/`
- Utils: `src/components/DefuseSDK/utils/`

### Step 3 — Dispatch Parallel Subagents

Launch one `Explore` subagent per investigation area using the Task tool. **All in a single message** for maximum parallelism.

Each subagent prompt must include:
1. The specific area to investigate
2. The symptom being investigated (so it knows what to look for)
3. Which files/directories to start from
4. What to return: relevant code paths, state transitions, potential failure points

Example prompt for a subagent:
```
Investigate [AREA] in the defuse-near codebase related to this bug: [SYMPTOM].

Start from: [specific files/dirs]
Look for: [what might cause the symptom]

Return:
1. The relevant code path (file:line references)
2. Any potential failure points or race conditions
3. Whether this area could cause the reported symptom (yes/no/maybe with reasoning)
```

### Step 4 — Synthesize Findings

After all subagents return, produce a structured report:

```markdown
## Root Cause Analysis

**Symptom:** [one line]
**Root Cause:** [one line — the actual WHY]
**Confidence:** High / Medium / Low

### Evidence
- [file:line] — [what this code does wrong]
- [file:line] — [how it connects to the symptom]

### Proposed Fix
- [minimal change description, specific files and what to change]
- Estimated: N files changed, ~M LOC

### Regression Surface
- [what else could break if we change this]
- [callers/consumers of modified code]

### Alternative Explanations (if confidence < High)
- [other possible causes that weren't ruled out]
```

### Step 5 — STOP: Ask Before Fixing

**This is a hard gate. Do not edit any files without explicit user approval.**

Present the root cause report, then ask:
> "Want me to implement this fix, or investigate further?"

Wait for the user to say "yes", "fix it", "go", "implement it", or equivalent.

**Do NOT:**
- Start editing files speculatively
- Apply fixes "while you're at it"
- Resume a previous session where a fix was identified and treat that as permission to proceed
- Interpret "continue" or "keep going" as approval to fix

The investigation phase ends here. Any fix is a new, separate task requiring fresh approval.

## Rules

- **Never guess** — if subagents don't find enough evidence, say so. "I couldn't determine the root cause" is better than a wrong diagnosis.
- **Minimal subagents** — 4-6 is the sweet spot. Don't launch 12. Each should have a focused, distinct scope.
- **File references always** — every finding must include `file:line` so the user can verify.
- **Root cause, not surface** — "the button doesn't work" is a symptom. "The machine never transitions from X to Y because guard Z fails when input is null" is a root cause.
- **Don't fix during investigation** — resist the urge to edit files while researching. Investigate first, fix second.
