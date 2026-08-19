# Radio Scheduler

A modular environment for developing, testing, benchmarking, and comparing radio scheduling algorithms for 5G/6G networks.

## Goals

- Build a reusable architecture for radio schedulers.
- Separate scenario generation from scheduling algorithms.
- Allow multiple algorithms to implement the same scheduling interface.
- Support reference implementations such as Round Robin, Proportional Fair, and MaxCQI.
- Support future AI-generated scheduling algorithms.
- Execute functional tests with expected outputs.
- Execute benchmarks measuring execution time, CPU, memory, scalability, and scheduling performance.
- Keep the architecture modular, maintainable, and extensible.

## Repository structure

```
docs/                                  Design and architecture documentation
  adr/                                  Architecture Decision Records (ADR-001..ADR-006)
  specification/domain-model-v0.1.md    Canonical domain model
src/radio_scheduler/                   Python package (ADR-004, ADR-005)
  domain/                               Shared entities — implemented
  scenario_generator/                   Generates TTIs, UEs (QoS by round-robin), Resource Blocks, CQI, and traffic arrivals — implemented (v0.1)
  scheduling_interface/                 The shared contract every scheduling algorithm implements — implemented (v0.1)
  reference_implementations/            Round Robin, Proportional Fair, MaxCQI — implemented (v0.1); future algorithms — not yet implemented
  benchmark/                            Measures execution time, CPU, memory, scalability, and performance — not yet implemented
tests/                                  Functional tests with expected outputs — implemented for scenario_generator, scheduling_interface, Round Robin, Proportional Fair, and MaxCQI
scripts/                                Operational entry points (run benchmarks, generate reports, etc.) — not yet implemented
```

See [`docs/architecture.md`](docs/architecture.md) for the full architecture, including module responsibilities and data flow. Architecturally significant decisions are recorded in [`docs/adr/`](docs/adr/).

## Status

The implementation language is Python (ADR-004). The initial architecture — module boundaries, data flow, and the closed-loop simulation model — is defined, and all architecturally significant decisions are documented as ADRs in [`docs/adr/`](docs/adr/). The domain model ([`docs/specification/domain-model-v0.1.md`](docs/specification/domain-model-v0.1.md)) is implemented as 13 immutable entities in `radio_scheduler.domain`; the `Scenario → Run → AllocationDecision → SchedulingPerformanceMetric` composition has been verified.

`scenario_generator` v0.1 is implemented: given a `ScenarioGeneratorConfig` and a seed, it deterministically produces a `Scenario` — TTIs, UEs with QoS Class assigned by round-robin, Resource Blocks, Channel Quality (CQI), and Traffic Arrivals. Generation is reproducible for a given configuration and seed, per the contract in [`ADR-007`](docs/adr/ADR-007-scenario-generator-reproducibility-contract.md).

`scheduling_interface` v0.1 is implemented: `ObservableState` defines exactly what a scheduling algorithm may observe at one TTI — the current TTI, eligible UEs, available Resource Blocks, Channel Quality, and Buffer/HARQ state (Buffer already reflects the current TTI's Traffic Arrival, so Traffic Arrival is not provided separately); nothing from any other TTI, and no final metrics. A scheduling algorithm's internal state is explicit and threaded by the caller — each step receives it and returns a new one, never holding it as hidden mutable state — and a single step may return zero or more `AllocationDecision` values. `radio_scheduler.domain.Scheduler` (an algorithm's identity — name/version) and `SchedulingAlgorithm` (its behavioral contract) are deliberately distinct types. See [`ADR-008`](docs/adr/ADR-008-scheduler-statefulness.md) for the full contract.

`reference_implementations` has three algorithms implemented. `RoundRobin` is a frequency-domain scheduler that distributes each TTI's Resource Blocks one at a time across eligible UEs (`Buffer.occupancy_bytes > 0`), cycling through `observable_state.ues` in its given order — never re-sorted by `ue_id` — and resuming the rotation from the position right after the last-served UE, skipping temporarily ineligible UEs without resetting. `ProportionalFair` scores each eligible UE (`ChannelQuality.cqi > 0` and `Buffer.occupancy_bytes > 0`) as `cqi / average`, where `average` is that UE's tracked exponential moving average of achieved throughput, and serves the top-scoring UE with every available Resource Block that TTI — a consequence of CQI being frequency-flat in the current domain model, not per-Resource-Block; every UE's average is updated each TTI, including TTIs where nobody is served. `MaxCQI` selects, among UEs eligible by the same dual condition (`cqi > 0` and `Buffer.occupancy_bytes > 0`), the one with the highest `cqi` this TTI — ties broken by canonical `observable_state.ues` order — and gives it every available Resource Block that TTI, the same frequency-flat-CQI consequence as `ProportionalFair`; unlike the other two, it carries no memory across TTIs and reuses `EmptySchedulerState` instead of a dedicated state type. All three algorithms' state is threaded explicitly through `initial_state()`/`allocate()`, per the `scheduling_interface` contract.

`scenario_generator`, `scheduling_interface`, `RoundRobin`, `ProportionalFair`, and `MaxCQI` are covered by automated tests using the standard-library `unittest` — 113 tests as of this writing (see [`tests/README.md`](tests/README.md)). The Simulation Loop and `benchmark` are not implemented yet.

`docs/architecture.md` does not currently name a specific next module to implement; the next increment will be decided when work resumes. The project is being built incrementally, one small step at a time.
