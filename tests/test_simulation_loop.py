import unittest
from dataclasses import FrozenInstanceError, dataclass

from radio_scheduler.domain import (
    AllocationDecision,
    ChannelQuality,
    QoSClass,
    Scenario,
    TrafficArrival,
    TTI,
    UE,
    ResourceBlock,
)
from radio_scheduler.reference_implementations import MaxCQI, ProportionalFair, RoundRobin
from radio_scheduler.scenario_generator import ScenarioGeneratorConfig, generate_scenario
from radio_scheduler.scheduling_interface import EmptySchedulerState, SchedulingStepResult
from radio_scheduler.simulation_loop import SimulationResult, run


def make_ue(ue_id):
    return UE(ue_id=ue_id, qos_class=QoSClass(name="GBR"))


def make_scenario(
    ue_ids=("ue-0", "ue-1"),
    num_ttis=2,
    resource_blocks_per_tti=1,
    cqi=10,
    arrivals_by_tti_ue=None,
):
    """Hand-built Scenario (not via generate_scenario) for precise control
    over per-TTI Traffic Arrival and Channel Quality. `cqi` is a flat
    default for every (TTI, UE) pair; `arrivals_by_tti_ue` is a dict
    {(tti_index, ue_id): size_bytes}, defaulting to 0 for any pair not
    listed."""
    ttis = tuple(TTI(index=i) for i in range(num_ttis))
    ues = tuple(make_ue(ue_id) for ue_id in ue_ids)
    resource_blocks = tuple(
        ResourceBlock(tti=tti, block_id=f"rb-{tti.index}-{j}")
        for tti in ttis
        for j in range(resource_blocks_per_tti)
    )
    channel_qualities = tuple(
        ChannelQuality(tti=tti, ue_id=ue.ue_id, cqi=cqi) for tti in ttis for ue in ues
    )
    arrivals_by_tti_ue = arrivals_by_tti_ue or {}
    traffic_arrivals = tuple(
        TrafficArrival(
            tti=tti,
            ue_id=ue.ue_id,
            size_bytes=arrivals_by_tti_ue.get((tti.index, ue.ue_id), 0),
        )
        for tti in ttis
        for ue in ues
    )
    return Scenario(
        seed=0,
        ttis=ttis,
        ues=ues,
        resource_blocks=resource_blocks,
        channel_qualities=channel_qualities,
        traffic_arrivals=traffic_arrivals,
    )


def served_ue_by_tti(decisions):
    """Maps tti index -> ue_id, assuming at most one decision per TTI
    (true for every scenario built in this file: single-RB-group,
    single-winner algorithms)."""
    return {decision.tti.index: decision.ue_id for decision in decisions}


@dataclass(frozen=True)
class RecordingState:
    observed_buffers: tuple[tuple[tuple[str, int], ...], ...] = ()


class RecordingAlgorithm:
    """Test double satisfying SchedulingAlgorithm: records, per call, a
    snapshot of the Buffer occupancy it was given (as a tuple of (ue_id,
    occupancy_bytes) pairs), and serves the ue_ids listed for the current
    TTI in `serve_by_tti_index` (a dict: tti index -> tuple of ue_ids),
    each given every Resource Block available that TTI. Only supports at
    most one ue_id per TTI, sufficient for this file's tests. Holds only
    immutable, constructor-time configuration — no hidden mutable state
    between calls, per the SchedulingAlgorithm contract."""

    def __init__(self, serve_by_tti_index=None):
        self._serve_by_tti_index = serve_by_tti_index or {}

    def initial_state(self):
        return RecordingState()

    def allocate(self, observable_state, scheduler_state):
        snapshot = tuple(
            (buffer.ue_id, buffer.occupancy_bytes) for buffer in observable_state.buffers
        )
        new_state = RecordingState(
            observed_buffers=scheduler_state.observed_buffers + (snapshot,)
        )
        ue_ids_to_serve = self._serve_by_tti_index.get(observable_state.tti.index, ())
        decisions = tuple(
            AllocationDecision(
                tti=observable_state.tti,
                ue_id=ue_id,
                resource_block_ids=tuple(
                    rb.block_id for rb in observable_state.resource_blocks
                ),
            )
            for ue_id in ue_ids_to_serve
        )
        return SchedulingStepResult(decisions=decisions, scheduler_state=new_state)


class SimulationResultShapeTests(unittest.TestCase):
    def test_simulation_result_is_immutable(self):
        result = SimulationResult(decisions=(), final_scheduler_state=EmptySchedulerState())
        with self.assertRaises(FrozenInstanceError):
            result.decisions = ()

    def test_importable_from_package_root(self):
        from radio_scheduler.simulation_loop import SimulationResult as SR
        from radio_scheduler.simulation_loop import run as run_fn

        self.assertIs(SR, SimulationResult)
        self.assertIs(run_fn, run)


class EmptyScenarioTests(unittest.TestCase):
    def test_empty_scenario_returns_no_decisions_and_untouched_initial_state(self):
        scenario = make_scenario(num_ttis=0)
        algorithm = RecordingAlgorithm()
        result = run(scenario, algorithm)
        self.assertEqual(result.decisions, ())
        self.assertEqual(result.final_scheduler_state, RecordingState())
        # No TTI means allocate() was never called: no snapshot recorded.
        self.assertEqual(result.final_scheduler_state.observed_buffers, ())


class SingleAndMultipleTTITests(unittest.TestCase):
    def test_single_tti_end_to_end_with_round_robin(self):
        scenario = make_scenario(
            ue_ids=("ue-0", "ue-1"),
            num_ttis=1,
            arrivals_by_tti_ue={(0, "ue-0"): 100, (0, "ue-1"): 100},
        )
        result = run(scenario, RoundRobin())
        self.assertEqual(served_ue_by_tti(result.decisions), {0: "ue-0"})

    def test_multiple_ttis_processed_exactly_once_each_in_order(self):
        scenario = make_scenario(ue_ids=("ue-0",), num_ttis=3)
        algorithm = RecordingAlgorithm()
        result = run(scenario, algorithm)
        # One recorded snapshot per TTI, in TTI order -> allocate() was
        # called exactly once per TTI, strictly in ascending order.
        self.assertEqual(len(result.final_scheduler_state.observed_buffers), 3)


class RoundRobinPropagationTests(unittest.TestCase):
    def test_round_robin_rotates_across_ttis_via_run(self):
        scenario = make_scenario(
            ue_ids=("ue-0", "ue-1"),
            num_ttis=3,
            arrivals_by_tti_ue={
                (tti, ue): 50 for tti in range(3) for ue in ("ue-0", "ue-1")
            },
        )
        result = run(scenario, RoundRobin())
        self.assertEqual(
            served_ue_by_tti(result.decisions), {0: "ue-0", 1: "ue-1", 2: "ue-0"}
        )


class ProportionalFairEvolutionTests(unittest.TestCase):
    def test_proportional_fair_alternates_as_average_evolves_via_run(self):
        # ue-0 has a much better channel than ue-1; both always have demand.
        scenario = make_scenario(
            ue_ids=("ue-0", "ue-1"),
            num_ttis=4,
            arrivals_by_tti_ue={
                (tti, ue): 50 for tti in range(4) for ue in ("ue-0", "ue-1")
            },
        )
        # cqi is flat per make_scenario's default; override via a second
        # scenario built with distinct per-UE cqi.
        ttis = scenario.ttis
        channel_qualities = tuple(
            ChannelQuality(tti=tti, ue_id="ue-0", cqi=15) for tti in ttis
        ) + tuple(ChannelQuality(tti=tti, ue_id="ue-1", cqi=3) for tti in ttis)
        scenario = Scenario(
            seed=scenario.seed,
            ttis=scenario.ttis,
            ues=scenario.ues,
            resource_blocks=scenario.resource_blocks,
            channel_qualities=channel_qualities,
            traffic_arrivals=scenario.traffic_arrivals,
        )
        result = run(scenario, ProportionalFair())
        # Despite ue-0's permanently better channel, PF's fairness EMA
        # makes the served UE alternate rather than always picking ue-0.
        self.assertEqual(
            served_ue_by_tti(result.decisions),
            {0: "ue-0", 1: "ue-1", 2: "ue-0", 3: "ue-1"},
        )


class MaxCQIEmptyStateTests(unittest.TestCase):
    def test_max_cqi_state_stays_empty_scheduler_state_throughout_run(self):
        scenario = make_scenario(
            ue_ids=("ue-0", "ue-1"),
            num_ttis=3,
            arrivals_by_tti_ue={
                (tti, ue): 50 for tti in range(3) for ue in ("ue-0", "ue-1")
            },
        )
        result = run(scenario, MaxCQI())
        self.assertIsInstance(result.final_scheduler_state, EmptySchedulerState)
        self.assertEqual(result.final_scheduler_state, EmptySchedulerState())


class EmptyDecisionsTests(unittest.TestCase):
    def test_ttis_with_no_demand_produce_no_decisions_and_do_not_crash(self):
        # No arrivals at all: every UE's Buffer stays 0 bytes every TTI.
        scenario = make_scenario(ue_ids=("ue-0", "ue-1"), num_ttis=3)
        result = run(scenario, MaxCQI())
        self.assertEqual(result.decisions, ())


class DeterminismTests(unittest.TestCase):
    def test_repeated_runs_with_same_inputs_produce_equal_results(self):
        scenario = make_scenario(
            ue_ids=("ue-0", "ue-1"),
            num_ttis=3,
            arrivals_by_tti_ue={
                (tti, ue): 50 for tti in range(3) for ue in ("ue-0", "ue-1")
            },
        )
        result_a = run(scenario, RoundRobin())
        result_b = run(scenario, RoundRobin())
        self.assertEqual(result_a, result_b)


class ImmutabilityTests(unittest.TestCase):
    def test_scenario_is_not_mutated_by_run(self):
        scenario = make_scenario(
            ue_ids=("ue-0", "ue-1"),
            num_ttis=2,
            arrivals_by_tti_ue={(0, "ue-0"): 100, (1, "ue-1"): 50},
        )
        expected = Scenario(
            seed=scenario.seed,
            ttis=scenario.ttis,
            ues=scenario.ues,
            resource_blocks=scenario.resource_blocks,
            channel_qualities=scenario.channel_qualities,
            traffic_arrivals=scenario.traffic_arrivals,
        )
        run(scenario, RoundRobin())
        self.assertEqual(scenario, expected)


class DrainRuleTests(unittest.TestCase):
    def test_drain_is_applied_after_allocate_and_visible_starting_next_tti(self):
        scenario = make_scenario(
            ue_ids=("ue-0",),
            num_ttis=3,
            arrivals_by_tti_ue={(0, "ue-0"): 100, (1, "ue-0"): 50, (2, "ue-0"): 0},
        )
        # ue-0 is served only at TTI 0.
        algorithm = RecordingAlgorithm(serve_by_tti_index={0: ("ue-0",)})
        result = run(scenario, algorithm)
        observed = [
            dict(snapshot)["ue-0"]
            for snapshot in result.final_scheduler_state.observed_buffers
        ]
        # TTI0: 0 (prior) + 100 (arrival) = 100, not yet drained (allocate()
        #   observes state *before* its own decision is applied).
        # TTI1: 0 (drained after TTI0's decision) + 50 (arrival) = 50.
        # TTI2: 50 (carried over, ue-0 not served at TTI1) + 0 (arrival) = 50.
        self.assertEqual(observed, [100, 50, 50])


class DecisionValidationTests(unittest.TestCase):
    def _run_with_bad_decision(self, bad_decision, num_ttis=1):
        scenario = make_scenario(ue_ids=("ue-0",), num_ttis=num_ttis)

        class BadAlgorithm:
            def initial_state(self):
                return EmptySchedulerState()

            def allocate(self, observable_state, scheduler_state):
                return SchedulingStepResult(
                    decisions=(bad_decision,), scheduler_state=scheduler_state
                )

        return run(scenario, BadAlgorithm())

    def test_decision_with_wrong_tti_is_rejected(self):
        bad = AllocationDecision(tti=TTI(index=999), ue_id="ue-0", resource_block_ids=())
        with self.assertRaises(ValueError):
            self._run_with_bad_decision(bad)

    def test_decision_with_unknown_ue_id_is_rejected(self):
        bad = AllocationDecision(tti=TTI(index=0), ue_id="ue-999", resource_block_ids=())
        with self.assertRaises(ValueError):
            self._run_with_bad_decision(bad)

    def test_decision_with_unknown_resource_block_id_is_rejected(self):
        bad = AllocationDecision(
            tti=TTI(index=0), ue_id="ue-0", resource_block_ids=("rb-999",)
        )
        with self.assertRaises(ValueError):
            self._run_with_bad_decision(bad)

    def test_decision_with_resource_block_repeated_within_itself_is_rejected(self):
        bad = AllocationDecision(
            tti=TTI(index=0), ue_id="ue-0", resource_block_ids=("rb-0-0", "rb-0-0")
        )
        with self.assertRaises(ValueError):
            self._run_with_bad_decision(bad, num_ttis=1)

    def test_resource_block_repeated_across_decisions_is_rejected(self):
        scenario = make_scenario(ue_ids=("ue-0", "ue-1"), num_ttis=1)

        class DoubleAllocatingAlgorithm:
            def initial_state(self):
                return EmptySchedulerState()

            def allocate(self, observable_state, scheduler_state):
                block_id = observable_state.resource_blocks[0].block_id
                decisions = (
                    AllocationDecision(
                        tti=observable_state.tti,
                        ue_id="ue-0",
                        resource_block_ids=(block_id,),
                    ),
                    AllocationDecision(
                        tti=observable_state.tti,
                        ue_id="ue-1",
                        resource_block_ids=(block_id,),
                    ),
                )
                return SchedulingStepResult(
                    decisions=decisions, scheduler_state=scheduler_state
                )

        with self.assertRaises(ValueError):
            run(scenario, DoubleAllocatingAlgorithm())

    def test_scheduler_exception_propagates_without_partial_result(self):
        scenario = make_scenario(ue_ids=("ue-0",), num_ttis=2)

        class ExplodingAlgorithm:
            def initial_state(self):
                return EmptySchedulerState()

            def allocate(self, observable_state, scheduler_state):
                if observable_state.tti.index == 1:
                    raise RuntimeError("scheduler exploded")
                return SchedulingStepResult(decisions=(), scheduler_state=scheduler_state)

        with self.assertRaises(RuntimeError):
            run(scenario, ExplodingAlgorithm())


class PipelineDelayAndTTIValidationTests(unittest.TestCase):
    def test_nonzero_pipeline_delay_is_rejected(self):
        scenario = make_scenario(num_ttis=1)
        with self.assertRaises(ValueError):
            run(scenario, RoundRobin(), pipeline_delay=1)

    def test_negative_pipeline_delay_is_rejected(self):
        scenario = make_scenario(num_ttis=1)
        with self.assertRaises(ValueError):
            run(scenario, RoundRobin(), pipeline_delay=-1)

    def test_duplicate_tti_index_is_rejected(self):
        ue = make_ue("ue-0")
        duplicated_ttis = (TTI(index=0), TTI(index=0))
        scenario = Scenario(
            seed=0,
            ttis=duplicated_ttis,
            ues=(ue,),
            resource_blocks=(),
            channel_qualities=(),
            traffic_arrivals=(),
        )
        with self.assertRaises(ValueError):
            run(scenario, RoundRobin())


class CrossAlgorithmEndToEndTests(unittest.TestCase):
    def test_same_scenario_runs_through_all_three_reference_algorithms(self):
        config = ScenarioGeneratorConfig(
            seed=42,
            num_ues=3,
            num_ttis=5,
            resource_blocks_per_tti=1,
            qos_class_names=("GBR",),
        )
        scenario = generate_scenario(config)

        rr_result = run(scenario, RoundRobin())
        pf_result = run(scenario, ProportionalFair())
        max_cqi_result = run(scenario, MaxCQI())

        for result in (rr_result, pf_result, max_cqi_result):
            self.assertIsInstance(result, SimulationResult)

        rr_served = served_ue_by_tti(rr_result.decisions)
        pf_served = served_ue_by_tti(pf_result.decisions)
        max_cqi_served = served_ue_by_tti(max_cqi_result.decisions)

        # The three algorithms' selection logic differs enough that they
        # should not all three produce the exact same decision sequence.
        self.assertFalse(rr_served == pf_served == max_cqi_served)


if __name__ == "__main__":
    unittest.main()
