import unittest
from dataclasses import FrozenInstanceError

from radio_scheduler.domain import TTI, UE, Buffer, QoSClass, ResourceBlock
from radio_scheduler.reference_implementations.round_robin import (
    RoundRobin,
    RoundRobinState,
)
from radio_scheduler.scheduling_interface import ObservableState


def make_ue(ue_id):
    return UE(ue_id=ue_id, qos_class=QoSClass(name="GBR"))


def make_state(
    tti_index=0,
    ue_ids=("ue-0", "ue-1", "ue-2"),
    eligible_ue_ids=None,
    no_buffer_ue_ids=(),
    num_resource_blocks=None,
):
    """ObservableState with UEs in exactly the given order. Buffers mark
    eligibility (occupancy_bytes=100 if eligible, else 0); ue_ids listed in
    no_buffer_ue_ids get no Buffer entry at all. Resource Blocks are
    rb-0..rb-{n-1} (defaults to one per UE)."""
    tti = TTI(index=tti_index)
    ues = tuple(make_ue(ue_id) for ue_id in ue_ids)
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
        channel_qualities=(),
        buffers=buffers,
        harq_states=(),
    )


def decisions_by_ue(decisions):
    return {d.ue_id: d.resource_block_ids for d in decisions}


class RoundRobinBasicRotationTests(unittest.TestCase):
    def test_first_tti_starts_at_first_ue_in_canonical_order(self):
        algo = RoundRobin()
        state = make_state(ue_ids=("ue-0", "ue-1", "ue-2"), num_resource_blocks=3)
        result = algo.allocate(state, algo.initial_state())
        self.assertEqual(
            decisions_by_ue(result.decisions),
            {"ue-0": ("rb-0",), "ue-1": ("rb-1",), "ue-2": ("rb-2",)},
        )
        self.assertEqual(result.scheduler_state, RoundRobinState(last_served_ue_id="ue-2"))

    def test_multiple_resource_blocks_per_ue_when_fewer_eligible_than_blocks(self):
        algo = RoundRobin()
        state = make_state(
            ue_ids=("ue-0", "ue-1", "ue-2"),
            eligible_ue_ids={"ue-0", "ue-1"},
            num_resource_blocks=4,
        )
        result = algo.allocate(state, algo.initial_state())
        self.assertEqual(
            decisions_by_ue(result.decisions),
            {"ue-0": ("rb-0", "rb-2"), "ue-1": ("rb-1", "rb-3")},
        )
        self.assertEqual(result.scheduler_state, RoundRobinState(last_served_ue_id="ue-1"))


class RoundRobinCanonicalOrderTests(unittest.TestCase):
    def test_rotation_follows_ues_list_order_not_lexicographic_ue_id(self):
        # "ue-10" sorts lexicographically before "ue-2" as a string; the
        # canonical order must still be list order (ue-2 first).
        algo = RoundRobin()
        state = make_state(ue_ids=("ue-2", "ue-10"), num_resource_blocks=1)
        result = algo.allocate(state, algo.initial_state())
        self.assertEqual(decisions_by_ue(result.decisions), {"ue-2": ("rb-0",)})


class RoundRobinEligibilityTests(unittest.TestCase):
    def test_ue_without_buffer_entry_is_ineligible(self):
        algo = RoundRobin()
        state = make_state(
            ue_ids=("ue-0", "ue-1"),
            no_buffer_ue_ids=("ue-1",),
            num_resource_blocks=2,
        )
        result = algo.allocate(state, algo.initial_state())
        self.assertEqual(decisions_by_ue(result.decisions), {"ue-0": ("rb-0", "rb-1")})

    def test_temporarily_ineligible_ue_is_skipped_without_resetting_cursor(self):
        algo = RoundRobin()

        # TTI 0: everyone eligible, 4 RBs.
        state0 = make_state(ue_ids=("ue-0", "ue-1", "ue-2"), num_resource_blocks=4)
        result0 = algo.allocate(state0, algo.initial_state())
        self.assertEqual(result0.scheduler_state, RoundRobinState(last_served_ue_id="ue-0"))

        # TTI 1: ue-1 becomes ineligible; 2 RBs.
        state1 = make_state(
            ue_ids=("ue-0", "ue-1", "ue-2"),
            eligible_ue_ids={"ue-0", "ue-2"},
            num_resource_blocks=2,
        )
        result1 = algo.allocate(state1, result0.scheduler_state)
        self.assertEqual(
            decisions_by_ue(result1.decisions), {"ue-2": ("rb-0",), "ue-0": ("rb-1",)}
        )
        self.assertEqual(result1.scheduler_state, RoundRobinState(last_served_ue_id="ue-0"))

        # TTI 2: ue-1 becomes eligible again; 3 RBs. It must be served
        # immediately, at the very next structural opportunity.
        state2 = make_state(ue_ids=("ue-0", "ue-1", "ue-2"), num_resource_blocks=3)
        result2 = algo.allocate(state2, result1.scheduler_state)
        self.assertEqual(
            decisions_by_ue(result2.decisions),
            {"ue-1": ("rb-0",), "ue-2": ("rb-1",), "ue-0": ("rb-2",)},
        )


class RoundRobinCursorResetTests(unittest.TestCase):
    def test_none_state_starts_at_first_ue(self):
        algo = RoundRobin()
        state = make_state(ue_ids=("ue-0", "ue-1"), num_resource_blocks=1)
        result = algo.allocate(state, RoundRobinState(last_served_ue_id=None))
        self.assertEqual(decisions_by_ue(result.decisions), {"ue-0": ("rb-0",)})

    def test_resets_to_first_ue_when_last_served_no_longer_observable(self):
        algo = RoundRobin()
        state = make_state(ue_ids=("ue-0", "ue-1", "ue-2"), num_resource_blocks=1)
        result = algo.allocate(state, RoundRobinState(last_served_ue_id="ue-999"))
        self.assertEqual(decisions_by_ue(result.decisions), {"ue-0": ("rb-0",)})


class RoundRobinEmptyResultTests(unittest.TestCase):
    def test_no_eligible_ues_returns_zero_decisions_and_unchanged_state(self):
        algo = RoundRobin()
        state = make_state(
            ue_ids=("ue-0", "ue-1"), eligible_ue_ids=set(), num_resource_blocks=2
        )
        previous_state = RoundRobinState(last_served_ue_id="ue-0")
        result = algo.allocate(state, previous_state)
        self.assertEqual(result.decisions, ())
        self.assertIs(result.scheduler_state, previous_state)

    def test_no_resource_blocks_returns_zero_decisions_and_unchanged_state(self):
        algo = RoundRobin()
        state = make_state(ue_ids=("ue-0", "ue-1"), num_resource_blocks=0)
        previous_state = RoundRobinState(last_served_ue_id="ue-1")
        result = algo.allocate(state, previous_state)
        self.assertEqual(result.decisions, ())
        self.assertIs(result.scheduler_state, previous_state)


class RoundRobinDecisionShapeTests(unittest.TestCase):
    def test_resource_block_ids_follow_observable_state_order_per_ue(self):
        algo = RoundRobin()
        state = make_state(
            ue_ids=("ue-0", "ue-1"),
            eligible_ue_ids={"ue-0"},
            num_resource_blocks=3,
        )
        result = algo.allocate(state, algo.initial_state())
        self.assertEqual(
            decisions_by_ue(result.decisions), {"ue-0": ("rb-0", "rb-1", "rb-2")}
        )

    def test_one_allocation_decision_per_served_ue(self):
        algo = RoundRobin()
        state = make_state(ue_ids=("ue-0", "ue-1", "ue-2"), num_resource_blocks=3)
        result = algo.allocate(state, algo.initial_state())
        self.assertEqual(len(result.decisions), 3)


class RoundRobinStateAndPurityTests(unittest.TestCase):
    def test_state_is_immutable(self):
        state = RoundRobinState()
        with self.assertRaises(FrozenInstanceError):
            state.last_served_ue_id = "ue-0"

    def test_initial_state_has_no_last_served_ue(self):
        self.assertEqual(RoundRobin().initial_state(), RoundRobinState(last_served_ue_id=None))

    def test_algorithm_holds_no_hidden_state(self):
        algo = RoundRobin()
        self.assertEqual(vars(algo), {})
        state = make_state(ue_ids=("ue-0", "ue-1"), num_resource_blocks=2)
        algo.allocate(state, algo.initial_state())
        self.assertEqual(vars(algo), {})

    def test_repeated_calls_with_same_inputs_are_structurally_equal(self):
        algo = RoundRobin()
        state = make_state(ue_ids=("ue-0", "ue-1", "ue-2"), num_resource_blocks=4)
        scheduler_state = RoundRobinState(last_served_ue_id="ue-1")
        result_a = algo.allocate(state, scheduler_state)
        result_b = algo.allocate(state, scheduler_state)
        self.assertEqual(result_a, result_b)


class ReferenceImplementationsPublicApiTests(unittest.TestCase):
    def test_round_robin_and_state_importable_from_package_root(self):
        from radio_scheduler.reference_implementations import RoundRobin, RoundRobinState

        algo = RoundRobin()
        state = algo.initial_state()
        self.assertIsInstance(state, RoundRobinState)


if __name__ == "__main__":
    unittest.main()
