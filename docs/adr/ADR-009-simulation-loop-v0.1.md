# ADR-009: Simulation Loop v0.1 — module ownership, buffer state-transition rule, and pipeline delay scope

## Status

Accepted

## Date

2026-08-19

## Context

ADR-002 established closed-loop simulation and named the "simulation loop" as a required module: something that steps through TTIs, feeds exogenous plus decision-dependent state to a scheduler via `scheduling_interface`, applies the returned `AllocationDecision` values to update `Buffer`/`HARQState`, and hands off the result. It explicitly deferred that module's ownership and design. ADR-003 built on this by defining a configurable pipeline delay `d` (default 1) between when a decision is computed and when its effect is applied, but likewise left the Simulation Loop's concrete design for a follow-up step.

With `scenario_generator`, `scheduling_interface`, and three `reference_implementations` (Round Robin, Proportional Fair, MaxCQI) now implemented, this module is the remaining structural gap preventing any of them from being run end-to-end against a `Scenario`. Designing it surfaces two questions neither ADR-002 nor ADR-003 resolved:

1. **What does "successfully transmitted" mean**, concretely, for updating `Buffer` occupancy? ADR-002's formula ("previous occupancy + new arrivals − what was successfully transmitted") presupposes a rule for converting an `AllocationDecision` into bytes transmitted. No such rule exists anywhere in the domain model: `AllocationDecision` carries only `resource_block_ids`, `ResourceBlock` carries no capacity field, and `ChannelQuality.cqi` is deliberately just an ordinal index with no CQI-to-rate conversion (ADR-006, `Related documents`). Inventing a capacity/rate model now would require deciding an MCS table or an arbitrary bytes-per-Resource-Block constant — a modeling commitment with no current consumer (no reference implementation or test needs a byte-accurate throughput figure yet) and directly against `docs/specification/domain-model-v0.1.md`'s Design Principle 5 ("minimal and additive vocabulary").
2. **What does pipeline delay `d` mean operationally** inside a single-pass, per-TTI step loop? ADR-003 describes `d=0` as "the decision computed for TTI *n* is applied within *n* itself... the scheduler never observes a state that omits the effect of its own most recent decision," and `d≥1` as observing decision-dependent state that lags by `d` TTIs. For `d≥1`, applying this literally requires a loop to hold a queue of decisions whose effects are pending — a "service pending" mechanism not yet designed. For `d=0`, no queue is needed: causally, a scheduler can never observe the outcome of a decision it has not yet made, so the only synchronously realizable reading of "applied within *n* itself" is that the decision's effect is reflected in `Buffer` state *after* `allocate()` returns for TTI *n*, but *before* TTI *n+1* begins.

## Decision

**Simulation Loop v0.1 lives in a new top-level module, `src/radio_scheduler/simulation_loop/`.** It exposes a single free function, `run(scenario, algorithm, pipeline_delay=0) -> SimulationResult[StateT]` — not a stateful class — consistent with this project's established preference for explicit, non-hidden state (ADR-007, ADR-008).

1. **Buffer state-transition rule (v0.1): binary, capacity-free drain.** A UE that receives at least one Resource Block in a TTI (i.e., appears in that TTI's validated `AllocationDecision` set with a non-empty `resource_block_ids`) has its entire current-TTI `Buffer.occupancy_bytes` — after that TTI's arrival is applied — drained to exactly `0`. A UE that receives no Resource Block that TTI carries its full backlog forward unchanged (plus the next TTI's arrival). This is deliberately not a claim about real transmission capacity: it is the simplest rule that lets `Buffer` be genuinely decision-dependent (closing the loop per ADR-002) without inventing a CQI-to-rate or bytes-per-Resource-Block model that nothing in this project currently consumes.

2. **`HARQState` is not populated in v0.1.** Every TTI's `ObservableState.harq_states` is `()`. `HARQState.retransmission_pending` (ADR-006) can only be non-trivially derived from a transmission-failure model, which does not exist (point 1). None of the three existing `reference_implementations` (Round Robin, Proportional Fair, MaxCQI) read `observable_state.harq_states`, so there is no current consumer to serve even a placeholder value for.

3. **v0.1 supports only `pipeline_delay=0`.** `run()` raises `ValueError` for any other value, before processing any TTI. Under `d=0`, a TTI *n* is processed as: apply *n*'s arrivals → build `ObservableState` (pre-decision) → call `allocate()` exactly once → validate the returned decisions → drain to `0` the `Buffer` of every UE the (validated) decisions served → move to TTI *n+1*. No queue of pending decisions is needed or built, because the decision computed for *n* is fully applied before *n* ends.

4. **`pipeline_delay ≥ 1` is out of scope for v0.1**, not silently unsupported. Supporting it requires a "service pending" mechanism — a delay queue holding computed-but-not-yet-applied decisions, drained `d` TTIs after they were computed — that has not been designed. This is named explicitly here as future work, not left as an unstated gap.

## Alternatives considered

- **Invent a bytes-per-Resource-Block or CQI-to-MCS capacity model now**, so `Buffer` could reflect a more realistic transmitted-bytes figure. Rejected for v0.1: no reference implementation, test, or benchmark currently needs a byte-accurate throughput number: `Buffer` is only read today by RR/PF/MaxCQI's eligibility checks (`occupancy_bytes > 0`), which the binary drain rule already satisfies exactly. Adding a capacity model now would be exactly the kind of "abstraction without an immediate consumer" this project's incremental principle (`CLAUDE.md`) warns against, and would preempt a modeling decision (MCS table, spectral efficiency) that deserves its own dedicated ADR when something actually needs it (flagged as future debt during Proportional Fair's design already).
- **Support `pipeline_delay ≥ 1` now via a decision queue.** Rejected for v0.1: doable, but the resulting scheduler-observation timeline (`Buffer` at *n* reflecting the decision computed at *n-d*) has already been implemented once, incorrectly conflated with `d=0`'s causally-impossible literal reading, and reverted before any code was written. Re-attempting it correctly is a well-scoped follow-up once `d=0` is proven working end-to-end against all three reference implementations.
- **Populate `HARQState` with a placeholder derived from `occupancy_bytes > 0`** (i.e., "retransmission pending" whenever backlog remains). Rejected: this would be redundant with `Buffer` under the current no-failure model (never diverges from it), misleadingly implies a real HARQ signal exists, and has no reader today.
- **Model the Simulation Loop as a stateful class** (e.g., with a `.step()` method advancing one TTI per call, mutable instance attributes for accumulated decisions). Rejected: conflicts with the explicit-state precedent already set by `scenario_generator` (ADR-007) and `scheduling_interface` (ADR-008); a free function taking and returning immutable values keeps the same testability and no-hidden-state properties.

## Consequences

- `Buffer` trajectories produced by v0.1's Simulation Loop are not physically realistic (a UE with any Resource Block always fully drains, regardless of how much data it had or how good its channel was) — acceptable for v0.1 because nothing downstream currently measures realism, but this must be revisited before `benchmark`'s `throughput_bps`/`SchedulingPerformanceMetric` can be computed meaningfully.
- Comparing two algorithms' `Buffer` trajectories under v0.1 does not yet mean what it will once a capacity model exists — a run just reflects "was this UE ever selected," not "how much data actually moved."
- `pipeline_delay` remains a parameter of `run()` (mirroring `domain.Run.pipeline_delay`, default `1`) but v0.1 only accepts `0` — the mismatch between `Run`'s domain default (`1`) and the Simulation Loop's only supported value (`0`) is a known, temporary inconsistency until `d≥1` is implemented; it is not resolved by this ADR.
- Any future ADR introducing a capacity/rate model or a pending-decision queue for `d≥1` extends this one additively; it does not need to reverse the binary drain rule for existing `d=0` runs, since that rule remains the correct behavior for the `d=0` case specifically.
- `simulation_loop` becomes the fourth module (after `domain`, `scenario_generator`, `scheduling_interface`) that `reference_implementations` output can be exercised through end-to-end; `benchmark` and `tests` can now be built against a real run, not just single-TTI unit calls.

## Validation criteria

- `run(scenario, algorithm, pipeline_delay=0)` calls `algorithm.initial_state()` exactly once, and `algorithm.allocate()` exactly once per TTI in `scenario.ttis`, in ascending `index` order.
- For any TTI where a UE is served (appears in a validated decision with a non-empty `resource_block_ids`), that UE's `Buffer.occupancy_bytes` as visible to the *next* TTI's `ObservableState` is exactly that next TTI's own arrival (i.e., `0` plus the new arrival) — never carrying forward the drained amount.
- `run(scenario, algorithm, pipeline_delay=1)` (or any value other than `0`) raises `ValueError` before any TTI is processed.
- `ObservableState.harq_states == ()` for every TTI produced by `run()`.
- Running the same `Scenario` through Round Robin, Proportional Fair, and MaxCQI via `run()` succeeds for all three without modification to `simulation_loop`, confirming genericity over `StateT`.

## Related documents

- [`ADR-002`](ADR-002-closed-loop-simulation.md) — closed-loop simulation and the exogenous/decision-dependent state split this ADR's Buffer rule implements a concrete instance of.
- [`ADR-003`](ADR-003-scheduling-pipeline-delay.md) — pipeline delay `d`; this ADR narrows v0.1's supported range to `d=0` and explains why, without altering ADR-003's own decision that `d` should eventually be configurable.
- [`ADR-006`](ADR-006-entity-representation-conventions.md) — CQI-as-index convention (no rate/capacity field) that this ADR's binary drain rule deliberately works around rather than extends.
- [`ADR-007`](ADR-007-scenario-generator-reproducibility-contract.md) — precedent for explicit, local, non-global state, extended here to the Simulation Loop's own design (free function, no hidden state).
- [`ADR-008`](ADR-008-scheduler-statefulness.md) — `SchedulingAlgorithm` contract this module's `run()` drives; the Simulation Loop is the "something" ADR-008 point 8 assigns responsibility to for providing `ObservableState`, threading `SchedulerState`, and applying decisions.
- [`docs/specification/domain-model-v0.1.md`](../specification/domain-model-v0.1.md) — Design Principle 5 (minimal and additive vocabulary), the basis for deferring a capacity/rate model.
