import gc
import os
import platform
import statistics
import time
import tracemalloc
from dataclasses import dataclass
from typing import TypeVar

from radio_scheduler.domain import Scenario, Scheduler
from radio_scheduler.scheduling_interface import SchedulingAlgorithm
from radio_scheduler.simulation_loop import run

StateT = TypeVar("StateT")


@dataclass(frozen=True)
class RunMeasurement:
    """One measured sample of running `simulation_loop.run()` for a single
    (Scenario, Scheduler, SchedulingAlgorithm) combination (ADR-010,
    docs/specification/benchmark-v0.1.md).

    `wall_time_ns` and `cpu_time_ns` come from pass (a) (timing, no
    `tracemalloc`); `peak_traced_memory_bytes` comes from pass (b) (a
    second, separate execution, with `tracemalloc` active) — never the
    same execution. `scenario_resource_blocks_per_tti` has exactly one
    entry per TTI in `scenario.ttis`, in ascending `TTI.index` order; it
    does not presuppose uniform Resource Block counts across TTIs.
    `cpu_count` is `None` whenever `os.cpu_count()` itself returns `None`.

    Carries no `scheduler_state` and is not generic — measurement data and
    provenance only, independent of any `SchedulingAlgorithm`'s state type.
    """

    wall_time_ns: int
    cpu_time_ns: int
    peak_traced_memory_bytes: int
    scenario_seed: int
    scenario_num_ttis: int
    scenario_num_ues: int
    scenario_resource_blocks_per_tti: tuple[int, ...]
    scheduler_name: str
    scheduler_version: str
    python_implementation: str
    python_version: str
    platform: str
    machine: str
    processor: str
    cpu_count: int | None


@dataclass(frozen=True)
class BenchmarkResult:
    """An aggregated set of `RunMeasurement` samples for one (Scenario,
    Scheduler, SchedulingAlgorithm) combination (ADR-010,
    docs/specification/benchmark-v0.1.md).

    The twelve provenance fields (everything but `samples` and the three
    `median_*` fields) are the same values shared by every element of
    `samples` — duplicated here for direct access without indexing into
    `samples`. This is a deliberate v0.1 choice: no separate provenance
    type is introduced.

    `median_wall_time_ns`, `median_cpu_time_ns`, and
    `median_peak_traced_memory_bytes` are `float`, not `int`, because
    `statistics.median()` returns the mean of the two central values when
    the sample count is even — the v0.1 default `repetitions=10` is even,
    so a fractional median is expected, not an error.
    """

    samples: tuple[RunMeasurement, ...]
    median_wall_time_ns: float
    median_cpu_time_ns: float
    median_peak_traced_memory_bytes: float
    scenario_seed: int
    scenario_num_ttis: int
    scenario_num_ues: int
    scenario_resource_blocks_per_tti: tuple[int, ...]
    scheduler_name: str
    scheduler_version: str
    python_implementation: str
    python_version: str
    platform: str
    machine: str
    processor: str
    cpu_count: int | None


def _gather_provenance(scenario: Scenario, scheduler: Scheduler) -> dict[str, object]:
    """The twelve provenance fields shared by `RunMeasurement` and
    `BenchmarkResult` (ADR-010 points 8-9), read directly off `scenario`
    and `scheduler` plus the standard-library environment probes named in
    docs/specification/benchmark-v0.1.md's flow step 4."""
    ttis_ascending = tuple(sorted(scenario.ttis, key=lambda tti: tti.index))
    resource_blocks_per_tti = tuple(
        sum(1 for rb in scenario.resource_blocks if rb.tti == tti)
        for tti in ttis_ascending
    )
    return {
        "scenario_seed": scenario.seed,
        "scenario_num_ttis": len(scenario.ttis),
        "scenario_num_ues": len(scenario.ues),
        "scenario_resource_blocks_per_tti": resource_blocks_per_tti,
        "scheduler_name": scheduler.name,
        "scheduler_version": scheduler.version,
        "python_implementation": platform.python_implementation(),
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "cpu_count": os.cpu_count(),
    }


def measure_run(
    scenario: Scenario,
    scheduler: Scheduler,
    algorithm: SchedulingAlgorithm[StateT],
    pipeline_delay: int = 0,
) -> RunMeasurement:
    """Takes exactly one measured sample of `(scenario, scheduler,
    algorithm)` (ADR-010, docs/specification/benchmark-v0.1.md).

    Executes `simulation_loop.run(scenario, algorithm, pipeline_delay)`
    twice internally: once timed (pass a, wall-clock and CPU time, no
    `tracemalloc`), once traced (pass b, `tracemalloc` active, for peak
    memory) — never both at once, since `tracemalloc`'s own overhead would
    perturb the timing figures. Raises `RuntimeError` immediately, with
    zero calls to `simulation_loop.run()`, if `tracemalloc.is_tracing()` is
    already `True` on entry; raises `RuntimeError` again, discarding pass
    (a)'s results and with pass (b) never executed, if tracemalloc became
    active between the two passes. Never mutates `scenario`, `scheduler`,
    or `algorithm`; never verifies that `scheduler` actually identifies
    `algorithm`.
    """
    if tracemalloc.is_tracing():
        raise RuntimeError(
            "tracemalloc is already tracing; measure_run() requires "
            "tracemalloc to be inactive when called"
        )

    gc.collect()
    t0_wall = time.perf_counter_ns()
    t0_cpu = time.process_time_ns()
    run(scenario, algorithm, pipeline_delay)
    t1_wall = time.perf_counter_ns()
    t1_cpu = time.process_time_ns()
    wall_time_ns = t1_wall - t0_wall
    cpu_time_ns = t1_cpu - t0_cpu

    gc.collect()
    if tracemalloc.is_tracing():
        raise RuntimeError(
            "tracemalloc became active between measure_run()'s timing and "
            "memory passes; aborting before the memory pass"
        )

    tracemalloc.start()
    try:
        run(scenario, algorithm, pipeline_delay)
        _, peak_traced_memory_bytes = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()

    return RunMeasurement(
        wall_time_ns=wall_time_ns,
        cpu_time_ns=cpu_time_ns,
        peak_traced_memory_bytes=peak_traced_memory_bytes,
        **_gather_provenance(scenario, scheduler),
    )


def benchmark_run(
    scenario: Scenario,
    scheduler: Scheduler,
    algorithm: SchedulingAlgorithm[StateT],
    repetitions: int = 10,
    pipeline_delay: int = 0,
) -> BenchmarkResult:
    """Runs one uncounted warm-up execution, then calls `measure_run`
    `repetitions` times, preserving every sample and computing medians
    (ADR-010, docs/specification/benchmark-v0.1.md).

    Raises `ValueError` immediately, before any execution, if
    `repetitions < 1`. The warm-up execution of
    `simulation_loop.run(scenario, algorithm, pipeline_delay)` is
    discarded and never contributes to `samples` or to any of the three
    medians. A successful call executes `simulation_loop.run()` exactly
    `1 + 2 * repetitions` times (1 warm-up, plus 2 per `measure_run`
    call). If the warm-up or any `measure_run` call raises, that
    exception propagates immediately and no `BenchmarkResult` — partial
    or otherwise — is returned.
    """
    if repetitions < 1:
        raise ValueError(f"repetitions must be >= 1 (got {repetitions})")

    run(scenario, algorithm, pipeline_delay)

    samples = tuple(
        measure_run(scenario, scheduler, algorithm, pipeline_delay)
        for _ in range(repetitions)
    )

    median_wall_time_ns = float(statistics.median(s.wall_time_ns for s in samples))
    median_cpu_time_ns = float(statistics.median(s.cpu_time_ns for s in samples))
    median_peak_traced_memory_bytes = float(
        statistics.median(s.peak_traced_memory_bytes for s in samples)
    )

    return BenchmarkResult(
        samples=samples,
        median_wall_time_ns=median_wall_time_ns,
        median_cpu_time_ns=median_cpu_time_ns,
        median_peak_traced_memory_bytes=median_peak_traced_memory_bytes,
        **_gather_provenance(scenario, scheduler),
    )
