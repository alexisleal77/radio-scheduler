"""Demo/replay fixture: a deliberately simple, correct SchedulingAlgorithm
candidate — NOT a reference implementation, NOT output from a qualified
specialized model. Used only to exercise HARNESS6G's own
materialization/checks/freeze pipeline in replay mode (see
docs/demo.md). Passes every exposed check: it only ever serves an
eligible UE (occupancy_bytes > 0), and returns zero decisions whenever
there is no eligible UE or no Resource Block.
"""

from radio_scheduler.domain import AllocationDecision
from radio_scheduler.scheduling_interface import EmptySchedulerState, SchedulingStepResult


class FirstEligibleUE:
    def initial_state(self):
        return EmptySchedulerState()

    def allocate(self, observable_state, scheduler_state):
        eligible_ue_ids = {
            buffer.ue_id
            for buffer in observable_state.buffers
            if buffer.occupancy_bytes > 0
        }

        served_ue_id = None
        if observable_state.resource_blocks:
            for ue in observable_state.ues:
                if ue.ue_id in eligible_ue_ids:
                    served_ue_id = ue.ue_id
                    break

        decisions: tuple = ()
        if served_ue_id is not None:
            decisions = (
                AllocationDecision(
                    tti=observable_state.tti,
                    ue_id=served_ue_id,
                    resource_block_ids=tuple(
                        rb.block_id for rb in observable_state.resource_blocks
                    ),
                ),
            )
        return SchedulingStepResult(decisions=decisions, scheduler_state=scheduler_state)


def build_algorithm():
    return FirstEligibleUE()
