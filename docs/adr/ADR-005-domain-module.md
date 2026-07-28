# ADR-005: Core domain module (`radio_scheduler.domain`) for shared entities

## Status

Accepted

## Date

2026-07-28

## Context

`docs/architecture_review.md` identified the absence of a canonical "Core/domain module" as a missing piece of the architecture: `scenario_generator`, `scheduling_interface`, `reference_implementations`, and `benchmark` all reference shared concepts (UE, Resource Block, Scenario, Allocation Decision, QoS Class, etc.) by name, but no module was declared the owner of their shape — leaving each module free to informally invent its own, quietly reintroducing coupling the architecture is meant to avoid.

`docs/specification/domain-model-v0.1.md` later resolved the *conceptual* side of this gap — Design Principles, Core Entities, and their relationships are now defined — but did not decide where in the codebase these entities would actually be implemented. That decision is now required to begin implementing `scenario_generator`, which needs concrete `Scenario`, `TTI`, `UE`, and related types to produce output against.

## Decision

Create a new subpackage, **`src/radio_scheduler/domain/`**, containing only the dataclasses corresponding to the entities defined in `docs/specification/domain-model-v0.1.md`'s Core Entities section. `scenario_generator`, `scheduling_interface`, `reference_implementations`, and `benchmark` all import from `domain`. `domain` imports from none of them — a one-way dependency, preventing import cycles and keeping it the single shared foundation the other four modules are built on.

## Alternatives considered

- **Place entities inside `scheduling_interface`** (on the reasoning that `docs/architecture.md` already calls it "the only thing `scenario_generator` and `reference_implementations` have in common"). Rejected: `scheduling_interface`'s role is the behavioral contract (given state, return a decision), not data-type ownership. Conflating the two would make one module responsible for two distinct concerns.
- **Place entities inside `scenario_generator`** (the first module being implemented, and the natural producer of `Scenario` data). Rejected: it would invert the intended dependency direction — `scheduling_interface`, `reference_implementations`, and `benchmark` would all depend on `scenario_generator` just to obtain basic types, even though `docs/architecture.md` explicitly states `scenario_generator` has no knowledge of scheduling algorithms.
- **Let each module define its own local types** for the concepts it needs. Rejected outright — this is precisely the coupling risk `docs/architecture_review.md` and Design Principle 1 of the domain model ("single canonical ownership") exist to prevent.

## Consequences

- A new subpackage `src/radio_scheduler/domain/` is added, containing dataclasses only — no generation, scheduling, or benchmarking logic — consistent with Design Principle 3 of the domain model ("entities are pure data").
- `scenario_generator`, `scheduling_interface`, `reference_implementations`, and `benchmark` all take a dependency on `domain`; `domain` must never import from any of them.
- The next implementation step — translating `domain-model-v0.1.md`'s Core Entities into actual dataclasses — now has a concrete home.
- Future test fixtures and conformance checks (an open item from `docs/architecture_review.md`) will import entity shapes from `domain` as their single source of truth.

## Validation criteria

No module other than `domain` defines its own version of a Core Entity type; `radio_scheduler.domain` has zero imports from `scenario_generator`, `scheduling_interface`, `reference_implementations`, or `benchmark`.

## Related documents

- [`docs/architecture_review.md`](../architecture_review.md) — original identification of the missing Core/domain module.
- [`docs/specification/domain-model-v0.1.md`](../specification/domain-model-v0.1.md) — conceptual definitions this module implements.
- [`ADR-004`](ADR-004-implementation-language-and-tooling.md) — Python/uv foundation this module is built on.
