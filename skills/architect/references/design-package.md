# Design package

Use this shape for each candidate and the final synthesis. Keep it proportional to the task.

## Problem and constraints

State the outcome, non-obvious integration constraints, invariants, and compatibility boundaries.

## Usage: caller's view

Write this first. Show the intended import and two or three realistic calls, including important failure behavior. The interface is derived from this usage; if they diverge, reconcile the interface to the caller experience.

## Shape

Show core data structures, public types and signatures, ownership, module map, and data flow. State where validation happens, which invariants types encode, what complexity the public surface hides, and what remains exposed.

## Synthesis decision

Name the base candidate, why it won against the rubric, useful ideas incorporated from alternatives, and rejected ideas with reasons.

## Tradeoffs and alternatives

For each tradeoff use: "We accept X in exchange for Y." Name at least one genuinely different alternative and explain why it lost, especially from the caller's perspective.

## Risks and verification

List unresolved questions, migration risks, and how implementation will prove the design works.

## First implementation step

Name the first concrete vertical slice to build against the design.
