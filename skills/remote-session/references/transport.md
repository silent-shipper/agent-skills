# Configured T3 over SSH

This fallback was exercised against T3 `0.0.46-nightly.20261011.2980` on the
configured Mini. Prefer native environment-targeted tools when available. SSH
uses existing authentication with strict host-key checks, not new host setup.

The Mini was verified at `surge@100.108.123.39` on 2026-10-12, with Tailscale DNS
`surges-mac-mini.tail5f24e1.ts.net`. Confirm the current device mapping. The saved
SSH host key is under the IP; strict checking of the DNS name failed. Use the
verified known-host entry rather than disabling host-key checks.

Read-only probe (creates and revokes a scoped read session; no new thread):

```sh
python3 scripts/remote_session.py probe --ssh surge@100.108.123.39
```

Prepare the private context file and inspect the complete dirty-file list. Pass
every new work file needed by the continuation with `--file`; paths are relative
to the current checkout. Preserve inherited model options and modes from
`orchestrator_capabilities` rather than using the example as a model default.

```sh
python3 scripts/remote_session.py send \
  --ssh surge@100.108.123.39 \
  --repo /Users/surge/Projects/metamask-e2e \
  --context /private/tmp/handoff.md \
  --title 'Continue benchmark work on Mac mini' \
  --provider codex --model gpt-6.1-sol --model-options '{"reasoningEffort":"high"}' \
  --runtime-mode auto --interaction-mode default \
  --file evals/express.mjs --file src/verification/handover.mjs
```

The helper discovers the running CLI from the PID in
`~/.t3/userdata/server-runtime.json`. Use `--t3-home` only for a configured
nondefault data directory. Its normal bearer sessions authenticate the app's
HTTP/WebSocket orchestration interface. They are not provider MCP credentials:
feeding these tokens to `/mcp` produced HTTP 401 in the actual handoff.

`send` requires fresh successful skill sync receipts on both hosts and compares
complete skill source hashes before launching. For a task that depends on
metamask-e2e, add `--toolkit-root /source/task/toolkit` and
`--remote-toolkit-root /target/task/toolkit`. Stage a differing task toolkit using
its source snapshot first. The gate compares the existing verifier's source digest;
it does not copy credentials, overwrite toolkits, or establish runner login.

The app-owned interfaces used are `/api/projects`, `/api/projects/mutate`,
`/api/orchestration/threads/<id>` with `x-t3-orchestration-protocol: 2`, and `/ws`
with `orchestrationProtocol=2` and the `orchestration.launchThread` RPC. The RPC
prepares the workspace before starting the agent. The helper registers the
existing repository only when missing, using a separate short-lived session
with the required `settings:write` scope. It never edits the T3 database directly.

On an incompatible interface, stop with the actual error and inspect the current
T3 tool/CLI documentation. Do not guess alternate mutation routes, weaken auth,
or change the remote service. The helper prints only launch/status metadata;
tokens stay in memory. Source staging remains available for the new thread.
