# Review rubric

Apply only relevant lenses and trace claims beyond the diff when needed.

## Correctness and regressions

Check happy and failure paths, empty and boundary inputs, error propagation, state transitions, stale state, concurrency, repeated execution, partial failure, and compatibility with existing callers. A possible condition is a finding only when its path is reachable.

## Root cause

Look for guards, retries, casts, fallbacks, or comments that hide a broken invariant or patch the wrong layer. Determine whether the change fixes the owning contract or merely masks a symptom.

## Structural integrity

Check ownership, coupling, abstraction level, validation boundaries, data-model fit, and whether the change reads as integrated or bolted on. Flag compatibility layers that have no remaining consumer. Do not penalize simple code for lacking speculative abstraction.

## Verification

Check that tests cover behavior and the reported bug or integration path. Prefer proof against the real output over proxies or self-reports. For async or delegated work, inspect artifacts when possible.

## Complexity budget

Flag complexity without a current need: scattered special cases, unnecessary configuration, single-use abstractions, thin wrappers, dead paths, duplicated canonical helpers, or magic behavior. Prefer a few high-impact structural findings over cosmetic volume.

## Security

Trace untrusted input to dangerous sinks, authentication and authorization decisions, secret exposure, unsafe serialization or rendering, and security-sensitive time-of-check/time-of-use behavior. Do not report generic possibilities without source-to-sink evidence.
