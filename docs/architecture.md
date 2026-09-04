# Architecture

This document describes the conceptual architecture of Radio Scheduler. The implementation language is Python (ADR-004); this document remains conceptual — concrete type/interface definitions live in the code and in each module's own README, not here.

## Design principles

- **Separation of concerns.** Scenario generation, scheduling logic, and benchmarking/testing are three independent concerns that live in three independent modules. None of them should need to know the internals of the others.
- **One shared contract.** Every scheduling algorithm — reference or AI-generated — implements the same `scheduling_interface`. That interface is the *only* thing `scenario_generator` and `reference_implementations`/`benchmark` have in common. This is what makes algorithms interchangeable and directly comparable under identical conditions.
- **Reproducibility.** A scenario is data, not code tied to a particular scheduler. The same scenario must be replayable against any number of algorithms and produce comparable, deterministic results.
- **Extensibility over modification.** Adding a new algorithm means adding a new module under `reference_implementations/` that implements `scheduling_interface` — it never requires changing `scenario_generator`, `benchmark`, or other algorithms. The same goes for adding a new scenario type.

## Module responsibilities

### `domain`
Canonical shared entities every other module depends on — UE, Resource Block, Scenario, Allocation Decision, QoS Class, and the rest of the model in `docs/specification/domain-model-v0.1.md`. No component may reinvent or extend these shapes locally; `domain` has no dependency on any other module.

### `scenario_generator`
Produces scheduling scenarios: network states over time (UEs, channel quality/CQI, buffer/traffic demand, available resource blocks, QoS class, etc.) that scheduling algorithms are evaluated against. This module has no knowledge of scheduling algorithms — it only produces data.

### `scheduling_interface`
Defines the contract every scheduler must implement: given the current network/scenario state, return a resource allocation decision. This is the seam of the whole system — the only module both `scenario_generator`-produced data and `reference_implementations` code are built against.

### `reference_implementations`
Concrete schedulers implementing `scheduling_interface`: Round Robin, Proportional Fair, MaxCQI, and eventually AI-generated algorithms. These serve both as usable baselines and as worked examples for anyone (human or AI) implementing a new algorithm.

### `simulation_loop`
Runs a `scheduling_interface` implementation against a `scenario_generator`-produced Scenario, TTI by TTI: applies each TTI's exogenous state, tracks the decision-dependent state produced by the algorithm's own allocation decisions, and produces the resulting sequence of Allocation Decisions. This is the module that actually exercises `reference_implementations` output against scenario data — `benchmark` and `tests` build on it rather than reimplementing this loop themselves.

### `benchmark`
Runs one or more schedulers against one or more scenarios and measures their **computational cost**: wall-clock time, CPU time, and peak Python-allocator-traced memory (ADR-010). Scheduling-performance metrics — throughput, fairness, latency/QoS satisfaction — remain out of scope for v0.1, deferred as a single atomic unit until a CQI-to-rate/capacity model exists in `domain`.

Benchmarking is about *comparing* algorithms, not verifying correctness.

### `tests`
Functional tests that check schedulers and scenario generators against expected outputs for fixed, deterministic scenarios. This is about *correctness*, not performance — a separate concern from `benchmark`.

### `scripts`
Operational entry points (running a benchmark suite, generating a report, regenerating a scenario set, etc.). Scripts are thin wrappers around `src/` — they should not contain scheduling or benchmarking logic themselves.

## Data flow

```
scenario_generator
      │  produces scenario data (network state over time)
      ▼
simulation_loop                       (runs a scheduling_interface
      │  implementation — one of reference_implementations/* — TTI by
      │  TTI, producing allocation decisions)
      ▼
benchmark
      │  measures computational cost (wall-clock time, CPU time, peak
      │  traced Python memory) — scheduling-performance metrics
      │  deferred (ADR-010)
      ▼
computational cost measurements

tests consume the same scenario_generator + scheduling_interface +
simulation_loop seam, but assert decisions against known-correct
expected output instead of measuring cost.
```

`scenario_generator` and `reference_implementations` never call each other directly; everything crosses through `scheduling_interface`.

## Status

Architecture and module boundaries are defined. The implementation language is Python (ADR-004). `domain` is implemented as the canonical shared entities (ADR-005). `scenario_generator` and `scheduling_interface` are implemented. `reference_implementations` has three algorithms implemented — Round Robin, Proportional Fair, and MaxCQI. `simulation_loop` v0.1 is implemented (ADR-009). `benchmark` v0.1 is implemented (ADR-010), scoped to computational cost only — scheduling-performance metrics remain deferred. `scripts` is not yet implemented.

Architecturally significant decisions, once made, are recorded as ADRs in [`docs/adr/`](adr/).
