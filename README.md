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
docs/                        Design and architecture documentation
src/
  scenario_generator/         Generates network scenarios, independent of any algorithm
  scheduling_interface/       The shared contract every scheduling algorithm implements
  reference_implementations/  Round Robin, Proportional Fair, MaxCQI, and future algorithms
  benchmark/                  Measures execution time, CPU, memory, scalability, and performance
tests/                        Functional tests with expected outputs
scripts/                      Operational entry points (run benchmarks, generate reports, etc.)
```

See [`docs/architecture.md`](docs/architecture.md) for the full architecture, including module responsibilities and data flow.

## Status

Early stage. The repository structure and architecture are defined; the implementation language and concrete `scheduling_interface` contract have not been chosen yet. The project is being built incrementally, one small step at a time.
