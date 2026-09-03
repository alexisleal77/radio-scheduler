from dataclasses import dataclass


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
