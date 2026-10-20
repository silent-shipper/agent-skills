# Open or update the PR

Push the branch using its configured remote; set an upstream when needed. Check
for an existing PR before creating one. Update its description when the final
scope changes. Use this exact PR-body format, preserving headings, order and
field labels. Put repository-required details in the relevant sections:

```markdown
**Risk: <Ultra low | Low | Medium | High>** — <one clause on why>

## Summary

<diagram, diff-sketch, or tree>

## Screenshots

<only when the UI changed: one captioned image per changed screen or state>

## Verified in browser

- <one behavior checked in a real browser, in plain words>

## Merge Danger

**Door:** <one-way or two-way>

<optional: description>

**Blast Radius:** <one-word description>

<optional: potential ramifications of merge>
```

Keep prose brief and use the repository's domain language (`GLOSSARY.md` when
present). Choose the smallest visual that explains the change. Never invent a
result or a screenshot.

Open with the risk line so a reviewer knows in one glance how much attention
the PR needs. Use the browser proof and Merge Danger to pick the level:

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

### Screenshots

Include `## Screenshots` whenever the PR changes anything visible in the UI;
omit the section only when nothing visible changed. Show the resulting state of
each changed screen or state, with a short caption, and add the before image
when it is readily available. Use the screenshots captured while verifying this
head.

`gh` cannot attach images, so publish them to the repository's `pr-assets`
branch, which holds only images and never merges:

```bash
if git fetch origin pr-assets 2>/dev/null; then
  git worktree add -B pr-assets /tmp/pr-assets origin/pr-assets
else
  git worktree add --orphan -b pr-assets /tmp/pr-assets
fi
mkdir -p /tmp/pr-assets/<branch> && cp <screenshots> /tmp/pr-assets/<branch>/
git -C /tmp/pr-assets add <branch> && git -C /tmp/pr-assets commit -m "assets: <branch>"
git -C /tmp/pr-assets push origin pr-assets && git worktree remove /tmp/pr-assets
```

Reference each image as
`![<caption>](https://github.com/<owner>/<repo>/blob/pr-assets/<branch>/<file>.png?raw=true)`
so it renders for anyone who can read the repository. If publishing is
impossible, say so in one line under `## Screenshots` instead of dropping the
section.

### Verified in browser

List only what was checked in a real browser, one short bullet per behavior, in
words a reviewer understands without the code. Lead with the outcome. Leave
out tests, lint, typecheck, build, CI, job IDs, tool or agent names and how the
proof was collected. When nothing was checked in a browser, write one bullet
instead: `- Not verified in browser: <reason>` or `- n/a: no UI or user flow
changed`. The `agent-guard` hook denies `gh pr create`/`gh pr edit` bodies
without a `## Verified in browser` section containing a bullet, or with
unfilled placeholders.

Example:

```markdown
## Screenshots

![Swap status after success](https://github.com/org/repo/blob/pr-assets/feat-swap-summary/after.png?raw=true)

## Verified in browser

- A completed swap collapses its steps into "Swap complete".
- A failed swap still shows each step and the error.
- The status card fits a 375 px mobile screen.
```

Put untested behavior that could change a merge decision in the Merge Danger
description. Explain reversibility, affected users/consumers and material
failure, migration or rollback risks under Merge Danger, with detail
proportional to the change.

For a multiline body, write the exact text to a temporary file and use
`gh pr create --body-file <file>` or `gh pr edit --body-file <file>`.

Share the PR URL and current head while CI runs. This is a progress update;
shipping with requested CI follow-through is complete when that head's required
checks have passed and supported blocking or highly relevant review findings
have been addressed, or an evidenced external blocker prevents completion.
