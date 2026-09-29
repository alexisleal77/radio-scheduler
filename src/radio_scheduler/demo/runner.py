from dataclasses import dataclass

from radio_scheduler.benchmark import BenchmarkResult, benchmark_run
from radio_scheduler.demo.scenarios import DemoScenario, build_demo_scenarios
from radio_scheduler.domain import AllocationDecision, Scheduler
from radio_scheduler.reference_implementations import MaxCQI, ProportionalFair, RoundRobin
from radio_scheduler.scheduling_interface import SchedulingAlgorithm
from radio_scheduler.simulation_loop import run


@dataclass(frozen=True)
class AlgorithmSpec:
    """One reference implementation paired with the domain identity
    (`Scheduler`) `benchmark.benchmark_run` needs for provenance."""

    scheduler: Scheduler
    algorithm: SchedulingAlgorithm


def default_algorithms() -> tuple[AlgorithmSpec, ...]:
    """The three existing reference implementations, each a fresh, stateless
    instance — none holds hidden mutable state (ADR-008), so reusing one
    instance across scenarios is safe, but a fresh instance is built here
    per call for clarity."""
    return (
        AlgorithmSpec(Scheduler(name="RoundRobin", version="0.1"), RoundRobin()),
        AlgorithmSpec(Scheduler(name="ProportionalFair", version="0.1"), ProportionalFair()),
        AlgorithmSpec(Scheduler(name="MaxCQI", version="0.1"), MaxCQI()),
    )


@dataclass(frozen=True)
class DemoRunResult:
    """One (scenario, algorithm) pair's decisions and computational-cost
    benchmark — the two kinds of evidence Delivery A must produce."""

    scenario_id: str
    scenario_description: str
    scheduler_name: str
    scheduler_version: str
    decisions: tuple[AllocationDecision, ...]
    benchmark: BenchmarkResult


def run_demo(
    demo_scenarios: tuple[DemoScenario, ...] | None = None,
    algorithms: tuple[AlgorithmSpec, ...] | None = None,
    benchmark_repetitions: int = 10,
) -> tuple[DemoRunResult, ...]:
    """Runs every (scenario, algorithm) pair through `simulation_loop.run()`
    (for decisions) and `benchmark.benchmark_run()` (for computational
    cost), orchestrating already-implemented and already-tested public
    APIs only — no scheduling or benchmarking logic is implemented here.

    Each pair gets an independent run: `simulation_loop.run()` and
    `benchmark.benchmark_run()` both call `algorithm.initial_state()`
    internally before processing any TTI, so no algorithm's state carries
    over from one scenario, or from one algorithm to another.
    """
    demo_scenarios = demo_scenarios if demo_scenarios is not None else build_demo_scenarios()
    algorithms = algorithms if algorithms is not None else default_algorithms()

    results: list[DemoRunResult] = []
    for demo_scenario in demo_scenarios:
        for spec in algorithms:
            simulation_result = run(demo_scenario.scenario, spec.algorithm)
            benchmark_result = benchmark_run(
                demo_scenario.scenario,
                spec.scheduler,
                spec.algorithm,
                repetitions=benchmark_repetitions,
            )
            results.append(
                DemoRunResult(
                    scenario_id=demo_scenario.scenario_id,
                    scenario_description=demo_scenario.description,
                    scheduler_name=spec.scheduler.name,
                    scheduler_version=spec.scheduler.version,
                    decisions=simulation_result.decisions,
                    benchmark=benchmark_result,
                )
            )
    return tuple(results)
