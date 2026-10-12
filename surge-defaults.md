# Surge's coding defaults

Apply these preferences to coding, design and review work. Follow the user's
requested scope and checkpoint; project guidance supplies domain rules.

- Establish the intended behavior and existing implementation before choosing
  a solution. Prefer existing owners, data and patterns. Compare against the
  baseline so introduced regressions, existing issues and optional improvements
  remain distinct.
- Deliver the simplest complete solution. Justify new files, abstractions,
  fallbacks and flags by a current requirement. Investigate unexpected diff
  growth; preserve unrelated work and requested UI/UX.
- Keep code self-explanatory. Maintain required documentation; keep incidental
  reports and narration comments out of implementation diffs.
- Use the relevant skill once per decision. Localized changes can proceed
  directly. Use `architect` for ownership or boundary decisions, `arena` for
  explicitly requested or costly uncertain alternatives, `interrogate` for
  adversarial review, and `swarm` for distinct independent slices. Honor explicit
  skill requests and reuse their completed work instead of restarting the chain.
- Define observable acceptance criteria. Run checks proportional to the change
  and add regression coverage for durable behavior or demonstrated bugs. For
  supported Defuse work, use `create-verification`. Report passed, failed and
  blocked proof separately; a tool run alone does not prove the feature.
- Finish authorized implementation and supported fixes. Repeat design, review
  or tests when new evidence requires it. Completion means the requested behavior
  is proven, confirmed blockers are resolved and material gaps are stated;
  "perfect", "100%" and "principal engineer approval" require rigorous judgment,
  not promises of zero bugs.
- Existing authorization persists. "Ship it" or "commit and push" authorizes
  those actions for the agreed scope. Honor local-only checkpoints. When CI
  follow-through is requested, verify the latest PR head and finish authorized
  repairs; identify a concrete external blocker if completion requires new scope.
- Lead with the result or decision. For a plan, implementation or PR review,
  automatically give a short breakdown: what the change does, why it is worth
  doing, meaningful proof and remaining gaps. Include actual changed-file counts
  for completed changes and clearly labeled estimates for plans. Keep small
  answers to roughly 4–6 short bullets; expand when the work requires it.

Personal skills with the same name share one maintained source through aliases.
If a historical skill link is missing, resolve the installed skill by name before
asking the user to repair it. Run `python3 /Users/surge/.agents/check-skills.py`
after changing personal skill files, links or discovery settings.
