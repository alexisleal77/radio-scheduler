import unittest

from radio_scheduler.domain import TTI, UE, Buffer, ChannelQuality, QoSClass, ResourceBlock
from radio_scheduler.reference_implementations.max_cqi import MaxCQI
from radio_scheduler.reference_implementations.proportional_fair import (
    ProportionalFair,
    ProportionalFairState,
)
from radio_scheduler.reference_implementations.round_robin import RoundRobin
from radio_scheduler.scheduling_interface import EmptySchedulerState, ObservableState


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


class MaxCQIBasicAllocationTests(unittest.TestCase):
    def test_selects_ue_with_highest_cqi(self):
        algo = MaxCQI()
        state = make_state(
            ue_ids=("ue-0", "ue-1", "ue-2"),
            cqi_by_ue_id={"ue-0": 5, "ue-1": 15, "ue-2": 9},
            num_resource_blocks=1,
        )
        result = algo.allocate(state, algo.initial_state())
        self.assertEqual(decisions_by_ue(result.decisions), {"ue-1": ("rb-0",)})

    def test_ignores_prior_state_entirely(self):
        # MaxCQI is memory-less: identical results regardless of what
        # "previous" state is threaded in.
        algo = MaxCQI()
        state = make_state(
            ue_ids=("ue-0", "ue-1"),
            cqi_by_ue_id={"ue-0": 5, "ue-1": 15},
            num_resource_blocks=1,
        )
        result = algo.allocate(state, EmptySchedulerState())
        self.assertEqual(decisions_by_ue(result.decisions), {"ue-1": ("rb-0",)})


class MaxCQIEligibilityTests(unittest.TestCase):
    def test_ue_without_channel_quality_entry_is_ineligible(self):
        algo = MaxCQI()
        state = make_state(
            ue_ids=("ue-0", "ue-1"),
            cqi_by_ue_id={"ue-1": 5},
            no_cqi_ue_ids=("ue-0",),
        )
        result = algo.allocate(state, algo.initial_state())
        self.assertEqual(decisions_by_ue(result.decisions), {"ue-1": ("rb-0", "rb-1")})

    def test_ue_with_cqi_zero_is_ineligible(self):
        algo = MaxCQI()
        state = make_state(ue_ids=("ue-0", "ue-1"), cqi_by_ue_id={"ue-0": 0, "ue-1": 5})
        result = algo.allocate(state, algo.initial_state())
        self.assertEqual(decisions_by_ue(result.decisions), {"ue-1": ("rb-0", "rb-1")})

    def test_ue_with_positive_cqi_but_empty_buffer_is_ineligible(self):
        algo = MaxCQI()
        state = make_state(
            ue_ids=("ue-0", "ue-1"),
            cqi_by_ue_id={"ue-0": 15, "ue-1": 5},
            eligible_ue_ids={"ue-1"},
        )
        result = algo.allocate(state, algo.initial_state())
        self.assertEqual(decisions_by_ue(result.decisions), {"ue-1": ("rb-0", "rb-1")})

    def test_ue_without_buffer_entry_is_ineligible(self):
        algo = MaxCQI()
        state = make_state(
            ue_ids=("ue-0", "ue-1"),
            cqi_by_ue_id={"ue-0": 15, "ue-1": 5},
            no_buffer_ue_ids=("ue-0",),
        )
        result = algo.allocate(state, algo.initial_state())
        self.assertEqual(decisions_by_ue(result.decisions), {"ue-1": ("rb-0", "rb-1")})

    def test_no_eligible_ues_returns_zero_decisions(self):
        algo = MaxCQI()
        state = make_state(
            ue_ids=("ue-0", "ue-1"),
            cqi_by_ue_id={"ue-0": 0, "ue-1": 0},
        )
        result = algo.allocate(state, algo.initial_state())
        self.assertEqual(result.decisions, ())

    def test_no_resource_blocks_returns_zero_decisions(self):
        algo = MaxCQI()
        state = make_state(ue_ids=("ue-0", "ue-1"), num_resource_blocks=0)
        result = algo.allocate(state, algo.initial_state())
        self.assertEqual(result.decisions, ())


class MaxCQITieBreakTests(unittest.TestCase):
    def test_tied_max_cqi_breaks_by_canonical_ues_order(self):
        algo = MaxCQI()
        state = make_state(
            ue_ids=("ue-1", "ue-0", "ue-2"),
            cqi_by_ue_id={"ue-1": 12, "ue-0": 12, "ue-2": 3},
            num_resource_blocks=1,
        )
        result = algo.allocate(state, algo.initial_state())
        self.assertEqual(decisions_by_ue(result.decisions), {"ue-1": ("rb-0",)})

    def test_tie_break_follows_ues_list_order_not_lexicographic_ue_id(self):
        # "ue-10" sorts lexicographically before "ue-2" as a string; the
        # canonical order must still be list order (ue-2 first).
        algo = MaxCQI()
        state = make_state(
            ue_ids=("ue-2", "ue-10"),
            cqi_by_ue_id={"ue-2": 8, "ue-10": 8},
            num_resource_blocks=1,
        )
        result = algo.allocate(state, algo.initial_state())
        self.assertEqual(decisions_by_ue(result.decisions), {"ue-2": ("rb-0",)})


class MaxCQIMultipleResourceBlocksTests(unittest.TestCase):
    def test_selected_ue_receives_every_resource_block(self):
        algo = MaxCQI()
        state = make_state(
            ue_ids=("ue-0", "ue-1"),
            cqi_by_ue_id={"ue-0": 4, "ue-1": 15},
            num_resource_blocks=5,
        )
        result = algo.allocate(state, algo.initial_state())
        self.assertEqual(
            decisions_by_ue(result.decisions),
            {"ue-1": ("rb-0", "rb-1", "rb-2", "rb-3", "rb-4")},
        )

    def test_one_allocation_decision_regardless_of_resource_block_count(self):
        algo = MaxCQI()
        state = make_state(ue_ids=("ue-0", "ue-1", "ue-2"), num_resource_blocks=4)
        result = algo.allocate(state, algo.initial_state())
        self.assertEqual(len(result.decisions), 1)


class MaxCQIStateAndPurityTests(unittest.TestCase):
    def test_initial_state_is_empty_scheduler_state(self):
        self.assertEqual(MaxCQI().initial_state(), EmptySchedulerState())

    def test_state_is_returned_unchanged(self):
        algo = MaxCQI()
        state = make_state(ue_ids=("ue-0", "ue-1"), num_resource_blocks=2)
        previous_state = EmptySchedulerState()
        result = algo.allocate(state, previous_state)
        self.assertIs(result.scheduler_state, previous_state)

    def test_algorithm_holds_no_hidden_state(self):
        algo = MaxCQI()
        self.assertEqual(vars(algo), {})
        state = make_state(ue_ids=("ue-0", "ue-1"), num_resource_blocks=2)
        algo.allocate(state, algo.initial_state())
        self.assertEqual(vars(algo), {})

    def test_repeated_calls_with_same_inputs_are_structurally_equal(self):
        algo = MaxCQI()
        state = make_state(
            ue_ids=("ue-0", "ue-1", "ue-2"),
            cqi_by_ue_id={"ue-0": 5, "ue-1": 9, "ue-2": 3},
            num_resource_blocks=4,
        )
        scheduler_state = EmptySchedulerState()
        result_a = algo.allocate(state, scheduler_state)
        result_b = algo.allocate(state, scheduler_state)
        self.assertEqual(result_a, result_b)


class ReferenceImplementationsPublicApiTests(unittest.TestCase):
    def test_max_cqi_importable_from_package_root(self):
        from radio_scheduler.reference_implementations import MaxCQI

        algo = MaxCQI()
        state = algo.initial_state()
        self.assertIsInstance(state, EmptySchedulerState)


class MaxCQIDifferentiationTests(unittest.TestCase):
    """Cross-algorithm tests: the same ObservableState(s) fed through
    MaxCQI, RoundRobin, and ProportionalFair produce different decisions,
    demonstrating each algorithm's distinct selection logic rather than
    merely asserting each in isolation."""

    def test_max_cqi_never_rotates_unlike_round_robin(self):
        # ue-0 has permanently the best channel; ue-1 is permanently worse
        # but still has demand every TTI.
        max_cqi = MaxCQI()
        round_robin = RoundRobin()
        max_cqi_state = max_cqi.initial_state()
        round_robin_state = round_robin.initial_state()

        max_cqi_served = set()
        round_robin_served = set()
        for tti in range(5):
            state = make_state(
                tti_index=tti,
                ue_ids=("ue-0", "ue-1"),
                cqi_by_ue_id={"ue-0": 15, "ue-1": 3},
                num_resource_blocks=1,
            )
            max_cqi_result = max_cqi.allocate(state, max_cqi_state)
            max_cqi_state = max_cqi_result.scheduler_state
            max_cqi_served.update(decisions_by_ue(max_cqi_result.decisions))

            round_robin_result = round_robin.allocate(state, round_robin_state)
            round_robin_state = round_robin_result.scheduler_state
            round_robin_served.update(decisions_by_ue(round_robin_result.decisions))

        # MaxCQI starves ue-1 entirely; RoundRobin alternates regardless of CQI.
        self.assertEqual(max_cqi_served, {"ue-0"})
        self.assertEqual(round_robin_served, {"ue-0", "ue-1"})

    def test_round_robin_serves_zero_cqi_ue_that_max_cqi_excludes(self):
        # ue-0 has cqi=0 (no usable channel reading) but has demand.
        state = make_state(
            ue_ids=("ue-0", "ue-1"),
            cqi_by_ue_id={"ue-0": 0, "ue-1": 9},
            num_resource_blocks=1,
        )

        max_cqi_result = MaxCQI().allocate(state, MaxCQI().initial_state())
        self.assertEqual(decisions_by_ue(max_cqi_result.decisions), {"ue-1": ("rb-0",)})

        round_robin_result = RoundRobin().allocate(state, RoundRobin().initial_state())
        self.assertEqual(
            decisions_by_ue(round_robin_result.decisions), {"ue-0": ("rb-0",)}
        )

    def test_max_cqi_ignores_fairness_history_unlike_proportional_fair(self):
        # ue-0 has a strong but already-heavily-served history; ue-1 has a
        # weaker channel but has never been served (average == 0).
        state = make_state(
            ue_ids=("ue-0", "ue-1"),
            cqi_by_ue_id={"ue-0": 15, "ue-1": 4},
            num_resource_blocks=1,
        )

        max_cqi_result = MaxCQI().allocate(state, MaxCQI().initial_state())
        self.assertEqual(decisions_by_ue(max_cqi_result.decisions), {"ue-0": ("rb-0",)})

        pf_previous_state = ProportionalFairState(
            average_throughput=(("ue-0", 15.0), ("ue-1", 0.0))
        )
        pf_result = ProportionalFair().allocate(state, pf_previous_state)
        # score(ue-0) = 15/15 = 1.0, score(ue-1) = +inf (never served) -> ue-1 wins.
        self.assertEqual(decisions_by_ue(pf_result.decisions), {"ue-1": ("rb-0",)})


if __name__ == "__main__":
    unittest.main()
