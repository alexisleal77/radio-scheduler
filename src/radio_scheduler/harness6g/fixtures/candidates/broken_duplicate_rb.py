"""Demo/replay fixture: a deliberately broken candidate that assigns the
same Resource Block to two different UEs within one TTI — a direct
contract violation that `simulation_loop.run()` must reject (ADR-009's
decision validation). Used to demonstrate HARNESS6G actually rejecting a
bad candidate (interface_conformance fails with the exception raised by
the simulation loop), not only accepting good ones.
"""

from radio_scheduler.domain import AllocationDecision
from radio_scheduler.scheduling_interface import EmptySchedulerState, SchedulingStepResult


class DuplicateResourceBlock:
    def initial_state(self):
        return EmptySchedulerState()

    def allocate(self, observable_state, scheduler_state):
        if not observable_state.resource_blocks or not observable_state.ues:
            return SchedulingStepResult(decisions=(), scheduler_state=scheduler_state)

        block_id = observable_state.resource_blocks[0].block_id
        decisions = tuple(
            AllocationDecision(
                tti=observable_state.tti,
                ue_id=ue.ue_id,
                resource_block_ids=(block_id,),
            )
            for ue in observable_state.ues[:2]
        )
        return SchedulingStepResult(decisions=decisions, scheduler_state=scheduler_state)


def build_algorithm():
    return DuplicateResourceBlock()
