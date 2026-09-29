import unittest

from radio_scheduler.demo import (
    build_demo_scenarios,
    default_algorithms,
    run_demo,
)
from radio_scheduler.demo.report import decisions_trace
from radio_scheduler.reference_implementations import MaxCQI, ProportionalFair, RoundRobin
from radio_scheduler.simulation_loop import run


def _scenario(scenario_id):
    for demo_scenario in build_demo_scenarios():
        if demo_scenario.scenario_id == scenario_id:
            return demo_scenario.scenario
    raise KeyError(scenario_id)


class UECompetitionOracleTests(unittest.TestCase):
    """Hand-traced expected decisions for `ue_competition`: two UEs tied on
    CQI (10) every TTI, both with backlog every TTI."""

    def setUp(self):
        self.scenario = _scenario("ue_competition")

    def test_round_robin_splits_one_rb_per_ue_each_tti(self):
        result = run(self.scenario, RoundRobin())
        trace = decisions_trace(result.decisions)
        self.assertEqual(
            trace,
            {
                0: [
                    {"ue_id": "ue-0", "resource_block_ids": ["rb-0-0"]},
                    {"ue_id": "ue-1", "resource_block_ids": ["rb-0-1"]},
                ],
                1: [
                    {"ue_id": "ue-0", "resource_block_ids": ["rb-1-0"]},
                    {"ue_id": "ue-1", "resource_block_ids": ["rb-1-1"]},
                ],
            },
        )

    def test_proportional_fair_switches_to_the_unserved_ue_next_tti(self):
        result = run(self.scenario, ProportionalFair())
        trace = decisions_trace(result.decisions)
        self.assertEqual(
            trace,
            {
                0: [{"ue_id": "ue-0", "resource_block_ids": ["rb-0-0", "rb-0-1"]}],
                1: [{"ue_id": "ue-1", "resource_block_ids": ["rb-1-0", "rb-1-1"]}],
            },
        )

    def test_max_cqi_always_picks_the_same_tie_broken_ue(self):
        result = run(self.scenario, MaxCQI())
        trace = decisions_trace(result.decisions)
        self.assertEqual(
            trace,
            {
                0: [{"ue_id": "ue-0", "resource_block_ids": ["rb-0-0", "rb-0-1"]}],
                1: [{"ue_id": "ue-0", "resource_block_ids": ["rb-1-0", "rb-1-1"]}],
            },
        )


class CQIDifferenceOracleTests(unittest.TestCase):
    """Hand-traced expected decisions for `cqi_difference`: one Resource
    Block, one TTI, cold-start, CQI differs (ue-0=3, ue-1=12)."""

    def setUp(self):
        self.scenario = _scenario("cqi_difference")

    def test_round_robin_picks_first_in_rotation_ignoring_cqi(self):
        result = run(self.scenario, RoundRobin())
        trace = decisions_trace(result.decisions)
        self.assertEqual(
            trace, {0: [{"ue_id": "ue-0", "resource_block_ids": ["rb-0-0"]}]}
        )

    def test_proportional_fair_at_cold_start_picks_by_tie_break_not_cqi(self):
        result = run(self.scenario, ProportionalFair())
        trace = decisions_trace(result.decisions)
        self.assertEqual(
            trace, {0: [{"ue_id": "ue-0", "resource_block_ids": ["rb-0-0"]}]}
        )

    def test_max_cqi_picks_the_higher_cqi_ue(self):
        result = run(self.scenario, MaxCQI())
        trace = decisions_trace(result.decisions)
        self.assertEqual(
            trace, {0: [{"ue_id": "ue-1", "resource_block_ids": ["rb-0-0"]}]}
        )


class NoEligibilityOrResourcesOracleTests(unittest.TestCase):
    """`no_eligibility_or_resources` must yield zero decisions for every
    reference implementation, in both boundary conditions (no eligible UE
    despite an available Resource Block; no Resource Block despite
    eligible UEs), without raising."""

    def setUp(self):
        self.scenario = _scenario("no_eligibility_or_resources")

    def test_all_three_algorithms_produce_no_decisions(self):
        for algorithm in (RoundRobin(), ProportionalFair(), MaxCQI()):
            with self.subTest(algorithm=type(algorithm).__name__):
                result = run(self.scenario, algorithm)
                self.assertEqual(result.decisions, ())


class RunDemoOrchestrationTests(unittest.TestCase):
    """`run_demo()` must exercise every (scenario, algorithm) pair exactly
    once and never raise — it is pure orchestration over already-tested
    APIs, not a re-implementation of scheduling or benchmarking logic."""

    def test_produces_one_result_per_scenario_algorithm_pair(self):
        results = run_demo(benchmark_repetitions=1)
        scenarios = build_demo_scenarios()
        algorithms = default_algorithms()
        self.assertEqual(len(results), len(scenarios) * len(algorithms))

        seen = {(r.scenario_id, r.scheduler_name) for r in results}
        expected = {
            (s.scenario_id, spec.scheduler.name)
            for s in scenarios
            for spec in algorithms
        }
        self.assertEqual(seen, expected)

    def test_each_result_carries_its_own_benchmark_samples(self):
        results = run_demo(benchmark_repetitions=1)
        for result in results:
            self.assertEqual(len(result.benchmark.samples), 1)


if __name__ == "__main__":
    unittest.main()
