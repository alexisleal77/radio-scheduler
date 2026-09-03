# Benchmark v0.1 — Operational Specification

## Purpose

This document defines the operational contract for `radio_scheduler.benchmark` v0.1: the exact public API, data shapes, execution flow, error conditions, and invariants an implementation must satisfy. It exists alongside [`ADR-010`](../adr/ADR-010-computational-cost-benchmark-v0.1.md), which records *why* this module is scoped and designed this way; this document records *what*, precisely, must be built. Where the two could be read as disagreeing, ADR-010 governs — this specification is a restatement and operationalization of its decisions, not an independent source of authority.

## Scope

`benchmark` v0.1 measures the **computational cost** of running `simulation_loop.run()` for one `(Scenario, Scheduler, SchedulingAlgorithm)` combination: wall-clock time, CPU time, and peak Python-allocator-traced memory. "Scalability" is not a fourth measured quantity — it is the act of applying this same measurement across scenarios of different sizes, a usage pattern left to the caller (ADR-010 point 7).

## Explicit Exclusions

The following are out of scope for v0.1 and must not be implemented as part of it:

- Any `domain.SchedulingPerformanceMetric` value (`throughput_bps`, `fairness_index`, `average_latency_ttis`) or any other radio-performance measure (fairness, throughput, packet latency, QoS satisfaction).
- A scalability-sweep helper or any multi-scenario orchestration abstraction.
- Verification that a supplied `Scheduler` identity matches the `SchedulingAlgorithm` instance actually executed.
- Persistence, serialization, or a "Run Record" concept — a `BenchmarkResult` is a return value, not a stored artifact.
- Support for `pipeline_delay` values other than `0` — this module does not itself validate `pipeline_delay`; it relies entirely on `simulation_loop.run()`'s own validation (ADR-009).
- Statistical reporting beyond the median (variance, percentiles, confidence intervals).
- Process isolation, CPU pinning, or any control over OS scheduling.
- Any new third-party dependency. Only the standard library (`time`, `gc`, `tracemalloc`, `platform`, `os`, `statistics`, `dataclasses`, `typing`) may be used.

## Responsibilities and Boundaries

- `benchmark` depends on `simulation_loop`, `domain`, and `scheduling_interface`. It never calls `scenario_generator` or `reference_implementations` directly — a `Scenario` and a `SchedulingAlgorithm` instance are supplied by the caller, already constructed.
- `benchmark` treats `simulation_loop.run()` as a black box: it never inspects or special-cases the returned `SimulationResult`'s `decisions` or `final_scheduler_state`; it only discards them after each execution.
- `benchmark` never mutates `scenario`, `scheduler`, or `algorithm`.
- `benchmark` never validates `pipeline_delay` itself — that check belongs solely to `simulation_loop.run()`, avoiding duplicated validation logic.
- `benchmark` never verifies that the caller-supplied `Scheduler` identity corresponds to the `SchedulingAlgorithm` actually executed (ADR-010 point 8) — this is a documented, unenforced trust boundary.

## Public API

Exported from `radio_scheduler.benchmark`: `RunMeasurement`, `BenchmarkResult`, `measure_run`, `benchmark_run`.

### `RunMeasurement`

A frozen dataclass representing one measured sample.

| Field | Type |
|---|---|
| `wall_time_ns` | `int` |
| `cpu_time_ns` | `int` |
| `peak_traced_memory_bytes` | `int` |
| `scenario_seed` | `int` |
| `scenario_num_ttis` | `int` |
| `scenario_num_ues` | `int` |
| `scenario_resource_blocks_per_tti` | `tuple[int, ...]` |
| `scheduler_name` | `str` |
| `scheduler_version` | `str` |
| `python_implementation` | `str` |
| `python_version` | `str` |
| `platform` | `str` |
| `machine` | `str` |
| `processor` | `str` |
| `cpu_count` | `int \| None` |

`scenario_resource_blocks_per_tti` has exactly one entry per TTI in `scenario.ttis`, ordered by ascending `TTI.index` — the same ordering `simulation_loop.run()` itself imposes. Entry `i` is the count of `ResourceBlock` records in `scenario.resource_blocks` whose `tti` equals the TTI at ascending position `i`. This field does not presuppose uniform Resource Block counts across TTIs; a `Scenario` built by hand with differing per-TTI counts is fully representable. `cpu_count` is `None` whenever `os.cpu_count()` itself returns `None` (undetermined logical CPU count on the host).

`RunMeasurement` carries no `scheduler_state` and is not generic — it is measurement data and provenance only, independent of any specific `SchedulingAlgorithm`'s internal state type.

### `BenchmarkResult`

A frozen dataclass representing an aggregated set of samples for one `(scenario, scheduler, algorithm)` combination.

| Field | Type |
|---|---|
| `samples` | `tuple[RunMeasurement, ...]` |
| `median_wall_time_ns` | `float` |
| `median_cpu_time_ns` | `float` |
| `median_peak_traced_memory_bytes` | `float` |
| `scenario_seed` | `int` |
| `scenario_num_ttis` | `int` |
| `scenario_num_ues` | `int` |
| `scenario_resource_blocks_per_tti` | `tuple[int, ...]` |
| `scheduler_name` | `str` |
| `scheduler_version` | `str` |
| `python_implementation` | `str` |
| `python_version` | `str` |
| `platform` | `str` |
| `machine` | `str` |
| `processor` | `str` |
| `cpu_count` | `int \| None` |

The twelve provenance fields are the same values that appear on every element of `samples` (all samples share one `scenario`, `scheduler`, and execution environment) and are duplicated here at the aggregate level for direct access without indexing into `samples`. `BenchmarkResult` does not introduce a separate provenance type — this is a deliberate v0.1 choice (see ADR-010 point 10 and this specification's design discussion); the duplication is accepted.

The three `median_*` fields are `float`, not `int`, because `statistics.median()` returns the arithmetic mean of the two central values when the sample count is even — the v0.1 default of `repetitions=10` is even, so a fractional median is a normal, expected outcome, not an error.

### `measure_run()`

```python
def measure_run(
    scenario: Scenario,
    scheduler: Scheduler,
    algorithm: SchedulingAlgorithm[StateT],
    pipeline_delay: int = 0,
) -> RunMeasurement:
    ...
```

Takes exactly one measured sample of `(scenario, scheduler, algorithm)`. See "measure_run() — Exact Flow" below.

### `benchmark_run()`

```python
def benchmark_run(
    scenario: Scenario,
    scheduler: Scheduler,
    algorithm: SchedulingAlgorithm[StateT],
    repetitions: int = 10,
    pipeline_delay: int = 0,
) -> BenchmarkResult:
    ...
```

Runs one uncounted warm-up execution, then calls `measure_run` `repetitions` times, preserving every sample and computing medians. See "benchmark_run() — Exact Flow" below.

Benchmark v0.1 assumes that Python garbage collection is enabled when `measure_run()` and `benchmark_run()` are called. Behavior with garbage collection disabled by the caller is outside the v0.1 contract.

## `measure_run()` — Exact Flow

1. **Entry precondition.** If `tracemalloc.is_tracing()` is `True`, raise `RuntimeError` immediately. This is the first action of the function: no `gc.collect()`, no timing pass, no call to `simulation_loop.run()`, and no call to `tracemalloc.start()` or `tracemalloc.stop()` occurs on this path. External tracing state is left exactly as found.

2. **Pass (a) — timing.**
   a. `gc.collect()`.
   b. Record `t0_wall = time.perf_counter_ns()` and `t0_cpu = time.process_time_ns()`.
   c. Call `simulation_loop.run(scenario, algorithm, pipeline_delay)`; discard the returned `SimulationResult`.
   d. Record `t1_wall = time.perf_counter_ns()` and `t1_cpu = time.process_time_ns()`.
   e. `wall_time_ns = t1_wall - t0_wall`; `cpu_time_ns = t1_cpu - t0_cpu`.

3. **Pass (b) — memory.**
   a. `gc.collect()`.
   b. **Second precondition check**, immediately before `tracemalloc.start()`: if `tracemalloc.is_tracing()` is `True` at this point, raise `RuntimeError` immediately. This protects against external tracing having been activated between pass (a) and this point. On this path: `tracemalloc.start()` is never called, `tracemalloc.stop()` is never called, the memory pass is never executed, and no result — partial or otherwise — is returned. The results of pass (a) are discarded along with everything else; the whole `measure_run()` call fails.
   c. `tracemalloc.start()`.
   d. `try:` call `simulation_loop.run(scenario, algorithm, pipeline_delay)` again (a second, independent execution); discard the returned `SimulationResult`; read `peak_traced_memory_bytes` from `tracemalloc.get_traced_memory()`'s second element.
   e. `finally:` call `tracemalloc.stop()` — this runs whether step (d) succeeded or `simulation_loop.run()` raised.

Garbage collection remains enabled while `simulation_loop.run()` executes. The benchmark does not call `gc.disable()`. The cost of garbage collection during execution is therefore included in the measured behavior.

4. **Gather provenance.** Read `scenario.seed`; `len(scenario.ttis)`; `len(scenario.ues)`; the per-TTI Resource Block counts (ascending `TTI.index` order) as `scenario_resource_blocks_per_tti`; `scheduler.name` and `scheduler.version`; and the environment fields via `platform.python_implementation()`, `platform.python_version()`, `platform.platform()`, `platform.machine()`, `platform.processor()`, and `os.cpu_count()`.

5. **Construct and return** a `RunMeasurement` from steps 2, 3, and 4's results.

A single successful call to `measure_run()` executes `simulation_loop.run()` exactly twice (step 2c and step 3d). A call that raises at step 1 or step 3b executes it zero times.

## `benchmark_run()` — Exact Flow

1. If `repetitions < 1`, raise `ValueError` immediately. No execution of any kind occurs on this path.

2. **Warm-up.** Call `simulation_loop.run(scenario, algorithm, pipeline_delay)` once; discard the returned `SimulationResult` entirely — no timing, no memory tracing, no `RunMeasurement` is constructed for this call. This execution is never counted and never contributes to `samples` or to any aggregate.

3. **Repetition loop.** Call `measure_run(scenario, scheduler, algorithm, pipeline_delay)` exactly `repetitions` times, appending each returned `RunMeasurement` to `samples` in call order. If any call raises (either `RuntimeError` from `measure_run`'s own preconditions, or an exception propagated from `simulation_loop.run()`), that exception propagates out of `benchmark_run()` immediately — no `BenchmarkResult`, partial or otherwise, is returned.

4. **Aggregate.** Compute `median_wall_time_ns`, `median_cpu_time_ns`, and `median_peak_traced_memory_bytes` via `statistics.median()` over the corresponding field across all elements of `samples`.

5. **Construct and return** a `BenchmarkResult` from `samples`, the three medians, and the provenance fields (identical across all samples, since they share one `scenario` and one `scheduler`; read once, not re-derived per sample).

A successful `benchmark_run(repetitions=N)` call executes `simulation_loop.run()` exactly `1 + 2N` times: 1 for the warm-up, plus 2 for each of the `N` calls to `measure_run`. For the default `N = 10`, this is 21 executions in total.

## Errors and Rejection Conditions

| Condition | Behavior |
|---|---|
| `tracemalloc.is_tracing()` is `True` when `measure_run()` is called | `RuntimeError`, raised as the first action; zero calls to `simulation_loop.run()`; `tracemalloc.start()`/`stop()` never called. |
| `tracemalloc.is_tracing()` is `True` immediately before `tracemalloc.start()` in pass (b) (i.e., became active between passes) | `RuntimeError`; `tracemalloc.start()`/`stop()` never called; pass (a)'s results are discarded; no partial `RunMeasurement` returned. |
| `benchmark_run(..., repetitions < 1)` | `ValueError`, raised before any execution. |
| `simulation_loop.run()` raises any exception (invalid `pipeline_delay`, invalid decision, or an exception from the algorithm itself) | Propagates unmodified through `measure_run()` and, if applicable, `benchmark_run()`. Never caught or wrapped. `tracemalloc.stop()` still runs via `finally` if the exception occurs during pass (b)'s execution of `simulation_loop.run()`. |

## Invariants

- If `tracemalloc.is_tracing()` is `True` at the moment `measure_run()` is called, zero calls to `simulation_loop.run()` occur, and `tracemalloc.start()`/`tracemalloc.stop()` are never called.
- If `tracemalloc.is_tracing()` is `True` immediately before `tracemalloc.start()` in pass (b), pass (b) is never executed, `tracemalloc.start()`/`stop()` are never called, and no `RunMeasurement` — partial or complete — is returned; `measure_run()` raises instead.
- Every successful call to `measure_run()` executes `simulation_loop.run()` exactly twice.
- Every successful call to `benchmark_run(repetitions=N)` executes `simulation_loop.run()` exactly `1 + 2N` times.
- `gc.collect()` runs and completes before each of the two passes' instrumented region begins; it never runs during a pass's instrumented region.
- Garbage collection is enabled during every measured call to `simulation_loop.run()`.
- `tracemalloc.is_tracing()` is `False` immediately after any call to `measure_run()` returns, whether it returned successfully or raised.
- The warm-up execution in `benchmark_run()` never contributes to `samples` or to any of the three medians.
- `len(BenchmarkResult.samples) == repetitions` for the `repetitions` value passed to a successful `benchmark_run()` call.
- All three numeric measurement fields (`wall_time_ns`, `cpu_time_ns`, `peak_traced_memory_bytes`) are non-negative on every `RunMeasurement`.
- `BenchmarkResult`'s three median fields are computed solely from `samples`; they are never independently re-measured or re-derived from any other source.
- `scenario_resource_blocks_per_tti` always has exactly `len(scenario.ttis)` elements, in ascending `TTI.index` order, and never assumes or requires uniform counts across TTIs.
- Neither `measure_run()` nor `benchmark_run()` ever produces a `domain.SchedulingPerformanceMetric` value.
- Neither function mutates `scenario`, `scheduler`, or `algorithm`.
- The `Scheduler` identity supplied by the caller is never checked against the `SchedulingAlgorithm` instance actually executed.

## Acceptance Criteria

Identical to the "Validation criteria" section of ADR-010, verbatim — this specification adds no criteria beyond it and omits none:

- `run(scenario, algorithm, pipeline_delay=0)` semantics inherited from `simulation_loop` (ADR-009) are never altered by this module's instrumentation.
- `len(BenchmarkResult.samples) == repetitions` for the requested `repetitions`.
- The warm-up execution never appears in `samples` and is never included in any aggregate.
- `wall_time_ns`, `cpu_time_ns`, and `peak_traced_memory_bytes` are non-negative on every `RunMeasurement`.
- `BenchmarkResult`'s reported median for each metric is computed from the preserved `samples`, never from discarded or re-derived data.
- Scenario, algorithm, and environment provenance is recorded correctly on every `RunMeasurement` and `BenchmarkResult`.
- For the deterministic reference algorithms (Round Robin, Proportional Fair, MaxCQI), the measurement instrumentation does not change the decisions `simulation_loop.run()` would otherwise produce for the same `(scenario, algorithm, pipeline_delay)`.
- Calling `measure_run` while `tracemalloc.is_tracing()` is already `True` raises `RuntimeError` and takes no measurement — zero calls to `simulation_loop.run()`.
- `tracemalloc.is_tracing()` is `False` after `measure_run` returns normally, and also after it propagates an exception.
- No `SchedulingPerformanceMetric` value is produced anywhere in this module.
- `benchmark_run(..., repetitions=0)` and any negative `repetitions` raise `ValueError` before any execution of `simulation_loop.run()`.

## Test Plan

Proposed file: `tests/test_benchmark.py`, following the structure and conventions of `tests/test_simulation_loop.py`.

| ADR-010 / specification criterion | Test |
|---|---|
| Result types are structurally correct and immutable | `test_run_measurement_is_immutable`, `test_benchmark_result_is_immutable`, field-presence assertions for both types |
| `len(samples) == repetitions` | `test_len_samples_equals_requested_repetitions` (multiple values of `repetitions`, including the default 10) |
| Warm-up excluded from samples/aggregates | `test_warmup_not_included_in_samples_or_medians`, using a call-counting algorithm double |
| Non-negative measurement fields | `test_run_measurement_fields_are_non_negative` |
| Median computed from preserved samples | `test_median_matches_statistics_median_of_samples` |
| Provenance recorded correctly | `test_provenance_fields_populated_correctly` (seed, TTI/UE counts, scheduler identity, environment fields) |
| Non-uniform Resource Blocks per TTI | `test_scenario_resource_blocks_per_tti_reflects_non_uniform_counts` — a hand-built `Scenario` with a different `ResourceBlock` count per TTI (e.g. 1, 3, 2 across three TTIs); asserts `scenario_resource_blocks_per_tti` has one element per TTI, in ascending `TTI.index` order, with each element matching that TTI's exact count, and that the tuple is not collapsed or averaged into a single value |
| Instrumentation does not alter decisions | `test_instrumented_run_matches_direct_simulation_loop_run` (Round Robin, Proportional Fair, MaxCQI) |
| `measure_run` executes `simulation_loop.run()` exactly twice (normal path) | `test_measure_run_executes_simulation_loop_exactly_twice` |
| `tracemalloc` active at entry → `RuntimeError`, zero executions | `test_measure_run_rejects_already_active_tracemalloc_at_entry` — pre-activates `tracemalloc`, uses a call-counting algorithm double, asserts `RuntimeError` and zero calls to `initial_state()`/`allocate()` |
| `tracemalloc` activated between passes → `RuntimeError`, no partial result | `test_measure_run_rejects_tracemalloc_activated_between_passes` — a test double that calls `tracemalloc.start()` as a side effect during pass (a)'s execution of `simulation_loop.run()`, then asserts `RuntimeError` from `measure_run`, that `tracemalloc.start()`/`stop()` were not called again by `measure_run` itself, and that no `RunMeasurement` is returned |
| `tracemalloc` stopped after success | `test_tracemalloc_stopped_after_successful_measurement` |
| `tracemalloc` stopped after failure during pass (b) | `test_tracemalloc_stopped_after_failed_measurement` |
| Garbage collection remains enabled during measured execution | `test_garbage_collection_remains_enabled_during_measured_calls` — an algorithm double that records `gc.isenabled()` at the moment `allocate()` is called; asserts the recorded value is `True` for both the timing pass and the memory pass of `measure_run()` |
| `repetitions < 1` rejected | `test_zero_and_negative_repetitions_raise_value_error` |
| `Scheduler` identity not verified | `test_scheduler_identity_mismatch_is_not_verified` — mismatched name/version with a real algorithm, asserts no error |
| No `SchedulingPerformanceMetric` produced | covered structurally by the field-presence assertions above; no dedicated behavioral test |
| End-to-end, all three reference algorithms | `test_benchmark_run_succeeds_for_round_robin_proportional_fair_and_max_cqi`, using `generate_scenario()` output |

No test asserts a relative-timing comparison between two different scenario sizes or algorithms — timing-based inequality assertions are inherently flaky and are deliberately excluded, consistent with this project's established testing practice.

## Expected Implementation Files

- `src/radio_scheduler/benchmark/measurement.py` — `RunMeasurement`, `BenchmarkResult`, `measure_run()`, `benchmark_run()`, and a private provenance-gathering helper.
- `src/radio_scheduler/benchmark/__init__.py` — exports.
- `src/radio_scheduler/benchmark/README.md` — updated from "not yet implemented."
- `tests/test_benchmark.py` — new.
- `tests/README.md` — updated coverage and test count.
- `README.md` (root) — updated module status and test count.
- `docs/architecture.md` — updated `benchmark` status line.

## Related Documents

- [`ADR-010`](../adr/ADR-010-computational-cost-benchmark-v0.1.md) — the decision this specification operationalizes.
- [`ADR-009`](../adr/ADR-009-simulation-loop-v0.1.md) — `simulation_loop.run()`, the unit this module measures.
- [`docs/specification/domain-model-v0.1.md`](domain-model-v0.1.md) — `Scenario`, `ResourceBlock`, `Scheduler`, and `SchedulingPerformanceMetric` definitions referenced throughout.
