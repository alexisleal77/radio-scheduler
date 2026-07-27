# ADR-002: Closed-loop simulation with explicit exogenous vs. decision-dependent state

## Status

Accepted

## Date

2026-07-27

## Context

`docs/architecture.md` describes `scenario_generator` as producing scenarios "independent of any algorithm" and having "no knowledge of scheduling algorithms." Taken literally, this means the entire network state trajectory — including buffer occupancy — is pre-generated and identical regardless of which scheduler runs against it, or whether one runs at all.

This breaks down for state that is causally downstream of scheduling decisions. Buffer occupancy at TTI *n* depends on what was actually transmitted at TTI *n-1*, which depends on what the scheduler chose to allocate and whether that transmission succeeded. HARQ retransmission need is the same kind of case: it only exists because a prior transmission was scheduled and failed, or wasn't scheduled at all. If this state is pre-baked independent of scheduling, every algorithm is evaluated against a queue trajectory drained by a hypothetical ideal server, not by the algorithm actually under test — which defeats the purpose of comparing algorithms on congestion, latency, and QoS satisfaction, all of which are stated project goals.

`docs/architecture_review.md` flagged this open-loop/closed-loop ambiguity as the highest-priority unresolved decision, since it drives the shape of `scheduling_interface` and determines whether a simulation loop module is required.

## Decision

Radio Scheduler uses **closed-loop simulation**. Network state is split into two categories:

- **Exogenous state** — generated entirely upfront by `scenario_generator`, independent of any scheduler and identical across all algorithms evaluated against a given scenario:
  - Channel quality / CQI per UE per TTI
  - UE mobility
  - Packet arrival process / traffic demand (new bytes entering each UE's buffer per TTI)
  - Available resource blocks per TTI
  - QoS class per UE

- **Decision-dependent state** — computed incrementally, TTI by TTI, as a function of the scheduler's allocation decision and the exogenous state for that TTI. This state is *not* produced by `scenario_generator` and is not identical across algorithms:
  - Buffer occupancy (previous occupancy + new arrivals − what was successfully transmitted, per the scheduler's decision and the transmission outcome)
  - HARQ retransmission state (a retransmission is needed when a transmission was scheduled and failed, or was due but not scheduled)

Producing decision-dependent state requires a component that steps through TTIs, feeds exogenous state plus the current decision-dependent state to the scheduler via `scheduling_interface`, applies the returned allocation to update buffer/HARQ state, and hands off the result to `benchmark`/`tests`. This is the "simulation loop," a module gap already identified in `docs/architecture_review.md`. This ADR establishes that such a module is required; it does not assign its ownership or design its interface — that is a separate, follow-up decision.

## Alternatives considered

- **Open-loop simulation** (full network state, including buffer occupancy, pre-generated independent of any scheduler) — simpler to implement, trivially parallelizable, and scenario files are byte-for-byte reproducible on their own with no simulation loop required. Rejected because it cannot produce realistic congestion, buffer overflow, or latency dynamics caused by a scheduler's own choices, which are exactly the properties `benchmark` needs to measure to compare scheduling performance meaningfully.

## Consequences

- `scenario_generator`'s responsibility narrows: it produces only exogenous state, not the full network state trajectory. `docs/architecture.md` needs to be updated to reflect this split (out of scope for this ADR).
- A new module — the simulation loop — is now required. No existing module owns it yet; assigning ownership (likely paired with the domain-model ownership question) is the next decision to make, per the order of resolution in `docs/architecture_review.md`.
- The same scenario, replayed against two different schedulers, will legitimately produce different buffer/HARQ trajectories. Reproducibility is preserved at the level of exogenous state (fixed/seeded) and the state-transition rule (deterministic given the prior state and the decision) — not at the level of the buffer trajectory itself, which is expected to vary by algorithm and is precisely what is being measured.
- `tests/` fixtures for buffer-dependent behavior must account for the fact that expected buffer state is a function of both the scenario and the scheduler under test, not the scenario alone.
- `scheduling_interface` must account for scheduler statefulness across TTIs (e.g. Proportional Fair's running throughput average, Round Robin's last-served UE) since the interface is now invoked repeatedly within a stepped loop rather than once against a fully materialized scenario. This ADR does not resolve that statefulness question — it remains open, per `docs/architecture_review.md`.

## Validation criteria

- Two different scheduling algorithms run against the same scenario produce identical exogenous-state values (CQI, arrivals, mobility, resource blocks, QoS class) at every TTI, and diverging buffer/HARQ trajectories where their allocation decisions diverge.
- Re-running the same algorithm against the same scenario (same seed) produces an identical decision-dependent state trajectory, confirming the state-transition rule is deterministic.
- `scenario_generator`'s output contains no buffer occupancy or HARQ fields — only exogenous state — once the module is implemented.

## Related documents

- [`docs/architecture.md`](../architecture.md) — `scenario_generator` and `scheduling_interface` responsibilities (to be updated to reflect the exogenous/decision-dependent split).
- [`docs/architecture_review.md`](../architecture_review.md) — original identification of the open-loop/closed-loop ambiguity and the missing simulation loop module.
- [`ADR-001`](ADR-001-json-as-scenario-format.md) — canonical format for scenario data; exogenous-state fields defined here are what `scenario_generator` will serialize under that format.
