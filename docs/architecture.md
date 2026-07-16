# Architecture

This document describes the conceptual architecture of Radio Scheduler. It is intentionally language-agnostic — the implementation language has not been chosen yet. Once it is, this document should be extended (not replaced) with concrete type/interface definitions.

## Design principles

- **Separation of concerns.** Scenario generation, scheduling logic, and benchmarking/testing are three independent concerns that live in three independent modules. None of them should need to know the internals of the others.
- **One shared contract.** Every scheduling algorithm — reference or AI-generated — implements the same `scheduling_interface`. That interface is the *only* thing `scenario_generator` and `reference_implementations`/`benchmark` have in common. This is what makes algorithms interchangeable and directly comparable under identical conditions.
- **Reproducibility.** A scenario is data, not code tied to a particular scheduler. The same scenario must be replayable against any number of algorithms and produce comparable, deterministic results.
- **Extensibility over modification.** Adding a new algorithm means adding a new module under `reference_implementations/` that implements `scheduling_interface` — it never requires changing `scenario_generator`, `benchmark`, or other algorithms. The same goes for adding a new scenario type.

## Module responsibilities

### `scenario_generator`
Produces scheduling scenarios: network states over time (UEs, channel quality/CQI, buffer/traffic demand, available resource blocks, QoS class, etc.) that scheduling algorithms are evaluated against. This module has no knowledge of scheduling algorithms — it only produces data.

### `scheduling_interface`
Defines the contract every scheduler must implement: given the current network/scenario state, return a resource allocation decision. This is the seam of the whole system — the only module both `scenario_generator`-produced data and `reference_implementations` code are built against.

### `reference_implementations`
Concrete schedulers implementing `scheduling_interface`: Round Robin, Proportional Fair, MaxCQI, and eventually AI-generated algorithms. These serve both as usable baselines and as worked examples for anyone (human or AI) implementing a new algorithm.

### `benchmark`
Runs one or more schedulers against one or more scenarios and records two categories of results:
- **Scheduling performance**: throughput, fairness, latency/QoS satisfaction, etc.
- **System cost**: execution time, CPU, memory, and scalability as the number of UEs/resource blocks grows.

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
scheduling_interface implementation   (one of reference_implementations/*)
      │  produces allocation decisions
      ▼
benchmark  ──────────────┐
      │ measures          │
      ▼                   ▼
performance metrics   system metrics (time/CPU/memory/scalability)

tests consume the same scenario_generator + scheduling_interface seam,
but assert decisions against known-correct expected output instead of
measuring cost.
```

`scenario_generator` and `reference_implementations` never call each other directly; everything crosses through `scheduling_interface`.

## Status

Architecture and module boundaries are defined. Implementation language, concrete data formats, and the exact `scheduling_interface` contract are not yet decided — that is the next step.

Architecturally significant decisions, once made, are recorded as ADRs in [`docs/adr/`](adr/).
