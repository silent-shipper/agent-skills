---
name: interrogate
description: Run an adversarial multi-reviewer examination of a diff, branch, design, or selected files, then synthesize findings with lead judgment. Use when the user says "interrogate", "adversarial review", "multi-agent review", "challenge this", "find blind spots", or "tear this apart". Reviewers are read-only; applying findings requires existing authorization for fixes.
---

# Interrogate

Send the same intent, scope, and rubric to multiple independent reviewers, then filter their findings into a pragmatic verdict. This skill explicitly calls for parallel subagents when collaboration tools are available.

Keep reviewers read-only. A review request alone does not authorize code changes. If the session already authorizes implementation or fixes, the lead may apply confirmed in-scope findings after synthesis and reverify; otherwise return the verdict. Do not ask again for authorization already given.

## Determine scope and intent

Identify the exact review target from the user: selected files, supplied patch, working tree, commit, branch diff, or design artifact. For branch review, determine the appropriate base rather than assuming `main`. Include surrounding callers, callees, types, tests, or decision context needed to trace claims.

State the author's intent in one clear paragraph using the request, commit or PR description, and code evidence. Reviewers challenge execution against that intent; they do not redefine the goal. Ask only when intent is materially ambiguous and cannot be recovered safely.

## Launch reviewers

Track Scope, Review, Synthesize, and Verdict in the task plan.

Read [reviewer-prompt.md](references/reviewer-prompt.md), [rubric.md](references/rubric.md), and [code-quality.md](references/code-quality.md). Use two independent read-only reviewers for a bounded change and three for broad or risky changes; honor a requested count. Add reviewers only for a concrete coverage need. Every reviewer receives the same intent, artifact paths or diff, relevant context, rubric, and output contract. Instruct reviewers not to edit files.

Use inherited models by default. Use model overrides only when the user or governing instructions explicitly request them. If several permitted model families are available, diversity can improve blind-spot coverage; otherwise independent contexts still provide useful variance. Do not invent personas merely to force disagreement.

## Synthesize

Parse and deduplicate all findings. Agreement by two or more independent reviewers is stronger evidence, not automatic truth. Lone-reviewer security or correctness findings still deserve careful tracing. Record explicit disagreements.

Read [lead-judgment.md](references/lead-judgment.md). The lead must validate important execution paths against the repository context and classify every distinct finding:

- **Act on:** confirmed correctness, security, regression, or material maintainability issue that should block shipping.
- **Consider:** legitimate tradeoff whose benefit may not outweigh its cost now.
- **Noted:** valid context or low-impact observation with no current action.
- **Dismissed:** incorrect, hypothetical without a reachable path, nitpicky, outside scope, or missing known context.

Keep the `Act on` section small and decisive. Explain dismissals so the user can override the lead's judgment.

## Verdict

Return:

1. **Intent** — the stated intent paragraph.
2. **Scope and reviewers** — artifact reviewed and reviewer count.
3. **Act on** — evidence, location, impact, and which reviewers raised it.
4. **Consider** — evidence and tradeoff.
5. **Noted** — concise observations.
6. **Dismissed** — rejected claims and why.
7. **Agreement map** — consensus, divergence, and what it implies.

When findings will be posted to a PR, first fetch existing review and issue
comments and drop findings already raised. Each posted comment names the user
impact in one sentence, cites the line, and is phrased as a suggestion ("maybe
we should…"), not a demand. Post nits only as short bullets in an approval.

Lead with the verdict and actionable findings; omit empty categories and keep the agreement map compact unless disagreement matters. When no actionable findings survive validation, say so plainly. After authorized fixes, check the changed paths and affected contracts. Repeat the full review only when the new diff or evidence requires it; a completed review with no confirmed blocker is sufficient.
