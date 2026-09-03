# ADR-010: Benchmark v0.1 — computational cost measurement methodology

## Status

Proposed

## Date

2026-09-03

## Context

`benchmark` is the last module of the originally-planned architecture still unimplemented — `src/radio_scheduler/benchmark/` currently holds only an empty `__init__.py` and a placeholder `README.md`. `simulation_loop` v0.1 (ADR-009) now gives `benchmark` a well-defined unit to measure: `run(scenario, algorithm, pipeline_delay=0) -> SimulationResult[StateT]`, executed against any of the three implemented `reference_implementations` (Round Robin, Proportional Fair, MaxCQI).

`docs/architecture.md` describes `benchmark` as recording two categories of results — "Scheduling performance" (throughput, fairness, latency/QoS) and "System cost" (execution time, CPU, memory, scalability). `docs/architecture_review.md` separately flagged benchmark methodology as unresolved: "reliable measurement needs repetition, warm-up handling, variance/statistical reporting, and ideally process isolation... As currently described, `benchmark` could be satisfied by a single untrusted timing run, which would not produce numbers comparable across algorithms." Neither gap has been resolved until now.

Scheduling-performance metrics cannot be computed honestly yet: `domain.SchedulingPerformanceMetric` (`throughput_bps`, `fairness_index`, `average_latency_ttis`) presupposes a CQI-to-rate/capacity model that does not exist anywhere in the domain model — the same gap already deferred during Proportional Fair's design and again explicitly in ADR-009's own Consequences section ("this must be revisited before `benchmark`'s `throughput_bps`/`SchedulingPerformanceMetric` can be computed meaningfully"). Computational cost, by contrast, needs no such model: it can be measured directly around `simulation_loop.run()` as a black box, and has an immediate consumer — comparing Round Robin, Proportional Fair, and MaxCQI's own computational cost as scenario size grows. This ADR scopes Benchmark v0.1 to that computational-cost half only, and defers scheduling-performance metrics as a single atomic unit until the capacity/rate model exists.

The project has no third-party dependencies (`pyproject.toml`: `dependencies = []`), consistent with ADR-004's tooling scope and ADR-007's stdlib-first precedent; any measurement approach must stay within the standard library.

## Decision

**Benchmark v0.1 lives in `src/radio_scheduler/benchmark/`, measuring only the computational cost of running `simulation_loop.run()` — never scheduling-performance metrics.**

1. **Scope: computational cost only.** Execution time, CPU time, Python-tracked memory, and scalability (repeating the first three across scenario sizes, not a fourth independent metric) are in scope. `domain.SchedulingPerformanceMetric` and any fairness/throughput/packet-latency/QoS measure are explicitly out of scope for v0.1, for the reason given in Context — this module produces no `SchedulingPerformanceMetric` value, partially or otherwise.

2. **Two-tier API: a single-sample primitive and a repeating aggregator.** `measure_run(scenario, scheduler, algorithm, pipeline_delay=0) -> RunMeasurement` takes exactly one sample. `benchmark_run(scenario, scheduler, algorithm, repetitions=10, pipeline_delay=0) -> BenchmarkResult` calls `measure_run` `repetitions` times, keeps every raw sample, and reports the median of each metric as the primary aggregate. `repetitions < 1` raises `ValueError` before any execution.

3. **One uncounted warm-up execution precedes the repetition loop.** `benchmark_run` runs `simulation_loop.run()` once, discarding its result and timing, before the loop of `repetitions` measured calls to `measure_run` begins. CPython has no JIT warm-up in the traditional sense, but the first execution can still be skewed by import resolution, allocator arena growth, and page faults that later executions don't pay for. The warm-up never contributes to `samples` or to any aggregate.

4. **`gc.collect()` runs immediately before each measured pass, and finishes before that pass's instrumentation starts.** Garbage collection stays enabled during `simulation_loop.run()` itself — its cost during execution is part of the real behavior being measured; only the *state* GC is in when a pass begins is normalized, not GC's behavior during the pass.

5. **Time and memory are measured in two separate internal executions, never simultaneously.** `measure_run` performs: pass (a) — `time.perf_counter_ns()` and `time.process_time_ns()` around one execution of `simulation_loop.run()`, with `tracemalloc` inactive; pass (b) — a second, separate execution of `simulation_loop.run()` with the same `scenario`/`algorithm`/`pipeline_delay`, measuring only peak Python-allocator memory. Pass (b)'s `tracemalloc` lifecycle is precise: `gc.collect()` runs and finishes first (point 4); then `tracemalloc.is_tracing()` is checked — if tracing is already active on entry, `measure_run` raises `RuntimeError` and takes no measurement, rather than contaminating the result or silently altering tracing state some other part of the process may depend on; otherwise `tracemalloc.start()` runs immediately before `simulation_loop.run()` is called, `tracemalloc.get_traced_memory()`'s peak is read immediately after it returns, and `tracemalloc.stop()` runs in a `finally` block — including when `simulation_loop.run()` raises, so tracing is never left active after a failed measurement. `tracemalloc`'s own tracing overhead would otherwise perturb the wall-clock and CPU figures if active during pass (a), which is why the two passes never overlap. One call to `measure_run` therefore executes the scenario **twice**; this is documented in `measure_run`'s own docstring, not hidden as an implementation detail. A `benchmark_run` with the default `repetitions=10` performs 1 warm-up plus 20 real executions of `simulation_loop.run()` — 21 executions in total.

6. **`tracemalloc.get_traced_memory()` measures Python-allocator memory, not total process memory.** It tracks only allocations made through CPython's own allocator — not the interpreter's own footprint, not OS-level RSS, and not any native/C-level allocation outside CPython's allocator (currently moot, since the project has no native dependencies). It is a peak-usage proxy suitable for *relative* comparison between algorithms measured the same way, not a claim about the process's real memory footprint.

7. **No scalability-sweep helper in v0.1.** The caller constructs scenarios of different sizes (varying `num_ues`, `num_ttis`, `resource_blocks_per_tti`) and calls `benchmark_run` once per size; "scalability" is this usage pattern, not a new abstraction. A dedicated sweep/aggregation helper is deferred until a concrete consumer (a script, a report generator) needs one.

8. **Algorithm identity is a required, caller-supplied parameter.** `measure_run`/`benchmark_run` take an explicit `domain.Scheduler(name, version)` — unlike `simulation_loop.run()`, which deliberately has no way to know it (see `simulation_loop/runner.py`'s `SimulationResult` docstring). Nothing in this module verifies structurally that the supplied `Scheduler` identity actually corresponds to the `SchedulingAlgorithm` instance executed; matching the two is the caller's responsibility.

9. **Scenario and execution-environment provenance are recorded alongside every measurement.** `RunMeasurement`/`BenchmarkResult` record `scenario.seed` and dimensions read directly off `scenario` (TTI count, UE count, Resource Blocks per TTI) rather than requiring the generating config, so hand-built `Scenario` values (already a first-class case throughout this project's own tests) remain fully usable. They also record the execution environment, using only the standard library: `platform.python_implementation()`, `platform.python_version()`, `platform.platform()` (operating-system/platform description), `platform.machine()` (architecture), `platform.processor()` (processor description — accepted to be empty on some systems), and `os.cpu_count()` (logical CPU count). This provenance identifies and differentiates results and helps contextualize them; it does not guarantee full scenario reconstruction — two `Scenario` values sharing a seed and the same dimensions but built differently (e.g. by hand vs. via `generate_scenario`) would record identical scenario provenance — and environment fields do not make comparisons across different machines or sessions valid; they are recorded for context, not to normalize or authorize cross-environment comparison. Full persistence, serialization, or a "Run Record" concept are not introduced by this ADR.

10. **Two new, module-local result types — neither extends `domain.SchedulingPerformanceMetric`.** `RunMeasurement` (frozen, one sample: `wall_time_ns: int`, `cpu_time_ns: int`, `peak_traced_memory_bytes: int`, plus the provenance from points 8–9) and `BenchmarkResult` (frozen: the same provenance, `samples: tuple[RunMeasurement, ...]`, and `median_wall_time_ns: float`, `median_cpu_time_ns: float`, `median_peak_traced_memory_bytes: float` — `float` rather than `int` because `statistics.median()` can produce a fractional value with the default `repetitions=10`, an even count). Folding cost fields into `SchedulingPerformanceMetric` would conflate a blocked concern (radio performance) with an available one (computational cost), and would violate the same "algorithm/module-specific artifacts stay local" principle already applied when `simulation_loop.SimulationResult` was kept separate from `domain.Run`.

11. **Measurement primitives: `time.perf_counter_ns()`, `time.process_time_ns()`, `tracemalloc` — no `timeit`.** Times are stored as integer nanoseconds; memory as integer bytes. `timeit` is oriented at repeated micro-benchmarking of small snippets with its own internal loop, which would fight rather than compose with the explicit warm-up/GC/two-pass control this ADR requires.

12. **Determinism is a precondition of the measured pair, never a guarantee of `simulation_loop.run()` itself.** `simulation_loop.run()` faithfully executes whatever `algorithm.allocate()` does; it does not make that computation deterministic. Repetition-based aggregation (point 2) assumes the specific `(scenario, algorithm)` pair being measured is itself deterministic, so that sample-to-sample variation reflects measurement noise rather than genuinely different computation. This module does not verify that assumption.

## Alternatives considered

- **A single, unrepeated execution per measurement.** Rejected: dominated by OS-scheduling noise, exactly the failure mode `docs/architecture_review.md` already named as insufficient for comparing algorithms.
- **`timeit` instead of hand-rolled timing.** Rejected (point 11): its own repetition/loop model doesn't compose with the explicit warm-up-once, GC-per-pass, two-separate-passes structure this ADR requires.
- **Measuring time and memory in the same pass, with `tracemalloc` active throughout.** Rejected: `tracemalloc`'s tracing overhead would perturb the wall-clock and CPU figures it runs alongside.
- **The `resource` module (`getrusage`) instead of `tracemalloc` for memory.** Rejected: Unix-only, breaking portability; `tracemalloc` is stdlib and cross-platform.
- **Building a scalability-sweep helper now.** Rejected for v0.1 (point 7): no concrete consumer yet: an unused abstraction risked ahead of need, the same reasoning already applied to deferring a `SimulationStepResult` type in ADR-009.
- **Requiring `ScenarioGeneratorConfig` for provenance instead of deriving it from `Scenario`.** Rejected (point 9): would break for hand-built `Scenario` values and couple `benchmark` unnecessarily to `scenario_generator`'s config shape.
- **Extending `domain.SchedulingPerformanceMetric` with cost fields, or partially populating it.** Rejected (point 10): its three fields are all required `float`s with no capacity model to fill them honestly; partially populating it would mean inventing a sentinel value for the blocked fields, exactly the kind of workaround this project avoids.
- **Skipping the warm-up execution.** Considered, on the grounds that CPython has no JIT. Rejected: import resolution, allocator growth, and page faults can still skew a genuinely first execution, and the cost of one extra run is small relative to the reliability gained.

## Consequences

- Every `measure_run()` call executes the scenario twice internally (point 5); a `benchmark_run()` with the default `repetitions=10` performs 1 warm-up plus 20 real (measured) executions of `simulation_loop.run()` — 21 executions of `simulation_loop.run()` in total — for one `(scenario, scheduler, algorithm)` triple. This is real, documented computational cost of running the benchmark itself, not hidden in an implementation detail.
- Benchmark results are only meaningful as *relative* comparisons within the same machine and session — this ADR does not claim cross-session or cross-machine comparability, and does not introduce process isolation or CPU pinning (both remain named gaps in `docs/architecture_review.md`). Recording environment metadata (point 9) documents what produced a result; it does not authorize comparing results produced in different environments.
- If the measured `(scenario, algorithm)` pair is not itself deterministic, sample-to-sample variation in a `BenchmarkResult` may partly reflect genuine behavioral differences rather than pure measurement noise (point 12) — the median is still computed, but its interpretation weakens.
- `domain.SchedulingPerformanceMetric` remains completely unused by this module; computing it is future work requiring its own ADR once a capacity/rate model exists.
- `RunMeasurement`/`BenchmarkResult` trust the caller-supplied `Scheduler` identity without structural verification against the `SchedulingAlgorithm` actually executed (point 8) — a documented, not enforced, boundary.
- No scenario persistence, serialization, or "Run Record" concept exists after this ADR; a `BenchmarkResult` is a return value, not a stored artifact.
- Statistical reporting beyond the median (e.g. variance, percentiles), a scalability-sweep helper, and process isolation remain deferred, named gaps — not solved by this ADR.

## Validation criteria

- `len(BenchmarkResult.samples) == repetitions` for the `repetitions` value requested.
- The warm-up execution never appears in `samples` and is never included in any aggregate.
- `wall_time_ns`, `cpu_time_ns`, and `peak_traced_memory_bytes` are non-negative on every `RunMeasurement`.
- `BenchmarkResult`'s reported median for each metric is computed from the preserved `samples`, never from discarded or re-derived data.
- Scenario, algorithm, and environment provenance (seed, dimensions, `Scheduler` identity, Python implementation/version, platform, machine, processor, CPU count) is recorded correctly on every `RunMeasurement` and `BenchmarkResult`.
- For the deterministic reference algorithms (Round Robin, Proportional Fair, MaxCQI), tests confirm that the measurement instrumentation (timers, `gc.collect()`, `tracemalloc`) does not change the decisions `simulation_loop.run()` would otherwise produce for the same `(scenario, algorithm, pipeline_delay)` — verified by tests calling `simulation_loop.run()` directly and comparing against each pass's own outcome; `measure_run()` itself returns only a `RunMeasurement` and never compares or exposes the two passes' `SimulationResult` values internally.
- Calling `measure_run` while `tracemalloc.is_tracing()` is already `True` raises `RuntimeError` and takes no measurement.
- `tracemalloc.is_tracing()` is `False` after `measure_run` returns normally, and also after it propagates an exception raised by a failed `simulation_loop.run()` call.
- No `SchedulingPerformanceMetric` value is produced anywhere in this module.
- `benchmark_run(..., repetitions=0)` and any negative `repetitions` raise `ValueError` before any execution of `simulation_loop.run()`.

## Related documents

- [`ADR-002`](ADR-002-closed-loop-simulation.md) — closed-loop simulation; `benchmark` measures the same `simulation_loop.run()` this ADR builds on, never reimplementing it.
- [`ADR-004`](ADR-004-implementation-language-and-tooling.md) — Python/stdlib-first tooling scope this ADR's zero-new-dependency measurement approach follows.
- [`ADR-006`](ADR-006-entity-representation-conventions.md) — CQI-as-index convention with no rate/capacity field, the reason scheduling-performance metrics stay out of scope here.
- [`ADR-007`](ADR-007-scenario-generator-reproducibility-contract.md) — precedent for stdlib-only, locally-scoped methodology decisions.
- [`ADR-009`](ADR-009-simulation-loop-v0.1.md) — `simulation_loop.run()`, the unit this ADR measures; first ADR to defer the capacity/rate model this one defers again.
- [`docs/architecture_review.md`](../architecture_review.md) — original statement of the benchmark-methodology gap this ADR resolves for its own (computational-cost) scope.
- [`docs/specification/domain-model-v0.1.md`](../specification/domain-model-v0.1.md) — `SchedulingPerformanceMetric`'s definition, and Design Principle 5 (minimal and additive vocabulary), the basis for not extending it prematurely.
