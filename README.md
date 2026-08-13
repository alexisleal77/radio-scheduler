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
  scenario_generator/                   Generates network scenarios — not yet implemented
  scheduling_interface/                 The shared contract every scheduling algorithm implements — not yet implemented
  reference_implementations/            Round Robin, Proportional Fair, MaxCQI, and future algorithms — not yet implemented
  benchmark/                            Measures execution time, CPU, memory, scalability, and performance — not yet implemented
tests/                                  Functional tests with expected outputs — not yet implemented
scripts/                                Operational entry points (run benchmarks, generate reports, etc.) — not yet implemented
```

See [`docs/architecture.md`](docs/architecture.md) for the full architecture, including module responsibilities and data flow. Architecturally significant decisions are recorded in [`docs/adr/`](docs/adr/).

## Status

The implementation language is Python (ADR-004). The initial architecture — module boundaries, data flow, and the closed-loop simulation model — is defined, and all architecturally significant decisions are documented as ADRs in [`docs/adr/`](docs/adr/). The domain model ([`docs/specification/domain-model-v0.1.md`](docs/specification/domain-model-v0.1.md)) is implemented as 13 immutable entities in `radio_scheduler.domain`; the `Scenario → Run → AllocationDecision → SchedulingPerformanceMetric` composition has been verified. No formal automated test suite exists yet (see [`tests/README.md`](tests/README.md)). The next module to be implemented is `scenario_generator`. The project is being built incrementally, one small step at a time.
