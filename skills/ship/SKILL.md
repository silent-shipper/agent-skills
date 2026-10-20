---
name: ship
description: Commit, push, open or update a PR, follow CI, and address consequential CodeRabbit and Codex PR feedback when the user requests shipping, "ship it", "push this", "open a PR", "commit and push", or PR status such as "check on PR X", "babysit this" or "get it green". Respect local-only checkpoints.
---

# Ship

Ship the agreed change and verify the latest PR revision. Use the repository's
actual commands, checks and contribution rules.

## Scope and authorization

Confirm the checkout, branch, intended diff and requested endpoint from the
session. Ship only to the repository the user named; "ship to main" is scoped to
that repository. Changing another repository needs the user's confirmation; the
installed `agent-guard` hook asks before a push, PR create, edit or merge that
targets a repository other than the session's. A request to resolve, ship or
merge a stack covers every PR in that stack, root first, not only the current one. Existing explicit authorization persists: "ship it", "push this" and
"commit and push" authorize the corresponding actions for this scope. Continue
without a second push-confirmation question. A local-only or draft-only request
remains a checkpoint; if shipping was not authorized, prepare the concrete result
before asking for the missing authorization.

Keep unrelated changes intact. Stage specific paths; never use `git add -A` or
`git add .`. Do not force-push, merge a PR, deploy, or broaden the change unless
the user authorized that action. Do not add a `Co-Authored-By` trailer.

## Prepare and prove

- Review the complete intended diff, including untracked dependencies imported
  by changed files. Include required new files and exclude scratch artifacts,
  credentials, authenticated traces and unrelated formatting.
- Inspect suspicious secret matches to establish whether they are sensitive;
  keep actual secrets out of commits and shared output.
- Run the required repository checks and the narrow tests that prove the changed
  behavior. Reuse evidence for the same source revision. Repeat checks after
  hooks, fixes or conflict resolution change the tested files; committing an
  unchanged tree alone does not require a second full run.
- Fix supported failures within the authorized scope and reverify. Preserve
  test intent. Add or update regression coverage when it catches a demonstrated
  bug or a non-obvious durable behavior; avoid filler tests.
- When a visible UI or design change benefits from visual review, capture and
  inspect a screenshot of the resulting app. Reuse screenshots from verification
  of the same source revision; add a before screenshot when readily available.
  If capture is unavailable, state the concrete limitation and continue the
  remaining shipping work.
- Commit in coherent pieces with concise conventional messages explaining the
  problem or resulting behavior. Do not split a small change into arbitrary
  code/test commits.

## Open the PR, then babysit it

Shipping has two halves. A shipping request ("ship it", "push this", "commit
and push") runs both, with the second in `drive` mode. "Open a PR" alone, or a
draft-only request, stops after the first.

1. [Open or update the PR](opening-a-pr.md): push, the exact PR-body format,
   risk, evidence and Merge Danger.
2. [Babysit the PR](babysit.md): declare a mode, work the lowest unmerged PR
   first, classify CI failures before any retry, and triage review feedback.

A PR-status request alone ("check on PR 12", "get it green", "address the
CodeRabbit comments") starts at the second half.

## Final result

Write the final reply with `status`: the PR link, that checks ran on the
latest head, meaningful changes, CI status and CodeRabbit/Codex feedback
disposition: fixed findings, relevant deferred findings
and material remaining gaps. Include actual changed-file counts. State completion
only when the requested endpoint is met; show an evidenced blocker plainly.
For relevant UI/design changes, show the resulting screenshot inline when
supported, otherwise link to the image artifact. State any capture or sharing
limitation briefly.
