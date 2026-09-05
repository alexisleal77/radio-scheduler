"""Minimal end-to-end example: generate a scenario, benchmark Round Robin
against it, and print a readable summary.

No CLI argument parsing yet — scenario and scheduler are fixed. This is a
thin wrapper around already-implemented and already-tested APIs
(scenario_generator, reference_implementations, benchmark); it contains no
scheduling or benchmarking logic of its own.
"""

from radio_scheduler.benchmark import benchmark_run
from radio_scheduler.domain import Scheduler
from radio_scheduler.reference_implementations import RoundRobin
from radio_scheduler.scenario_generator import ScenarioGeneratorConfig, generate_scenario

SCENARIO_CONFIG = ScenarioGeneratorConfig(
    seed=42,
    num_ues=5,
    num_ttis=20,
    resource_blocks_per_tti=4,
    qos_class_names=("GBR", "Best Effort"),
)


def main() -> None:
    scenario = generate_scenario(SCENARIO_CONFIG)
    scheduler = Scheduler(name="RoundRobin", version="0.1")
    algorithm = RoundRobin()

    result = benchmark_run(scenario, scheduler, algorithm)

    print("Radio Scheduler — benchmark summary")
    print("====================================")
    print(f"Scheduler:            {result.scheduler_name} v{result.scheduler_version}")
    print(f"Scenario seed:        {result.scenario_seed}")
    print(f"TTIs:                 {result.scenario_num_ttis}")
    print(f"UEs:                  {result.scenario_num_ues}")
    print(
        "Resource Blocks/TTI:  "
        f"{result.scenario_resource_blocks_per_tti[0]} "
        f"(uniform across {len(result.scenario_resource_blocks_per_tti)} TTIs)"
    )
    print(f"Repetitions:          {len(result.samples)}")
    print()
    print(f"Median wall time:     {result.median_wall_time_ns / 1e6:.3f} ms")
    print(f"Median CPU time:      {result.median_cpu_time_ns / 1e6:.3f} ms")
    print(
        "Median peak memory:   "
        f"{result.median_peak_traced_memory_bytes / 1024:.1f} KiB"
    )
    print()
    print(
        f"Platform:             {result.python_implementation} "
        f"{result.python_version} on {result.platform}"
    )


if __name__ == "__main__":
    main()
