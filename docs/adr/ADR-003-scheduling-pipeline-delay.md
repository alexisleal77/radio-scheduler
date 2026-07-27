# ADR-003: Configurable scheduling pipeline delay in the Simulation Loop

## Status

Accepted

## Date

2026-07-27

## Context

ADR-002 established closed-loop simulation and split network state into exogenous state (produced by `scenario_generator`) and decision-dependent state (buffer occupancy, HARQ), updated by the Simulation Loop based on the scheduler's decisions. It left open exactly *when*, relative to the TTI a decision was computed for, that decision is applied to update decision-dependent state.

Two orderings were considered:

- **Immediate application**: the decision computed for TTI *n* is applied (transmission executed, buffer/HARQ updated) within *n* itself. The scheduler never observes a state that omits the effect of its own most recent decision.
- **Delayed application**: the decision computed for TTI *n* is applied only at TTI *n+1* (or later). The scheduler always observes decision-dependent state that lags its own most recent decision by some number of TTIs.

To decide between them, we checked whether either ordering matches how real 3GPP-based systems and their simulators are structured, since Radio Scheduler aims for scheduling algorithms and results that are conceptually comparable to real deployments:

- **3GPP NR spec**: scheduling decisions and their execution are explicitly separated by slot-offset parameters — K0 (DCI-to-PDSCH offset), K2 (DCI-to-PUSCH offset, which is *never* zero — a UL grant can never be executed in the same slot it was issued), and K1 (PDSCH-to-HARQ-feedback offset). This is a spec-level pipeline, not an implementation detail of any one tool.
- **ns-3 NR module**: implements a `MacToChannelDelay` attribute (default 2 slots) — the MAC/scheduler deliberately works ahead of the PHY to model real processing latency between a decision and its execution.
- **srsRAN**: the low-PHY processes downlink samples several slots ahead of actual transmission (~3-slot offset), and preserves the classic LTE n+4 HARQ feedback timing.
- **OpenAirInterface**: implements the same K0/K2-based grant-to-transmission offsets natively through its FAPI MAC-PHY interface (DL_TTI.request / UL_DCI.request precede the corresponding transmission by the specified offset).

In all three tools, the offset is a *configurable parameter*, not a hardcoded constant — real deployments and their simulators vary K0/K1/K2 and equivalent delays depending on processing capability and use case.

## Decision

The Simulation Loop applies a scheduler's decision for TTI *n* to decision-dependent state (buffer/HARQ update, transmission execution) after a **configurable pipeline delay of `d` TTIs**, defaulting to **`d = 1`**.

This is an architectural abstraction of the real-system decision/execution split (K0/K1/K2 and their simulator equivalents), not a hardcoded implementation detail. `d` is a parameter of the Simulation Loop, not a fixed constant baked into its control flow — `d = 0` (immediate application) remains a valid, supported configuration, and `d > 1` is not excluded.

## Alternatives considered

- **Immediate application only (`d` fixed at 0)** — simplest to reason about and implement, and the scheduler always acts on fully current state. Rejected as the sole/default behavior because it has no counterpart in real 3GPP-based systems or their simulators, all of which separate decision from execution by at least one processing step; using it as the only option would make Radio Scheduler results structurally incomparable to real or realistically-simulated systems.
- **Fixed delay hardcoded at exactly 1 TTI** — matches the common default case (e.g., ns-3's default 2-slot delay is close in spirit, srsRAN's ~3-slot offset, LTE's n+4 HARQ timing) but forecloses studying how algorithms behave as the delay grows, which real systems show varies with processing capability. Rejected in favor of a configurable parameter with `d = 1` only as the *default*, preserving the ability to study delay sensitivity as a research question later.

## Consequences

- The Simulation Loop must buffer at least `d` TTIs' worth of pending decisions (computed but not yet applied) rather than applying a decision's effects synchronously within the same step it was produced.
- The scheduler statefulness/lifecycle question (still open per ADR-002) must now account for the fact that a scheduler deciding for TTI *n* will not observe the outcome of that decision until TTI *n+d* — any internal running state the scheduler keeps (e.g. Proportional Fair's throughput average) needs to be updated based on what it decided, not on an outcome it cannot yet see.
- `d` becomes a first-class scenario/run parameter alongside the scenario itself: two runs with the same scenario and scheduler but different `d` are expected to produce different decision-dependent trajectories, and comparisons between algorithms must hold `d` fixed to be meaningful.
- This opens a new research axis explicitly supported by the framework: measuring how robust a scheduling algorithm is to increasing pipeline delay, which mirrors a real, practically relevant question in 5G/6G scheduler design.
- `d = 0` remains available as a simplification for early development, debugging, and simple correctness tests, without requiring a separate code path — it is just the degenerate case of the same mechanism.

## Validation criteria

- With `d = 0`, the Simulation Loop's behavior is identical to the immediate-application ordering (decision for *n* is fully reflected in state by the end of *n*).
- With the default `d = 1`, decision-dependent state observed by the scheduler at TTI *n+1* reflects the decision computed at TTI *n*, and not the decision computed at *n+1* itself — matching the delayed-application timeline discussed for this decision.
- Changing `d` requires no change to the `scheduling_interface` contract itself — only to the Simulation Loop's internal buffering — confirming that pipeline delay is a Simulation Loop concern, not a scheduler-facing one.

## Related documents

- [`ADR-002`](ADR-002-closed-loop-simulation.md) — closed-loop simulation and the exogenous/decision-dependent state split this decision builds on.
- [`docs/architecture_review.md`](../architecture_review.md) — original identification of the missing Simulation Loop module and the open scheduler-statefulness question this ADR interacts with.
