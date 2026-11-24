---
name: ship-it
description: "Commit, push, open or update a PR, follow CI and review feedback, and land PRs and stacks: fix conflicts and CI, settle CodeRabbit, Codex and human review threads, approve and merge. Use for $ship, \"ship it\", \"just ship\", \"push this\", \"open a PR\", \"commit and push\", \"check on PR X\", \"babysit this\", \"get it green\", \"fix conflicts\", \"fix CI here\", \"solve the comments\", \"approve and merge\", \"merge the stack\" or \"land this\", even when no commit or push is requested. Respect local-only checkpoints."
---

# Ship it

Ship the agreed change and verify the latest PR revision. Use the repository's
actual commands, checks and contribution rules. `$ship` and "ship it" mean this
skill, never Claude Code's bundled `/ship`, which does not merge.

## Scope and authorization

Confirm the checkout, branch, intended diff and requested endpoint from the
session. Ship only to the repository the user named; "ship to main" is scoped to
that repository. Changing another repository needs the user's confirmation; the
installed `agent-guard` hook asks before a push, PR create, edit or merge that
targets a repository other than the session's, and checks PR-body browser
receipts as described in [opening-a-pr.md](opening-a-pr.md). A PR in a GitHub
stack means the whole stack: a request to fix, review, approve, ship or merge it
covers every layer, whoever authored it. Existing explicit authorization persists: "ship it", "push this" and
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
- Before the first push of a behavior change, review the final diff with
  `interrogate`, including one reviewer from a different provider family when
  available. Fix confirmed Act-on findings, reverify, and review the changed
  paths again. Size the re-check to the new diff: after a rebase, a
  conflict resolution or a minor fix, run one focused verifier at the new head;
  a wording-only change needs none. Run the full review and browser
  verification again only for new behavior, a redesign or a large new diff.
  Stop after a round with no Act-on finding or after 3 rounds, and
  list what remains in the result. Honor a requested round count. Skip this for
  docs-only changes.
- When anything visible in the UI changes, capture and inspect a screenshot of
  each changed screen or state; they go in the PR description. Reuse
  screenshots from verification of the same source revision; add a before
  screenshot when readily available. If capture is unavailable, state the
  concrete limitation and continue the remaining shipping work.
- Commit in coherent pieces with concise conventional messages explaining the
  problem or resulting behavior. Do not split a small change into arbitrary
  code/test commits.

## Open the PR, then babysit it

Shipping has two halves. A shipping request ("ship it", "push this", "commit
and push") runs both, with the second in `drive` mode. "Open a PR" alone, or a
draft-only request, stops after the first.

1. [Open or update the PR](opening-a-pr.md): push, the exact PR-body format,
   risk, screenshots, browser verification and Merge Danger.
2. [Babysit the PR](babysit.md): declare a mode, fix a stack from the bottom,
   classify CI failures before any retry, and triage review feedback.

A PR-status request alone ("check on PR 12", "get it green", "address the
CodeRabbit comments") starts at the second half. A landing request ("fix the
conflicts and merge", "approve and merge") starts there too and ends with
[Land](#land-a-pr-or-stack).

## Land a PR or stack

A merge request ("merge", "land", "approve and merge", "fix the conflicts and
merge") asks for one outcome: the PR merged. Without one, stop at the step
asked for: "approve" approves, and "fix CI", "fix conflicts" or "solve the
comments" end with the PR ready and a report. Read its stack first
(`gh api repos/<owner>/<repo>/pulls/<n> --jq .stack`; `stacks/<number>` lists
the layers bottom first). Run several requested PRs or stacks in parallel, one
worker per stack in its own worktree; browser runs still take the queue one at
a time.

Each of these requests authorizes, on every layer and whoever wrote it, the
steps it needs: updating it with its base and resolving conflicts (a stack
rebase is pushed with `--force-with-lease`), pushing fixes for failures the PR
causes, replying to and resolving review threads, asking a bot to re-review,
and dismissing a bot's stale change request once its findings are fixed or
answered. "Approve" adds approving each layer on its live head with an empty
body; a merge request adds that and the stack merge. Do all of it without
asking. Stop only for:

- a person's open change request;
- a fix that would change what the PR does rather than make it pass;
- a red check you can't attribute after reading its log ([babysit](babysit.md));
- anything outside standing grants: production data, real money beyond the
  test account, another repository.

Report each as `Blocker: what → who` and finish the rest. Pending checks are
not a stop: watch the PR and continue when it wakes you. When the permission
check refuses a step, give the user the exact command and carry on with the
other steps.

Review threads: fix each relevant finding and reply with the commit, answer the
others in one or two plain sentences, then resolve every thread. Bots follow
the repository's own rules; `.coderabbit.yaml` says how CodeRabbit approves.

Merge the stack as one unit from its top PR once every layer is approved on its
live head and its checks are settled: T3 `pull_request_merge` with
`number: <top>`, `stack: true`, `method: "squash"` and
`expectedHeadSha: <top head>`. Without T3, run
`gh api -X PUT repos/<owner>/<repo>/pulls/<top>/merge-async -f merge_method=squash -f sha=<top head>`
and poll the returned uuid. Never merge a layer alone; `agent-guard` denies it.
When GitHub splits a stack (one layer with two children), say so and merge each
branch from its own top.

## Final result

Write the final reply with `status`: the PR link, that checks ran on the
latest head, meaningful changes, CI status and CodeRabbit/Codex feedback
disposition: fixed findings, relevant deferred findings
and material remaining gaps. Include actual changed-file counts. State completion
only when the requested endpoint is met; show an evidenced blocker plainly.
For relevant UI/design changes, show the resulting screenshot inline when
supported, otherwise link to the image artifact. State any capture or sharing
limitation briefly.
