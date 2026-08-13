import unittest
from dataclasses import FrozenInstanceError, dataclass, fields

from radio_scheduler.domain import (
    TTI,
    UE,
    AllocationDecision,
    Buffer,
    ChannelQuality,
    HARQState,
    QoSClass,
    ResourceBlock,
)
from radio_scheduler.scheduling_interface.observable_state import ObservableState
from radio_scheduler.scheduling_interface.scheduling_algorithm import (
    EmptySchedulerState,
    SchedulingStepResult,
)


def make_ues(n=2):
    return tuple(UE(ue_id=f"ue-{i}", qos_class=QoSClass(name="GBR")) for i in range(n))


def make_observable_state(**overrides):
    tti = TTI(index=0)
    ues = make_ues(2)
    defaults = dict(
        tti=tti,
        ues=ues,
        resource_blocks=tuple(
            ResourceBlock(tti=tti, block_id=f"rb-0-{i}") for i in range(2)
        ),
        channel_qualities=tuple(
            ChannelQuality(tti=tti, ue_id=ue.ue_id, cqi=10) for ue in ues
        ),
        buffers=tuple(
            Buffer(tti=tti, ue_id=ue.ue_id, occupancy_bytes=100) for ue in ues
        ),
        harq_states=tuple(
            HARQState(tti=tti, ue_id=ue.ue_id, retransmission_pending=False)
            for ue in ues
        ),
    )
    defaults.update(overrides)
    return ObservableState(**defaults)


# Fixtures defined only within this test file — not reference implementations.
# Their classes intentionally do not inherit from SchedulingAlgorithm: passing
# them wherever a SchedulingAlgorithm is expected exercises structural (duck
# -typed) conformance, since the Protocol is not runtime_checkable (ADR-008).


@dataclass(frozen=True)
class CounterState:
    """Minimal concrete scheduler state, used only to test explicit state
    threading — not a reference implementation."""

    count: int


class CounterAlgorithm:
    """Minimal SchedulingAlgorithm-shaped object with a trivial counter
    state, used only to test explicit state threading."""

    def initial_state(self) -> CounterState:
        return CounterState(count=0)

    def allocate(self, observable_state, scheduler_state):
        new_state = CounterState(count=scheduler_state.count + 1)
        decisions = tuple(
            AllocationDecision(
                tti=observable_state.tti, ue_id=ue.ue_id, resource_block_ids=()
            )
            for ue in observable_state.ues
        )
        return SchedulingStepResult(decisions=decisions, scheduler_state=new_state)


class NoMemoryAlgorithm:
    """Minimal stateless SchedulingAlgorithm-shaped object, used only to
    test EmptySchedulerState usage."""

    def initial_state(self) -> EmptySchedulerState:
        return EmptySchedulerState()

    def allocate(self, observable_state, scheduler_state):
        return SchedulingStepResult(decisions=(), scheduler_state=scheduler_state)


class ObservableStateConstructionTests(unittest.TestCase):
    def test_valid_construction(self):
        state = make_observable_state()
        self.assertEqual(state.tti, TTI(index=0))
        self.assertEqual(len(state.ues), 2)
        self.assertEqual(len(state.resource_blocks), 2)
        self.assertEqual(len(state.channel_qualities), 2)
        self.assertEqual(len(state.buffers), 2)
        self.assertEqual(len(state.harq_states), 2)

    def test_collections_are_tuples(self):
        state = make_observable_state()
        for collection in (
            state.ues,
            state.resource_blocks,
            state.channel_qualities,
            state.buffers,
            state.harq_states,
        ):
            self.assertIsInstance(collection, tuple)

    def test_is_immutable(self):
        state = make_observable_state()
        with self.assertRaises(FrozenInstanceError):
            state.tti = TTI(index=99)


class ObservableStateTemporalScopeTests(unittest.TestCase):
    def test_rejects_resource_block_from_other_tti(self):
        with self.assertRaises(ValueError):
            make_observable_state(
                resource_blocks=(ResourceBlock(tti=TTI(index=1), block_id="rb-1-0"),)
            )

    def test_rejects_channel_quality_from_other_tti(self):
        with self.assertRaises(ValueError):
            make_observable_state(
                channel_qualities=(
                    ChannelQuality(tti=TTI(index=1), ue_id="ue-0", cqi=5),
                )
            )

    def test_rejects_buffer_from_other_tti(self):
        with self.assertRaises(ValueError):
            make_observable_state(
                buffers=(Buffer(tti=TTI(index=1), ue_id="ue-0", occupancy_bytes=10),)
            )

    def test_rejects_harq_state_from_other_tti(self):
        with self.assertRaises(ValueError):
            make_observable_state(
                harq_states=(
                    HARQState(
                        tti=TTI(index=1), ue_id="ue-0", retransmission_pending=False
                    ),
                )
            )


class ObservableStateUeReferenceTests(unittest.TestCase):
    def test_rejects_channel_quality_with_unknown_ue_id(self):
        with self.assertRaises(ValueError):
            make_observable_state(
                channel_qualities=(
                    ChannelQuality(tti=TTI(index=0), ue_id="ue-999", cqi=5),
                )
            )

    def test_rejects_buffer_with_unknown_ue_id(self):
        with self.assertRaises(ValueError):
            make_observable_state(
                buffers=(Buffer(tti=TTI(index=0), ue_id="ue-999", occupancy_bytes=10),)
            )

    def test_rejects_harq_state_with_unknown_ue_id(self):
        with self.assertRaises(ValueError):
            make_observable_state(
                harq_states=(
                    HARQState(
                        tti=TTI(index=0), ue_id="ue-999", retransmission_pending=False
                    ),
                )
            )


class ObservableStateUniquenessTests(unittest.TestCase):
    def test_rejects_duplicate_ue_id(self):
        with self.assertRaises(ValueError):
            make_observable_state(
                ues=(
                    UE(ue_id="ue-0", qos_class=QoSClass(name="GBR")),
                    UE(ue_id="ue-0", qos_class=QoSClass(name="Voice")),
                ),
                channel_qualities=(),
                buffers=(),
                harq_states=(),
            )

    def test_rejects_duplicate_block_id(self):
        tti = TTI(index=0)
        with self.assertRaises(ValueError):
            make_observable_state(
                resource_blocks=(
                    ResourceBlock(tti=tti, block_id="rb-0-0"),
                    ResourceBlock(tti=tti, block_id="rb-0-0"),
                )
            )

    def test_rejects_duplicate_channel_quality_for_same_ue(self):
        tti = TTI(index=0)
        with self.assertRaises(ValueError):
            make_observable_state(
                channel_qualities=(
                    ChannelQuality(tti=tti, ue_id="ue-0", cqi=5),
                    ChannelQuality(tti=tti, ue_id="ue-0", cqi=9),
                )
            )

    def test_rejects_duplicate_buffer_for_same_ue(self):
        tti = TTI(index=0)
        with self.assertRaises(ValueError):
            make_observable_state(
                buffers=(
                    Buffer(tti=tti, ue_id="ue-0", occupancy_bytes=10),
                    Buffer(tti=tti, ue_id="ue-0", occupancy_bytes=20),
                )
            )

    def test_rejects_duplicate_harq_state_for_same_ue(self):
        tti = TTI(index=0)
        with self.assertRaises(ValueError):
            make_observable_state(
                harq_states=(
                    HARQState(tti=tti, ue_id="ue-0", retransmission_pending=True),
                    HARQState(tti=tti, ue_id="ue-0", retransmission_pending=False),
                )
            )


class ObservableStateAllowedAbsenceTests(unittest.TestCase):
    def test_accepts_empty_collections(self):
        state = ObservableState(
            tti=TTI(index=0),
            ues=(),
            resource_blocks=(),
            channel_qualities=(),
            buffers=(),
            harq_states=(),
        )
        self.assertEqual(state.ues, ())
        self.assertEqual(state.resource_blocks, ())
        self.assertEqual(state.channel_qualities, ())
        self.assertEqual(state.buffers, ())
        self.assertEqual(state.harq_states, ())

    def test_accepts_ue_without_channel_quality_buffer_or_harq_state(self):
        # No completeness policy is asserted here: a UE with none of these
        # records is valid, and this test does not require the opposite.
        tti = TTI(index=0)
        ue = UE(ue_id="ue-0", qos_class=QoSClass(name="GBR"))
        state = ObservableState(
            tti=tti,
            ues=(ue,),
            resource_blocks=(),
            channel_qualities=(),
            buffers=(),
            harq_states=(),
        )
        self.assertEqual(state.ues, (ue,))


class EmptySchedulerStateTests(unittest.TestCase):
    def test_explicit_construction(self):
        state = EmptySchedulerState()
        self.assertIsInstance(state, EmptySchedulerState)

    def test_structural_equality(self):
        self.assertEqual(EmptySchedulerState(), EmptySchedulerState())

    def test_is_immutable(self):
        state = EmptySchedulerState()
        with self.assertRaises(FrozenInstanceError):
            state.x = 1  # type: ignore[attr-defined]

    def test_has_no_fields(self):
        self.assertEqual(fields(EmptySchedulerState), ())


class SchedulingStepResultTests(unittest.TestCase):
    def test_accepts_zero_decisions(self):
        result = SchedulingStepResult(decisions=(), scheduler_state=EmptySchedulerState())
        self.assertEqual(result.decisions, ())

    def test_accepts_multiple_allocation_decisions(self):
        tti = TTI(index=0)
        decisions = (
            AllocationDecision(tti=tti, ue_id="ue-0", resource_block_ids=("rb-0-0",)),
            AllocationDecision(tti=tti, ue_id="ue-1", resource_block_ids=("rb-0-1",)),
        )
        result = SchedulingStepResult(
            decisions=decisions, scheduler_state=EmptySchedulerState()
        )
        self.assertEqual(result.decisions, decisions)

    def test_decisions_field_is_tuple(self):
        result = SchedulingStepResult(decisions=(), scheduler_state=EmptySchedulerState())
        self.assertIsInstance(result.decisions, tuple)

    def test_carries_concrete_scheduler_state_type(self):
        state = CounterState(count=7)
        result = SchedulingStepResult(decisions=(), scheduler_state=state)
        self.assertIs(result.scheduler_state, state)
        self.assertIsInstance(result.scheduler_state, CounterState)

    def test_is_immutable(self):
        result = SchedulingStepResult(decisions=(), scheduler_state=EmptySchedulerState())
        with self.assertRaises(FrozenInstanceError):
            result.decisions = ()

    def test_does_not_enforce_allocation_policy(self):
        # Multiple decisions for the same UE, and partial Resource Block
        # coverage, are both structurally valid — no policy is asserted.
        tti = TTI(index=0)
        decisions = (
            AllocationDecision(tti=tti, ue_id="ue-0", resource_block_ids=("rb-0-0",)),
            AllocationDecision(tti=tti, ue_id="ue-0", resource_block_ids=("rb-0-1",)),
        )
        result = SchedulingStepResult(
            decisions=decisions, scheduler_state=EmptySchedulerState()
        )
        self.assertEqual(len(result.decisions), 2)


class ExplicitChainedStateTests(unittest.TestCase):
    def test_algorithm_object_gains_no_mutable_state(self):
        algo = CounterAlgorithm()
        self.assertEqual(vars(algo), {})
        obs = make_observable_state()
        algo.allocate(obs, algo.initial_state())
        self.assertEqual(vars(algo), {})

    def test_previous_state_is_not_mutated(self):
        algo = CounterAlgorithm()
        obs = make_observable_state()
        state0 = algo.initial_state()
        algo.allocate(obs, state0)
        self.assertEqual(state0, CounterState(count=0))

    def test_new_state_is_returned_explicitly_in_step_result(self):
        algo = CounterAlgorithm()
        obs = make_observable_state()
        result = algo.allocate(obs, algo.initial_state())
        self.assertIsInstance(result, SchedulingStepResult)
        self.assertEqual(result.scheduler_state, CounterState(count=1))

    def test_two_chained_calls_produce_successive_states(self):
        algo = CounterAlgorithm()
        obs = make_observable_state()
        state0 = algo.initial_state()
        result1 = algo.allocate(obs, state0)
        result2 = algo.allocate(obs, result1.scheduler_state)
        self.assertEqual(result1.scheduler_state, CounterState(count=1))
        self.assertEqual(result2.scheduler_state, CounterState(count=2))

    def test_repeated_calls_with_same_inputs_are_structurally_equal(self):
        algo = CounterAlgorithm()
        obs = make_observable_state()
        state0 = algo.initial_state()
        result_a = algo.allocate(obs, state0)
        result_b = algo.allocate(obs, state0)
        self.assertEqual(result_a, result_b)


class StatelessAlgorithmTests(unittest.TestCase):
    def test_zero_decisions_accepted(self):
        algo = NoMemoryAlgorithm()
        obs = make_observable_state()
        result = algo.allocate(obs, algo.initial_state())
        self.assertEqual(result.decisions, ())

    def test_empty_state_remains_explicit(self):
        algo = NoMemoryAlgorithm()
        state0 = algo.initial_state()
        self.assertIsInstance(state0, EmptySchedulerState)
        obs = make_observable_state()
        result = algo.allocate(obs, state0)
        self.assertIsInstance(result.scheduler_state, EmptySchedulerState)
        self.assertEqual(result.scheduler_state, state0)


if __name__ == "__main__":
    unittest.main()
