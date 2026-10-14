---
name: remote-session
description: Move the current coding session to a configured remote T3 environment when the user asks to hand off, send, or continue this work on another machine. Transfer the worktree state and context, then launch and verify a new remote T3 thread.
---

# Remote session

Continue the same work on the requested machine. A chat summary is not a source
handoff: transfer the exact base revision, tracked changes and new work files.
Prefer an existing configured T3 environment; do not turn this into host setup,
deployment, credential migration or publication.

## Prepare

- Identify the requested environment and repository. Use the configured remote
  T3 connection when tools support targeting that environment. Tools bound to
  the current environment do not launch remotely merely because the prompt says
  “Mac mini.” The last verified Mini transport is documented in the reference.
- Read current project guidance. Record the source HEAD, branch and dirty files.
  Include new work files explicitly; do not silently drop untracked code. Keep
  unrelated target edits intact. Reuse remote credentials and dependencies.
- Check task prerequisites on the target: required skill guidance, runner login,
  wallet setup when relevant, and consumer app revision/contracts. A configured
  T3 service does not establish these. Carry required guidance or resolve its
  installed source; report missing login/configuration rather than silently
  copying credentials. Different app revisions need a fresh validation baseline.
- Require `skills.py ready` on both Macs and matching complete skills source
  hashes. For verification-dependent tasks, pass the helper both `--toolkit-root`
  and `--remote-toolkit-root`, naming the exact task toolkits. Its prelaunch gate
  compares the verifier's native source digest. If they differ, stage the required
  toolkit in an isolated target checkout first; do not overwrite its shared checkout
  or silently substitute whichever toolkit is installed. Capture login readiness
  separately; matching source alone does not establish it.
- Write the handoff context to a private temporary file: intended outcome,
  accepted decisions, authorization/checkpoints, changed owners, exact checks
  and results, evidence locations, active owned jobs, blockers and next actions.
  Distinguish passing proof, failures, cleanup evidence and untested changes.
- Quiesce only this session's owned work when moving execution. Do not cancel
  other threads. Resolve funded actions before cutover; do not run one funded
  wallet concurrently on two hosts. Never copy credentials by default.

## Transfer and launch

Use an environment-targeted `t3_thread_launch` when available, with an explicit
workspace binding and inherited provider/model/options and permission modes.
Uncommitted changes must be staged separately; a new worktree does not inherit
them. Verify the remote environment before creating the thread.

For the configured SSH T3 service, use
[scripts/remote_session.py](scripts/remote_session.py). It stages a Git bundle,
binary patch, selected extra files, context and content manifest. It uses the
existing remote T3 service to prepare a worktree and launch a top-level thread;
the initial message requires importing and verifying the snapshot before work.
The helper uses temporary scoped sessions and revokes them. Read
[references/transport.md](references/transport.md) for its supported transport
and invocation. Do not reuse another agent's token or disable authentication.

The new thread must apply the staged patch/files in its bound worktree, then run
the manifest verifier. A mismatch blocks continuation; preserve the source and
diagnose it. Dependencies, build caches, wallet profiles and environment files
are not worktree source and are not synced automatically. Transfer additional
private evidence only when useful, selected explicitly and checked for secrets.

## Complete

Retain the returned thread ID. Verify its workspace and running/preparing state;
after a lost launch response inspect that ID before considering a retry. Do not
create duplicate conversations. Stop local execution after successful cutover.
Link the new thread as `[title](t3-thread://v1/<threadId>)` and state any remaining
import or verification gap. Distinguish thread launch, verified source sync and
readiness to resume the task.

After source import is verified, read the remote thread's workspace, live run state
and recent activity. Automatically settle the source thread once the remote run
is `running`, has begun the handed-off task and has no pending request. Use the
source environment's `t3_thread_organize` with `action: "settle"`; settlement takes
effect when the source turn completes. Launch acceptance, `preparing`, `queued` or
`starting` alone is insufficient. Keep the source active if the remote thread is
waiting, stopped, failed or its import or execution is unresolved, and report the
exact gap. Respect an explicit request to keep the source thread active. Do not
wait for the remote task to finish before settling after a successful cutover.

This skill does not imply a commit, push, deployment or message to another person.
