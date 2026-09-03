# benchmark

Measures the **computational cost** of running `simulation_loop.run()` for one `(Scenario, Scheduler, SchedulingAlgorithm)` combination: wall-clock time, CPU time, and peak Python-allocator-traced memory. See [`ADR-010`](../../../docs/adr/ADR-010-computational-cost-benchmark-v0.1.md) ([pt-BR](../../../docs/adr/pt-BR/ADR-010-computational-cost-benchmark-v0.1.md)) for the full decision this module implements, and [`docs/specification/benchmark-v0.1.md`](../../../docs/specification/benchmark-v0.1.md) for its exact operational contract.

Benchmarking measures and compares algorithms; it does not assert correctness (see `tests/` for that).

## Scheduling performance is out of scope

`benchmark` v0.1 produces no `domain.SchedulingPerformanceMetric` value — no throughput, fairness, packet latency, or QoS satisfaction figure. That half of the original `benchmark` scope (see `docs/architecture.md`) is deferred as a single atomic unit until a CQI-to-rate/capacity model exists in the domain model (ADR-010). Only computational cost is implemented here.

## Public API

- **`RunMeasurement`** — one measured sample: `wall_time_ns`, `cpu_time_ns`, `peak_traced_memory_bytes`, plus scenario/scheduler/environment provenance.
- **`BenchmarkResult`** — an aggregated set of `RunMeasurement` samples for one `(scenario, scheduler, algorithm)`: `samples`, the three `median_*` fields, and the same provenance.
- **`measure_run(scenario, scheduler, algorithm, pipeline_delay=0)`** — takes exactly one `RunMeasurement`.
- **`benchmark_run(scenario, scheduler, algorithm, repetitions=10, pipeline_delay=0)`** — runs a warm-up plus `repetitions` calls to `measure_run`, returning a `BenchmarkResult`.

## Methodology

`measure_run` takes time and memory in two separate internal executions of `simulation_loop.run()`, never simultaneously — `tracemalloc`'s own overhead would otherwise perturb the timing figures:

- **Pass (a) — timing**: `gc.collect()`, then `time.perf_counter_ns()`/`time.process_time_ns()` around one execution, with `tracemalloc` inactive.
- **Pass (b) — memory**: `gc.collect()`, then a second, independent execution with `tracemalloc` active, reading the peak from `tracemalloc.get_traced_memory()`.

One `measure_run` call therefore executes `simulation_loop.run()` twice. `benchmark_run` runs one uncounted warm-up execution first (discarded, never in `samples` or any median), then calls `measure_run` `repetitions` times, preserving every sample in `BenchmarkResult.samples` and reporting `statistics.median()` of each metric as `median_wall_time_ns`, `median_cpu_time_ns`, and `median_peak_traced_memory_bytes`. With the default `repetitions=10`, a `benchmark_run` call executes `simulation_loop.run()` a total of `1 + 2 * 10 = 21` times.

## Provenance

Every `RunMeasurement`/`BenchmarkResult` records `scenario.seed`, TTI/UE counts, Resource Blocks per TTI, the caller-supplied `Scheduler` identity, and the execution environment (`platform.python_implementation()`, `platform.python_version()`, `platform.platform()`, `platform.machine()`, `platform.processor()`, `os.cpu_count()`). This identifies and contextualizes a result; it does not verify that `scheduler` actually corresponds to `algorithm` (a documented, unenforced trust boundary — ADR-010 point 8).

## Limitations

Results are only meaningful as relative comparisons within the same machine and session. Recording environment metadata documents what produced a result; it does not authorize comparing results captured on different machines, OS loads, or sessions — no process isolation or CPU pinning is performed.

## Example

```python
from radio_scheduler.benchmark import benchmark_run
from radio_scheduler.domain import Scheduler
from radio_scheduler.reference_implementations import RoundRobin
from radio_scheduler.scenario_generator import ScenarioGeneratorConfig, generate_scenario

config = ScenarioGeneratorConfig(
    seed=42,
    num_ues=2,
    num_ttis=3,
    resource_blocks_per_tti=2,
    qos_class_names=("GBR", "Best Effort"),
)
scenario = generate_scenario(config)

result = benchmark_run(scenario, Scheduler(name="RoundRobin", version="0.1"), RoundRobin())
print(result.median_wall_time_ns, len(result.samples))
```

Status: v0.1 implemented. See [`docs/architecture.md`](../../../docs/architecture.md).
