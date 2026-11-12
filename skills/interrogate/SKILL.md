---
name: interrogate
description: Run an adversarial multi-reviewer examination of a diff, branch, design, or selected files, then synthesize findings with lead judgment. Use when the user says "interrogate", "adversarial review", "multi-agent review", "challenge this", "find blind spots", or "tear this apart". Reviewers prove findings with runs and never edit the reviewed checkout; applying findings requires existing authorization for fixes.
---

# Interrogate

Send the same intent, scope, and rubric to multiple independent reviewers, then filter their findings into a pragmatic verdict. This skill explicitly calls for parallel subagents when collaboration tools are available.

Reviewers try to break the change, and a finding survives only when a run proves it. Reviewers never edit the reviewed checkout; they keep repro scripts and scratch tests in a temporary directory or their own worktree. A review request alone does not authorize code changes. If the session already authorizes implementation or fixes, the lead may apply confirmed in-scope findings after synthesis and reverify; otherwise return the verdict. Do not ask again for authorization already given.

## Determine scope and intent

Identify the exact review target from the user: selected files, supplied patch, working tree, commit, branch diff, or design artifact. For branch review, determine the appropriate base rather than assuming `main`. Include surrounding callers, callees, types, tests, or decision context needed to trace claims.

State the author's intent in one clear paragraph using the request, commit or PR description, and code evidence. Reviewers challenge execution against that intent; they do not redefine the goal. Ask only when intent is materially ambiguous and cannot be recovered safely.

For gated changes, describe the shipped default and the intended enabled behavior. Establish from the request whether the verdict concerns merging disabled, enabling, or releasing. Include the required operating modes in the shared review brief and verification plan. Evidence from the disabled mode supports that mode only; state any required mode that remains unexecuted beside the recommendation.

## Launch reviewers

Track Scope, Review, Synthesize, and Verdict in the task plan.

Read [reviewer-prompt.md](references/reviewer-prompt.md), [rubric.md](references/rubric.md), and [code-quality.md](references/code-quality.md). Use two independent read-only reviewers for a bounded change and three for broad or risky changes; honor a requested count. Add reviewers only for a concrete coverage need. Every reviewer receives the same intent, artifact paths or diff, relevant context, rubric, and output contract. Instruct reviewers not to edit files.

Use inherited models by default. Use model overrides only when the user or governing instructions explicitly request them. If several permitted model families are available, diversity can improve blind-spot coverage; otherwise independent contexts still provide useful variance. Do not invent personas merely to force disagreement.

## Synthesize

Rerun each finding's command yourself. Keep a finding only when the output shows the failure and the failure breaks the intent; drop the rest, and merge findings that share a root cause. A finding nobody could prove with a run goes to `Noted` at most, never `Act on`. Then parse and deduplicate the kept findings. Agreement by two or more independent reviewers is stronger evidence, not automatic truth. Lone-reviewer security or correctness findings still deserve careful tracing. Record explicit disagreements.

Read [lead-judgment.md](references/lead-judgment.md). The lead must validate important execution paths against the repository context and classify every distinct finding:

- **Act on:** a problem shown by a failing run at the head or a doc line the change made wrong: a bug a user would hit, a failed gate or a wrong shipped doc. A problem the base branch already has, whether trunk or the PR below in a stack, blocks only when the change copies it or newly reaches it.
- **Consider:** legitimate tradeoff whose benefit may not outweigh its cost now.
- **Noted:** valid context or low-impact observation with no current action.
- **Dismissed:** incorrect, hypothetical without a reachable path, nitpicky, outside scope, or missing known context.

Keep the `Act on` section small and decisive. Explain dismissals so the user can override the lead's judgment.

## Verdict

Return:

1. **What it does** — two plain sentences without code names: what changes for users in the operating mode being reviewed, distinguishing the shipped default from intended enabled behavior for gated changes; and what prompted it (the linked issue or incident, or "not stated").
2. **Scope and reviewers** — artifact reviewed, reviewer count, executed checks, exercised behavior, mocked or bypassed dependencies, and unproven acceptance criteria.
3. **Act on** — evidence, location, impact, and which reviewers raised it.
4. **Consider** — evidence and tradeoff.
5. **Noted** — concise observations.
6. **Dismissed** — rejected claims and why.
7. **Agreement map** — consensus, divergence, and what it implies.
8. **Draft comment** — the ready-to-paste PR comment for the Act on and
   worthwhile Consider findings, written per unslop's PR comment rules.

In chat, show only the verdict line, one bullet per Act on finding with its
fix, and the draft comment, within the reply limit in the user's defaults.
Write the full verdict (all sections above) to a file and link it.
Keep clearance claims within that evidence scope in both the full verdict and
chat. A known regression remains a regression when classified `Consider`;
accepting its tradeoff does not justify "no regressions." State material
unproven acceptance criteria beside the recommendation.

When findings will be posted to a PR, first fetch existing review and issue
comments and drop findings already raised. Each posted comment cites the line
and follows unslop's rules for PR comments. Post nits only as short bullets in
an approval.

Lead with the verdict and actionable findings; omit empty categories and keep the agreement map compact unless disagreement matters. When no actionable findings survive validation, say so plainly. After authorized fixes, check the changed paths and affected contracts. Repeat the full review only when the new diff or evidence requires it; a completed review with no confirmed blocker is sufficient.
