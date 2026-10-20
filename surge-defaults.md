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
  Standing grants: spending from the funded MetaMask test account for
  verification, and finishing every PR when asked to resolve a stack. Shipping
  is scoped to the repository the user named; ask before changing another.
- Lead with the result or decision. For a plan, implementation or PR review,
  automatically give a short `status` catch-up: what the change does, why it is
  worth doing, meaningful proof, remaining gaps and what waits on the user.
  Include actual changed-file counts for completed changes and clearly labeled
  estimates for plans. Keep it under about 80 words with at most 3 change
  bullets; give more detail only when the user asks.

Personal skills with the same name share one maintained source through aliases.
At the start of coding work, run `python3 ~/.agents/skill-config/scripts/skills.py ready`
once. If stale, run `sync` and recheck; a blocked sync must be stated and resolved
before relying on changed skills. Independent repo inspection can continue.
The receipt proves installed content, not text already loaded into this session;
re-read required changed skills and start a new session for discovery changes.

Keep `~/.agents/skill-config` as the clean published installation. To change
personal skills or defaults, run `python3 ~/.agents/skill-config/scripts/skills.py edit <task>`
and edit the returned worktree. Validate there, review and commit the intended
paths, then run its `scripts/skills.py publish --peer <user@other-mac>`.
Completing a requested shared skill change includes publication and verification
on both configured Macs unless the user requests local-only work. Report a
blocked peer or publication explicitly; never label a local edit synced.

Keep shared toolkit development in task worktrees. Before verification, select
the intended toolkit, record `skills.py toolkit-identity`, and use that same root
throughout. A dirty default toolkit blocks implicit selection; an experimental
task checkout must be selected explicitly with `METAMASK_E2E_ROOT`. Preserve
running jobs and their frozen snapshots when publishing newer tooling. Ordinary
app repos use Git branches and task worktrees; never background-pull or mirror
an active worktree. Cross-machine continuation uses a verified source handoff.

If a historical skill link is missing, resolve the installed skill by name before
asking the user to repair it. Run `python3 /Users/surge/.agents/check-skills.py`
after changing personal skill files, links or discovery settings.
