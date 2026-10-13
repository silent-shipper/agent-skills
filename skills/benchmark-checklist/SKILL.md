---
name: benchmark-checklist
description: Vet a measured performance, latency, reliability or agent-evaluation claim before reporting it or choosing an option. Use for benchmark results and measured speedups/regressions, not ordinary passing test reports.
---

# Benchmark checklist

Write the claim, workload, success predicate and measurement budget first. Read
what the harness times, counts and omits. Use the project's existing benchmark
owner and cost tiers; do not build another harness or run a cohort per tweak.

Keep app/source, toolkit, charter/corpus, model, account prerequisites and timeout
budgets with each trial where applicable. Freeze them within a comparison. An
evaluator change starts a new cohort. Separate queue wait, setup and execution;
record host load and sleep interruptions rather than silently pooling them.

Before trusting a number, answer the relevant checks from actual evidence:

- **Limiter:** what resource or path bounds it? Profile separately from timed
  trials. If you cannot explain why the result is not twice as good, investigate.
- **Comparable conditions:** production settings, realistic data, versions,
  tuning and warm/cold state must match. Comparing an untuned side does not
  establish which option the user should adopt.
- **Physical bounds:** check time saved against the changed path's share of
  total time, and throughput against CPU, network and storage limits.
- **Correct work:** count errors, skipped/cached work and timeouts. Prove the
  intended work happened inside the timed region and its output was correct.
- **Repeatability:** use the existing cohort design, alternating/interleaving
  sides where possible. For a performance choice without a project design,
  use at least five runs per side and report median and range. A gap smaller
  than the spread is no measurable difference.
- **User relevance:** measure the end-to-end wait, not just a tiny helper.
  Reliability/eval claims need representative tasks, independent acceptance
  criteria and retained unsuccessful attempts; never grade from self-report.

A requested quick ballpark may use one run: still check errors, correct work and
obvious condition mismatches, label it a single observation, and do not select a
winner from it. A pilot catches breakage; it is not a reliability result.

Report faster, slower, no measurable difference or inconclusive with units,
sample counts, spread, identity, queue policy and the limiter or missing proof.
Keep full receipts in the existing evidence artifact. Preserve canonical
failed/blocked results and distinguish completed outcomes from final acceptance.
Do not claim general financial/auth speed gains from guest-only measurements.

Adapted from [Lauren Tan's pstack benchmark checklist](https://github.com/cursor/plugins/blob/1dcc2bacde73ddd284803b7af28164d0436198fc/pstack/skills/benchmark-checklist/SKILL.md). See [LICENSE](LICENSE).
