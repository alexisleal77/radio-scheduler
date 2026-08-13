# ADR-008: Scheduler statefulness — explicit, threaded state instead of stateful objects

## Status

Accepted

## Date

2026-08-13

## Context

`docs/architecture.md` describes `scheduling_interface` only at a high level: "given the current network/scenario state, return a resource allocation decision." `docs/architecture_review.md` flagged the concrete shape of that contract as an unresolved architectural question from the start: "Scheduler statefulness and lifecycle: is a `scheduling_interface` implementation a stateful object with a lifecycle (e.g., reset between runs, step per TTI), or a pure function with externally carried state?" It was never resolved, and was skipped over when work moved to language selection and the domain model. It cannot be deferred further: implementing `scheduling_interface` requires deciding it, since it determines the interface's very shape (class vs. function, what each call receives and returns).

The question is forced by algorithm reality: Round Robin must remember which UE it served last; Proportional Fair must maintain a running average of each UE's achieved throughput; MaxCQI may need no memory at all. Something has to carry this memory across TTIs, and where/how it is carried is exactly what this ADR decides. Per `docs/adr/README.md`, scheduler statefulness is named explicitly as an example decision warranting an ADR.

## Decision

A scheduler is a **step function with explicit, externally threaded internal state** — not a stateful object with hidden mutable attributes.

1. **No hidden mutable state between calls.** A scheduler implementation holds no state of its own between invocations. Every value it needs to remember from one TTI to the next is passed in and handed back out explicitly.

2. **Each step receives, separately:**
   - the current **observable state** of the network (`ObservableState` — exact shape deferred, see "Out of scope" below);
   - the algorithm's **previous internal state** (`SchedulerState` — exact shape deferred; algorithm-specific).

3. **Each step returns, separately:**
   - zero or more `AllocationDecision` values for the current TTI;
   - the algorithm's **new internal state**, to be threaded into the next call.

4. **Internal state is explicit because different algorithms have different memories.** Round Robin needs the position or identity of the last-served UE. Proportional Fair needs a running history or average of per-UE throughput. MaxCQI may need no historical memory at all — an empty state is a first-class, valid case (see point 12 below), not a special-cased exception to the contract.

5. **Algorithm-specific internal state is never folded into the shared domain entities.** `SchedulerState` for a given algorithm stays local to that algorithm's own implementation in `reference_implementations`; it is not added as fields on `UE`, `Scenario`, or any other entity in `radio_scheduler.domain`.

6. **`ObservableState` contains only what the scheduler may legitimately see at the current TTI:** the exogenous state for that TTI (per ADR-002) and whatever decision-dependent state (Buffer, HARQ) is visible under the pipeline delay `d` (per ADR-003) — nothing from future TTIs, and no final scheduling-performance metrics (those belong to `benchmark`/`SchedulingPerformanceMetric`, computed after the fact, never fed back into a scheduling decision).

7. **The contract allows multiple `AllocationDecision` values per TTI**, because a TTI's Resource Blocks are typically distributed across more than one UE. This requires no change to the `AllocationDecision` entity (ADR-006) — it is already shaped as one decision per UE; a TTI's full allocation is simply the set of `AllocationDecision` values returned together.

8. **The Simulation Loop — not the scheduler — is responsible for:** providing `ObservableState` each TTI; loading the scheduler's previous `SchedulerState`; invoking the scheduler; retaining the returned `SchedulerState` for the next TTI; and applying the returned `AllocationDecision` values to update `Buffer` and `HARQState` (per ADR-002).

9. **`scheduling_interface` must not:** generate scenarios (that is `scenario_generator`'s responsibility); mutate any global simulation state; compute scheduling-performance metrics (that is `benchmark`'s responsibility); control the pipeline delay `d` (that is the Simulation Loop's responsibility, per ADR-003); or access any TTI other than the current one.

10. **Explicit state is deliberately chosen for what it enables**, beyond stylistic preference: isolated unit testing of a single step without constructing or resetting an object; exact reproduction of a run from a recorded state trace; inspection of state transitions between TTIs; checkpointing mid-run; and — most importantly for this project's stated goal of admitting AI-generated algorithms — straightforward conformance validation, since a step becomes a pure input/output equality check rather than requiring reasoning about an object's mutable internals or lifecycle.

11. **The future Python interface will express `SchedulerState` generically** (e.g. via a type parameter), so each algorithm can declare its own concrete state type, instead of the contract falling back to a generic `dict`, `Any`, or one universal class carrying optional fields for every algorithm's needs.

12. **An empty/trivial state is explicitly supported** for algorithms with no historical memory (e.g. MaxCQI): such an algorithm still receives and returns a `SchedulerState` value each call, for contract uniformity — it is simply a trivial one, not an algorithm-specific exception to the step signature.

## Out of scope for this ADR

The concrete Python types and method/function signature — the exact shape of `ObservableState` and `SchedulerState`, their field names, whether they are dataclasses or another construct, and where they live in the module tree — are **not** decided here. These are reversible, local implementation details, to be settled in a subsequent, smaller step, consistent with how ADR-007 deferred `ScenarioGeneratorConfig`'s concrete field list.

## Alternatives considered

- **Stateful scheduler object** (mutable instance attributes, e.g. `scheduler.allocate(observable_state) -> AllocationDecision`, with lifecycle "one instance per Run"). Matches how real systems are commonly built (e.g. persistent MAC scheduler classes in ns-3/OAI). Rejected: conflicts with this project's already-established preference for no hidden state (ADR-007's local, explicitly-threaded RNG; Design Principle 4 of the domain model), and complicates the future conformance/validation test suite flagged in `docs/architecture_review.md` — testing a step would require managing an object's lifecycle and mutable internals instead of a pure input/output check.
- **Global or shared state** (e.g. a module-level dict of per-UE running averages). Rejected outright: the same class of risk ADR-007 explicitly rejected for pseudo-randomness — hidden shared state risks silent cross-Run or cross-algorithm contamination, and breaks the traceability Design Principle 4 requires.
- **Fold every algorithm's state into the shared domain entities** (e.g. add a `running_throughput` field to `UE`). Rejected: violates Design Principle 2 ("entities represent domain concepts, not implementation artifacts") — a Proportional-Fair-specific running average is not a concept a domain expert would recognize as belonging to a UE in general — and reintroduces exactly the coupling ADR-005 was created to prevent, since every new algorithm would be tempted to add its own fields to shared entities.
- **Return only one `AllocationDecision` per TTI.** Rejected: does not match physical reality, where a TTI's Resource Blocks are normally split across multiple UEs; `AllocationDecision`'s existing one-decision-per-UE shape (ADR-006) already anticipates multiple decisions per TTI, so restricting to one would either force an unrealistic single-UE-gets-everything allocation or require redesigning an already-accepted entity for no benefit.
- **Use `dict` or `Any` as a universal state type.** Rejected: defeats static typing and self-documentation of what an algorithm's state actually contains, makes malformed state indistinguishable from valid state without runtime inspection, and works against this project's consistent use of explicit, typed structures (frozen dataclasses) everywhere else in the domain model.

## Consequences

- The Simulation Loop (still without an assigned module home) must be designed to thread `SchedulerState` across its per-TTI loop, in addition to its already-decided responsibilities (applying decisions, updating Buffer/HARQState, respecting the pipeline delay). This adds a concrete requirement to that module's future design.
- Every future `reference_implementations` algorithm defines its own `SchedulerState` type; there is no shared "scheduler state" entity to extend, by design.
- Unit tests for a scheduling algorithm can call its step function directly with a hand-constructed `ObservableState` and `SchedulerState`, asserting the returned decisions and new state — no object setup/teardown required.
- A future conformance/validation suite for human- or AI-generated algorithms (a gap named in `docs/architecture_review.md`) can be built as input/output checks against the step function, without needing to reason about mutable object lifecycles.
- The concrete types (`ObservableState`, `SchedulerState`, the exact function/generic signature) remain to be designed in a follow-up step; this ADR constrains that design but does not complete it.

## Validation criteria

- No `reference_implementations` algorithm stores state as an instance attribute mutated in place between step calls; all cross-TTI memory is passed in and returned explicitly.
- Calling a scheduler's step function twice with identical `(ObservableState, SchedulerState)` inputs produces identical `(AllocationDecision, ...)` and new-state outputs.
- No field specific to one scheduling algorithm exists on any entity in `radio_scheduler.domain`.
- A TTI where more than one UE receives Resource Blocks is representable as multiple `AllocationDecision` values returned from a single step call.

## Related documents

- [`docs/architecture_review.md`](../architecture_review.md) — original statement of the unresolved scheduler statefulness question this ADR resolves.
- [`docs/adr/README.md`](README.md) — names scheduler statefulness as a canonical example warranting an ADR.
- [`ADR-002`](ADR-002-closed-loop-simulation.md) — exogenous vs. decision-dependent state split that shapes `ObservableState`; Simulation Loop ownership of Buffer/HARQState updates.
- [`ADR-003`](ADR-003-scheduling-pipeline-delay.md) — pipeline delay `d` as a Simulation Loop concern, not exposed to `scheduling_interface`.
- [`ADR-005`](ADR-005-domain-module.md) — single canonical ownership of shared entities, which algorithm-specific state must not violate.
- [`ADR-006`](ADR-006-entity-representation-conventions.md) — `AllocationDecision`'s existing one-decision-per-UE shape, reused as-is for multi-UE TTIs.
- [`ADR-007`](ADR-007-scenario-generator-reproducibility-contract.md) — precedent for explicit, non-global, non-hidden state, extended here to scheduler state by this module's own choice (not mandated by ADR-007).
- [`docs/specification/domain-model-v0.1.md`](../specification/domain-model-v0.1.md) — Design Principles 2, 4, and 5 that motivate rejecting the alternatives above.
