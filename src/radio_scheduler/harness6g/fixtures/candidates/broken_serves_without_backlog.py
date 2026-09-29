"""Demo/replay fixture: a deliberately broken candidate that gives every
Resource Block to the first UE in canonical order regardless of whether
that UE has any backlog. It is structurally valid (no duplicate/unknown
ids, so it passes interface_conformance and, on the two scenarios that
happen to have backlog for the first UE throughout, served_ue_must_have
_backlog too) but violates the task's domain rule on
no_eligibility_or_resources (TTI 0: a Resource Block is available but no
UE has backlog — this candidate serves the first UE anyway), caught by
domain_conformance. Demonstrates why a domain-specific check matters
beyond generic interface/contract checks: a bug can pass every generic
check and still be functionally wrong for the actual scheduling task.
"""

from radio_scheduler.domain import AllocationDecision
from radio_scheduler.scheduling_interface import EmptySchedulerState, SchedulingStepResult


class IgnoresBacklog:
    def initial_state(self):
        return EmptySchedulerState()

    def allocate(self, observable_state, scheduler_state):
        if not observable_state.resource_blocks or not observable_state.ues:
            return SchedulingStepResult(decisions=(), scheduler_state=scheduler_state)

        first_ue = observable_state.ues[0]
        decisions = (
            AllocationDecision(
                tti=observable_state.tti,
                ue_id=first_ue.ue_id,
                resource_block_ids=tuple(
                    rb.block_id for rb in observable_state.resource_blocks
                ),
            ),
        )
        return SchedulingStepResult(decisions=decisions, scheduler_state=scheduler_state)


def build_algorithm():
    return IgnoresBacklog()
