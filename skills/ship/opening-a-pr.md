# Open or update the PR

Push the branch using its configured remote; set an upstream when needed. Check
for an existing PR before creating one. Update its description when the final
scope changes. Use this exact PR-body format, preserving headings, order and
field labels. Put repository-required details in the relevant sections:

```markdown
**Risk: <Ultra low | Low | Medium | High>** — <one clause on why>

## Summary

<diagram, diff-sketch, or tree>

## Evidence

- **Before:** <one observable result>
  **After:** <the same result, changed>

**Checks:** <comma-separated passing checks; pending CI>

**Browser:** <verified <evidence link> | not run: <reason> | n/a: <why no UI>>

**Gaps:** <optional: one line of untested or unproven behavior>

## Merge Danger

**Door:** <one-way or two-way>

<optional: description>

**Blast Radius:** <one-word description>

<optional: potential ramifications of merge>
```

Keep prose brief and use the repository's domain language (`GLOSSARY.md` when
present). Choose the smallest visual that explains the change. Use observed
screenshots or exact checks and results as evidence; state missing baseline
evidence and pending checks explicitly. Never invent a before/after result.

Open with the risk line so a reviewer knows in one glance how much attention
the PR needs. Use the evidence and Merge Danger to pick the level:

- **Ultra low:** no user-visible behavior change, two-way door, plain revert,
  proven by tests (moves, renames, dead-code removal, refactors with parity).
- **Low:** small, contained behavior change in one area; two-way door.
- **Medium:** user-facing behavior change across flows, or a notable gap in
  proof.
- **High:** one-way door, funds, auth, data migration, or wide blast radius.

The clause names the reason in plain words, for example
`**Risk: Ultra low** — moves System Status into one folder; no behavior
change, plain revert.` Keep it consistent with Merge Danger; never round a
risk down to make the PR look easier.

Keep Evidence scannable for a reviewer who reads it once:

- Use one to three Before/After pairs, each about one behavior a reviewer
  cares about, in one short sentence per side. Lead with the number or outcome.
- Put lint, typecheck, build, formatting and suite counts on the single
  `Checks:` line, not in the pairs.
- Leave out process narration: verification job IDs, tool or agent names,
  review rounds, "source-matched"/"VERIFIED" status, hooks or harness details
  used to collect proof, and file-match confirmations.
- `Browser:` states whether the changed user flow was exercised in a real
  browser, with the evidence link, or why not. A "not run" line is honest; a
  missing line is a claim of proof without proof. The `agent-guard` hook denies
  `gh pr create`/`gh pr edit` bodies without an Evidence section containing an
  After result, `Checks:` and `Browser:` lines, or with unfilled placeholders.
- Put at most one line of unproven behavior under `Gaps:`; move rollout risk
  to Merge Danger. Omit `Gaps:` when there are none.
- If a detail does not change whether a reviewer would merge, drop it.

Example:

```markdown
- **Before:** Cold mobile login took 23.4 s.
  **After:** 18.3 s (22% faster).
- **Before:** 9 of 10 new regression tests failed.
  **After:** All 10 pass.

**Checks:** auth/wallet suite 140/140, typecheck, build, Biome. CI pending.

**Browser:** verified https://github.com/org/repo/pull/12#issuecomment-1 (login on preview)

**Gaps:** Live Coinbase signing not tested.
```

For relevant UI/design changes, include the resulting screenshot in Evidence
when it can be shared using an accessible image attachment or URL.
Explain reversibility, affected users/consumers and material failure, migration
or rollback risks under Merge Danger, with detail proportional to the change.

For a multiline body, write the exact text to a temporary file and use
`gh pr create --body-file <file>` or `gh pr edit --body-file <file>`.

Share the PR URL and current head while CI runs. This is a progress update;
shipping with requested CI follow-through is complete when that head's required
checks have passed and supported blocking or highly relevant review findings
have been addressed, or an evidenced external blocker prevents completion.
