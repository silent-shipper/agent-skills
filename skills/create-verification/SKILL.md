---
name: create-verification
description: Verify Defuse changes with focused module tests and evidence-backed Tester Army using the funded MetaMask test account. Use for feature verification and regression checks, not the client portal or intents explorer.
---

# Create Verification

Resolve the existing personal toolkit on this host once:

```bash
VERIFY_TOOLKIT_ROOT="$(python3 ~/.agents/skill-config/scripts/skills.py toolkit-root)"
```

Stop if resolution fails. `METAMASK_E2E_ROOT` selects an explicit checkout when
needed; otherwise the resolver checks the two installed Mac locations. Use the
same resolved root for every command, guide, feature map and evidence path.
The root check proves installed scripts and documentation, not external runner
login or browser readiness; use the toolkit's doctor before queueing.
Reuse its funded test account, configured wallet, credentials and ChatGPT connection.
Funds are provided for real feature development and verification. The user has
given standing authorization to spend from this dedicated test account; do not
ask for separate spending approval. When the requested behavior requires an
account action, execute it through the target app UI using the smallest viable
amount that proves the behavior. The dedicated test
wallet approves normal requests from that app UI, including limit orders, other
assets, typed-data signing and transactions. Do not apply the CLI preparation
swap allowlist or spending caps as a UI signing gate. Inspect live balances first. Normal feature
verification needs no packaging, new account, wallet rebuild or copied tooling.

## Requirement

Invoking this skill means the change must be proven, not planned. Run every proof
chosen below before reporting completion; for any UI or account behavior that
includes a live managed run (`verify:app`) performing the real account action, such
as the swap, order or send itself. A plan, charter, preview, unit test or login
alone is never completion. Do not ask before running or before spending from the
test account. If a run cannot start or finish, report it blocked with the exact
cause and what remains unproven. Tester Army logs in through MetaMask itself; never
substitute Playwright, a preview route or screenshots because login looks hard.
Claim completion only by citing the run's `result.json` status and code for the
current source; an edit or merge after the run makes it stale until rerun or
accepted. Never dismiss a failed run or tester finding as a glitch without evidence
from its proof. `STEPS_RECOVERED` means every declared outcome passed after an
earlier step failed: read those steps in `tester/report.json` and decide case by case.
Report a product symptom (a stuck control, a wrong or empty list) as a finding; if it
was a tester misstep, say so and cite the run with that caveat.

## Choose the proof

Read the target checkout's app guidance, owning Module/tests and, for browser
work, `apps/defuse-near/test/CONTRACT.md`. Define acceptance criteria before
implementing a new feature or verifying a change: required account state, user
action and observable outcome, including relevant failure, cancellation or
empty-state behavior.

For resting limit-order placement, place a small real order, assert its identity,
amount, price and `OPEN` state, then cancel that test order and reconcile its
refund. Login, balances, previews and lower-layer tests cannot replace the account
action under test.

- Logic/machines/API payloads/CLI: run the narrow owning test from its workspace
  (`bun run test --run <test-file> --maxWorkers=2 --minWorkers=1`); typecheck when relevant.
- Browser behavior: use a focused Tester Army charter with the toolkit's `verify:app`.
  Planning, preflight and execution share the same runner policy. Choose the
  smallest checks that prove the requested change; missing charters block.
- Visual, layout or styling change: look at the result before and after the edit.
  Charter each changed route in the session it needs (authenticated routes need
  the MetaMask login), declare one readiness outcome, and ask Tester Army to call
  `capture_view` at the requested breakpoints and color schemes. Open the PNGs listed
  under `links.captures`, compare them with the request or reference image, and
  iterate until they match. Captures are review evidence: report what you saw, never
  "verified". Never borrow an unrelated catalog charter, such as a guest shell check,
  for a page it does not open.
- Existing Tier1 regression: run an exact spec or named test only when it checks
  an affected regression or the user requests it. State the behavior it proves;
  invoking this skill alone does not require a Playwright spec or Tier1 suite.
- Missing holdings/history/entitlements: report the prerequisite and run an
  independent lower-layer proof. Unknown/loading/error never means zero.

- Declare settlement, refund or balance proof as its own independent outcome.
  For persistence, reload and recheck the same resource in the new document.
- For features unknown to the toolkit, discover the UI/API contract and generic
  proof primitive, then specify a real configured-account UI action and outcomes.
  If the contract or recipient is missing, name that prerequisite and the UI
  journey to run once it is available.

List the required behaviors and proof layer before running. Map each behavior
to an executed assertion and evidence path or a failed/blocked result afterward.
Inspect actual prerequisites per action: a read-only quote may not require funds.
Account preflight gates only the journey whose UI or owning fixture requires
that state; continue independent public UI, metadata and module checks. Settlement
asset limits do not prohibit read-only quote checks for other assets. Keep a
lower-layer proof distinct from an unexecuted UI journey. Login readiness alone
does not prove the feature. For recurring token availability, metadata or quote
checks, adapt the short [feature proof prompts](references/feature-proofs.md)
to the current target.

## Verify in the browser

Before queueing, check the acceptance criteria against the original request and
changed behavior, independently of the implementation's current output. For a
behavioral change, have a focused reviewer check for omitted actions, surfaces
and state transitions. Then write a feature charter with `goal`, immutable `requiredOutcomes`
and action-specific `prerequisites`. Every outcome has an ID, evidence kind and
exact expected hooks/values; bind lifecycle/UI checks to the same resource. Print a
maintained example with `npm --prefix "$VERIFY_TOOLKIT_ROOT" run queue -- charter <feature-id>`
(`charter --list` lists them), or author an arbitrary feature charter using the toolkit prompt guide at `$VERIFY_TOOLKIT_ROOT/docs/prompt-verification.md`.
Pass `--charter /absolute/path/to/charter.json`; a free-form goal alone cannot pass.
Before any run, lint it: `node "$VERIFY_TOOLKIT_ROOT/src/verification/charter-lint.mjs" --app . --charter <file>`
must pass. Fix every problem it reports. Bind dynamic row IDs with resource templates, never
wildcards. Take expected values from `test/CONTRACT.md` or a bound resource, never guess them.
Keep a charter to ten outcomes or fewer and split longer journeys into separate charters.
Authenticated goals ask the tester to log in; it calls `login_with_metamask`,
then records the session outcome before feature checks. Describe login steps only when the
login controls are the feature under test.
Use each declared `outcomeId` when recording proof.

From the target checkout's `apps/defuse-near`, use the toolkit commands below; the app
needs no verifier of its own, only its `/api/verification-identity` route. `verify:app`
submits the managed Tester Army job, binds the served source and reads canonical evidence.
Next starts after queue admission and closes afterward. Fix compilation failures
before retrying. A verification runs its preflight (charter, identity route, app environment,
dependencies, dev server, disk, cleanup gate) before it is queued; a blocked preflight
names a remedy. Fix the prerequisite and rerun; never skip browser proof because a
checkout lacks setup. Check first with `queue -- doctor --app . --charter <file>`. `--url "$VERIFY_APP_URL"` before the
`--` reuses a caller-owned server; another checkout or production cannot prove local edits.

```bash
npm --prefix "$VERIFY_TOOLKIT_ROOT" run verify:app -- -- --charter /tmp/feature-charter.json
# For a maintained catalog charter:
npm --prefix "$VERIFY_TOOLKIT_ROOT" run verify:app -- -- --feature auth.metamask
# Recheck after your final edit, using the emitted jobId and current criteria:
npm --prefix "$VERIFY_TOOLKIT_ROOT" run queue -- accept <job-id> --charter /tmp/feature-charter.json
```

For a refactor or any change that touches several features or commits, write one batch spec
(cells of app checkout and charter or catalog feature, with repeats) and run
`npm --prefix "$VERIFY_TOOLKIT_ROOT" run queue -- batch run <spec.json>`. Rerun the same
command to resume: finished cells are reused only while their app source, charter and toolkit are
unchanged. A held batch names its remedy (repeated infrastructure blocks, or a funded attempt to
reconcile before `--reconciled`). `queue -- batch status <spec.json>` prints the evidence matrix.

Keep the historical run verdict separate from current acceptance. A source or
charter change blocks reuse; do not claim an earlier pass proves the edited patch.
A mapped charter can be rechecked with `accept <job-id> --feature <feature-id>`.

All browser checks and large unit suites use this shared queue across Codex and
Claude; keep coding in parallel. Do not start verification servers before queue
admission. Use `npm --prefix "$VERIFY_TOOLKIT_ROOT" run queue -- run -- <command>`
for other heavy checks; typecheck, unit test, lint and build commands use a separate work
lane and do not wait behind browser runs. To wait for a running verification, call
`queue -- wait <job-uuid>` (or `--app <apps/defuse-near>`) through the same npm prefix
instead of polling `status`; exit 3 means still queued, so call it again. Use
`queue -- cancel <job-uuid>` to stop one. Waiting/completed queue states are not feature proof.

Replace the example charter with the feature's actions and exact expected hooks.
Record every outcome with `verify_observation` or the account verification tools.
The CLI runs Tester Army directly and checks identity, readiness and unresolved
operations; generating a test file is optional.

- Use semantic hooks/state waits. No sleeps, forced/coordinate clicks, mock
  wallets, React internals or machine events to bypass behavior. Add missing
  hooks at the owning Interface and update `test/CONTRACT.md`.
- When a required interaction repeatedly fails, inspect the trace to distinguish
  a runner limitation from a product defect before queuing another identical
  attempt. Preserve the run’s canonical verdict. If the runner cannot drive the
  control, use or add an owning semantic helper in the managed session. A separate
  helper-only test is supplemental.
- AI navigates the app; deterministic tools own real MetaMask popups. Keep
  credentials/auth payloads out of goals and shared evidence.
- Match account, balance plane and exact asset variant. Current ordinary Defuse
  screens use Confidential funds; public migration/legacy routes select public
  funds explicitly. There is no global mode switch. Require session readiness.
- Keep explicitly read-only and review-only goals read-only. Wallet rejection
  checks stop before financial submission; live order cancellation must prove
  cancellation and refund.
- UI wallet approvals use the prepared account and exact app origin. Use
  `approve_allowed_signature` for signatures, typed data, transactions and network
  prompts; `verify_wallet_request` records completion, which alone is not
  settlement proof. For a resting limit order take a balance checkpoint before
  placement, then use `verify_limit_order` for `open` and `refunded` around the
  same order's UI cancellation. Preserve independent UI amount/price assertions.
  Use `verify_operation` for a UI swap's independent settlement and balance proof.
  CLI balance preparation retains its separate bounded same-account Confidential
  USDC/NEAR policy. Repair missing outcome
  support in existing tooling without reintroducing a swap-only UI signing gate.
  Reconcile ambiguous submissions before retrying; never blindly resubmit.

For setup or tool details only, read the existing
toolkit prompt guide at `$VERIFY_TOOLKIT_ROOT/docs/prompt-verification.md`.

## Keep the feature map current

Use the active toolkit checkout's `catalog/<app>.json` as the feature map;
`queue -- charter --list --app <app>` exposes its recipes. When the task changes
mapped navigation, routes, source locations, hooks or prerequisites, reconcile
that entry against the owning app source and follow the toolkit's documented
maintenance check. Keep navigation, source anchors, gotchas and required
outcomes together. Distinguish stale documentation, a harness gap and a product
regression; never delete intended behavior to make a check green. Name any
unmapped surfaces relevant to the task. Static maintenance is not live proof:
run the affected journey before claiming the behavior verified. Use the same
toolkit checkout for the map and the verification run.

## Regression and evidence

For a relevant existing Tier1 regression or an explicit request, queue the exact
spec/named test below. Tier1 is an explicit regression path; `verify:app` uses Tester Army.

```bash
npm --prefix "$VERIFY_TOOLKIT_ROOT" run queue -- run -- bunx playwright test test/modules/<module>/<file>.spec.ts --project=tier1 --workers=1 --retries=0 --grep '<exact regression name>'
```

Use its owned fixtures/helpers; do not transplant wallets into Synpress fixtures.
For new business logic, durable behavior changes and bug fixes, add or update
the owning regression test at the lowest sufficient layer. For a bug fix, prove
the same assertion fails for the intended defect on baseline and passes on the
candidate; run that exact test by its full name so unrelated passing tests cannot
satisfy it. Keep coverage proportional; cosmetic
edits do not automatically need new regression tests, but they always need visual
captures of the changed views.
Keep task checks/reports ignored; retain regression tests after they pass on
current source. A blocked browser does not stop independent tests.

Inspect `result.json`, `proof.json` and `tester/report.json` in the emitted
`metamask-e2e/.e2e/verification/<run>/`. A result that did not pass carries `reason` (the
tester's stop summary and first unfinished step), `toolErrors` and `explanation` (meaning and
next step); `queue -- explain <CODE>` describes any code. `diagnostics` lists the app's 5xx
responses and page errors during the run and quoted tester claims that no observed screen text
contains; check them before calling a failure a product bug or a tester misstep. Passing requires recorded assertions and
a finished journey; financial proof also needs reconciled receipts/balance
evidence. AI prose or exit zero alone is insufficient. Missing/skipped/timed-out
or incomplete proof is blocked. Inspect existing runners' reports equally.

For Tester Army, use the app verifier's accepted status for completion and `queue -- inspect
<job-uuid>` for the historical canonical headline, required
outcome coverage, source identity, resource links and failed/blocked gaps. Source
proof is observed mutable source unless the report establishes a stronger target.
A later recovery is separate evidence and never changes the original failed run.
For an interrupted funded action, recover only its exact persisted resources with
`--recover-run <run-id> --charter <recovery-charter>`; do not resubmit funding.
Report target, exact command, passed/failed/blocked result, assertions, evidence
path and remaining gaps. Keep authenticated traces private. A task check does
not establish full Tier1 coverage.
