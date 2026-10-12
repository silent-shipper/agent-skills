# Design red flags

Revise or reject a candidate when these appear.

## Shallow module

The public surface is large but hides little. Callers must coordinate several methods for one operation or learn internal stages and policies. Prefer a smaller interface backed by substantial behavior.

## Information leakage

Multiple modules depend on the same representation, protocol, storage, or policy decision. Keep transport and wire types private; parse external data into domain types at the boundary.

## Temporal decomposition

Modules are organized mainly as load, validate, transform, and save stages even though they share one representation and its invariants. Group responsibilities around domain knowledge and ownership instead of execution order.

## Pass-through layer

A method forwards essentially the same arguments to another method without adding policy, adaptation, or a distinct abstraction. Remove it or move responsibility to the module capable of completing the operation.

## Shared mutable state without ownership

Two actors can write the same state but conflict handling is conventional or unspecified. Prefer exclusive or per-actor ownership with an explicit merge/read boundary unless serialization is a real domain requirement.
