import unittest
from dataclasses import FrozenInstanceError

from radio_scheduler.domain import TTI, UE, Buffer, ChannelQuality, QoSClass, ResourceBlock
from radio_scheduler.reference_implementations.proportional_fair import (
    ProportionalFair,
    ProportionalFairState,
)
from radio_scheduler.scheduling_interface import ObservableState


def make_ue(ue_id):
    return UE(ue_id=ue_id, qos_class=QoSClass(name="GBR"))


def make_state(
    tti_index=0,
    ue_ids=("ue-0", "ue-1", "ue-2"),
    cqi_by_ue_id=None,
    no_cqi_ue_ids=(),
    eligible_ue_ids=None,
    no_buffer_ue_ids=(),
    num_resource_blocks=None,
):
    """ObservableState with UEs in exactly the given order. ChannelQuality
    defaults to cqi=10 for every UE unless overridden by cqi_by_ue_id;
    ue_ids listed in no_cqi_ue_ids get no ChannelQuality entry at all.
    Buffers mark demand (occupancy_bytes=100 if eligible, else 0);
    eligible_ue_ids defaults to every UE having demand; ue_ids listed in
    no_buffer_ue_ids get no Buffer entry at all. Resource Blocks are
    rb-0..rb-{n-1} (defaults to one per UE)."""
    tti = TTI(index=tti_index)
    ues = tuple(make_ue(ue_id) for ue_id in ue_ids)
    if cqi_by_ue_id is None:
        cqi_by_ue_id = {}
    channel_qualities = tuple(
        ChannelQuality(tti=tti, ue_id=ue_id, cqi=cqi_by_ue_id.get(ue_id, 10))
        for ue_id in ue_ids
        if ue_id not in no_cqi_ue_ids
    )
    if eligible_ue_ids is None:
        eligible_ue_ids = set(ue_ids)
    buffers = tuple(
        Buffer(
            tti=tti,
            ue_id=ue_id,
            occupancy_bytes=100 if ue_id in eligible_ue_ids else 0,
        )
        for ue_id in ue_ids
        if ue_id not in no_buffer_ue_ids
    )
    rb_count = len(ue_ids) if num_resource_blocks is None else num_resource_blocks
    resource_blocks = tuple(
        ResourceBlock(tti=tti, block_id=f"rb-{i}") for i in range(rb_count)
    )
    return ObservableState(
        tti=tti,
        ues=ues,
        resource_blocks=resource_blocks,
        channel_qualities=channel_qualities,
        buffers=buffers,
        harq_states=(),
    )


def decisions_by_ue(decisions):
    return {d.ue_id: d.resource_block_ids for d in decisions}


def averages_by_ue(state):
    return dict(state.average_throughput)


class ProportionalFairBasicAllocationTests(unittest.TestCase):
    def test_single_ue_never_served_before_wins_and_takes_all_resource_blocks(self):
        algo = ProportionalFair()
        state = make_state(ue_ids=("ue-0", "ue-1", "ue-2"), num_resource_blocks=3)
        result = algo.allocate(state, algo.initial_state())
        self.assertEqual(
            decisions_by_ue(result.decisions),
            {"ue-0": ("rb-0", "rb-1", "rb-2")},
        )

    def test_all_never_served_ues_tie_break_by_canonical_order(self):
        algo = ProportionalFair()
        state = make_state(ue_ids=("ue-2", "ue-10"), num_resource_blocks=1)
        result = algo.allocate(state, algo.initial_state())
        self.assertEqual(decisions_by_ue(result.decisions), {"ue-2": ("rb-0",)})


class ProportionalFairScoringTests(unittest.TestCase):
    def test_higher_cqi_over_average_ratio_wins(self):
        algo = ProportionalFair()
        state = make_state(
            ue_ids=("ue-0", "ue-1"),
            cqi_by_ue_id={"ue-0": 5, "ue-1": 12},
            num_resource_blocks=1,
        )
        previous_state = ProportionalFairState(
            average_throughput=(("ue-0", 5.0), ("ue-1", 5.0))
        )
        # score(ue-0) = 5/5 = 1.0, score(ue-1) = 12/5 = 2.4 -> ue-1 wins.
        result = algo.allocate(state, previous_state)
        self.assertEqual(decisions_by_ue(result.decisions), {"ue-1": ("rb-0",)})

    def test_lower_average_can_overcome_higher_cqi(self):
        algo = ProportionalFair()
        state = make_state(
            ue_ids=("ue-0", "ue-1"),
            cqi_by_ue_id={"ue-0": 15, "ue-1": 4},
            num_resource_blocks=1,
        )
        previous_state = ProportionalFairState(
            average_throughput=(("ue-0", 15.0), ("ue-1", 1.0))
        )
        # score(ue-0) = 15/15 = 1.0, score(ue-1) = 4/1 = 4.0 -> ue-1 wins.
        result = algo.allocate(state, previous_state)
        self.assertEqual(decisions_by_ue(result.decisions), {"ue-1": ("rb-0",)})


class ProportionalFairEligibilityTests(unittest.TestCase):
    def test_ue_without_channel_quality_entry_is_ineligible(self):
        algo = ProportionalFair()
        state = make_state(ue_ids=("ue-0", "ue-1"), no_cqi_ue_ids=("ue-0",))
        result = algo.allocate(state, algo.initial_state())
        self.assertEqual(decisions_by_ue(result.decisions), {"ue-1": ("rb-0", "rb-1")})

    def test_ue_with_cqi_zero_is_ineligible(self):
        algo = ProportionalFair()
        state = make_state(ue_ids=("ue-0", "ue-1"), cqi_by_ue_id={"ue-0": 0})
        result = algo.allocate(state, algo.initial_state())
        self.assertEqual(decisions_by_ue(result.decisions), {"ue-1": ("rb-0", "rb-1")})

    def test_ue_with_positive_cqi_but_empty_buffer_is_ineligible(self):
        algo = ProportionalFair()
        state = make_state(ue_ids=("ue-0", "ue-1"), eligible_ue_ids={"ue-1"})
        result = algo.allocate(state, algo.initial_state())
        self.assertEqual(decisions_by_ue(result.decisions), {"ue-1": ("rb-0", "rb-1")})

    def test_ue_without_buffer_entry_is_ineligible(self):
        algo = ProportionalFair()
        state = make_state(ue_ids=("ue-0", "ue-1"), no_buffer_ue_ids=("ue-0",))
        result = algo.allocate(state, algo.initial_state())
        self.assertEqual(decisions_by_ue(result.decisions), {"ue-1": ("rb-0", "rb-1")})

    def test_ue_regains_eligibility_after_temporary_loss_of_demand(self):
        algo = ProportionalFair()

        # TTI 0: only ue-0 has demand; it is served.
        state0 = make_state(
            ue_ids=("ue-0", "ue-1"), eligible_ue_ids={"ue-0"}, num_resource_blocks=1
        )
        result0 = algo.allocate(state0, algo.initial_state())
        self.assertEqual(decisions_by_ue(result0.decisions), {"ue-0": ("rb-0",)})

        # TTI 1: ue-1 gains demand and, having a lower (zero) average, wins.
        state1 = make_state(ue_ids=("ue-0", "ue-1"), num_resource_blocks=1)
        result1 = algo.allocate(state1, result0.scheduler_state)
        self.assertEqual(decisions_by_ue(result1.decisions), {"ue-1": ("rb-0",)})

    def test_no_eligible_ues_returns_zero_decisions(self):
        algo = ProportionalFair()
        state = make_state(
            ue_ids=("ue-0", "ue-1"),
            cqi_by_ue_id={"ue-0": 0, "ue-1": 0},
        )
        result = algo.allocate(state, algo.initial_state())
        self.assertEqual(result.decisions, ())

    def test_no_resource_blocks_returns_zero_decisions(self):
        algo = ProportionalFair()
        state = make_state(ue_ids=("ue-0", "ue-1"), num_resource_blocks=0)
        result = algo.allocate(state, algo.initial_state())
        self.assertEqual(result.decisions, ())


class ProportionalFairStateUpdateTests(unittest.TestCase):
    def test_served_ue_average_updates_toward_its_cqi(self):
        algo = ProportionalFair()
        state = make_state(ue_ids=("ue-0",), cqi_by_ue_id={"ue-0": 10})
        previous_state = ProportionalFairState(average_throughput=(("ue-0", 4.0),))
        result = algo.allocate(state, previous_state)
        # new_avg = 0.9 * 4.0 + 0.1 * 10 = 4.6
        self.assertAlmostEqual(averages_by_ue(result.scheduler_state)["ue-0"], 4.6)

    def test_unserved_eligible_ue_average_decays_toward_zero(self):
        algo = ProportionalFair()
        state = make_state(
            ue_ids=("ue-0", "ue-1"), cqi_by_ue_id={"ue-0": 15, "ue-1": 1}
        )
        previous_state = ProportionalFairState(
            average_throughput=(("ue-0", 1.0), ("ue-1", 5.0))
        )
        # ue-0 wins (never mind ue-1); ue-1's average decays: 0.9*5.0 = 4.5
        result = algo.allocate(state, previous_state)
        self.assertAlmostEqual(averages_by_ue(result.scheduler_state)["ue-1"], 4.5)

    def test_all_observed_ues_get_an_average_entry_even_if_ineligible(self):
        algo = ProportionalFair()
        state = make_state(
            ue_ids=("ue-0", "ue-1"), cqi_by_ue_id={"ue-0": 10, "ue-1": 0}
        )
        result = algo.allocate(state, algo.initial_state())
        self.assertEqual(set(averages_by_ue(result.scheduler_state)), {"ue-0", "ue-1"})
        # ue-1 is ineligible (cqi=0) and unserved: average stays 0.
        self.assertAlmostEqual(averages_by_ue(result.scheduler_state)["ue-1"], 0.0)

    def test_state_is_not_left_unchanged_when_no_resource_blocks(self):
        algo = ProportionalFair()
        state = make_state(ue_ids=("ue-0",), cqi_by_ue_id={"ue-0": 10}, num_resource_blocks=0)
        previous_state = ProportionalFairState(average_throughput=(("ue-0", 8.0),))
        result = algo.allocate(state, previous_state)
        # Nobody served this TTI: average still decays toward 0.
        self.assertAlmostEqual(averages_by_ue(result.scheduler_state)["ue-0"], 7.2)

    def test_state_is_not_left_unchanged_when_no_eligible_ues(self):
        algo = ProportionalFair()
        state = make_state(ue_ids=("ue-0",), cqi_by_ue_id={"ue-0": 0})
        previous_state = ProportionalFairState(average_throughput=(("ue-0", 8.0),))
        result = algo.allocate(state, previous_state)
        self.assertAlmostEqual(averages_by_ue(result.scheduler_state)["ue-0"], 7.2)


class ProportionalFairStateAndPurityTests(unittest.TestCase):
    def test_state_is_immutable(self):
        state = ProportionalFairState()
        with self.assertRaises(FrozenInstanceError):
            state.average_throughput = (("ue-0", 1.0),)

    def test_initial_state_has_no_tracked_averages(self):
        self.assertEqual(
            ProportionalFair().initial_state(), ProportionalFairState(average_throughput=())
        )

    def test_algorithm_holds_no_hidden_state(self):
        algo = ProportionalFair()
        self.assertEqual(vars(algo), {})
        state = make_state(ue_ids=("ue-0", "ue-1"), num_resource_blocks=2)
        algo.allocate(state, algo.initial_state())
        self.assertEqual(vars(algo), {})

    def test_repeated_calls_with_same_inputs_are_structurally_equal(self):
        algo = ProportionalFair()
        state = make_state(ue_ids=("ue-0", "ue-1", "ue-2"), num_resource_blocks=4)
        scheduler_state = ProportionalFairState(
            average_throughput=(("ue-0", 3.0), ("ue-1", 6.0))
        )
        result_a = algo.allocate(state, scheduler_state)
        result_b = algo.allocate(state, scheduler_state)
        self.assertEqual(result_a, result_b)


class ReferenceImplementationsPublicApiTests(unittest.TestCase):
    def test_proportional_fair_and_state_importable_from_package_root(self):
        from radio_scheduler.reference_implementations import (
            ProportionalFair,
            ProportionalFairState,
        )

        algo = ProportionalFair()
        state = algo.initial_state()
        self.assertIsInstance(state, ProportionalFairState)


if __name__ == "__main__":
    unittest.main()
