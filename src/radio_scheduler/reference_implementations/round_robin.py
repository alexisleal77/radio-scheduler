from dataclasses import dataclass

from radio_scheduler.domain import AllocationDecision
from radio_scheduler.scheduling_interface import ObservableState, SchedulingStepResult


@dataclass(frozen=True)
class RoundRobinState:
    """Explicit RoundRobin state (ADR-008): the ue_id that received the last
    Resource Block assigned, or None before any TTI has been served."""

    last_served_ue_id: str | None = None


def _find_next_eligible_index(ue_order, eligible_ue_ids, start_index):
    """First index >= start_index (cyclically) in ue_order whose ue_id is
    eligible, or None if no UE in ue_order is eligible."""
    count = len(ue_order)
    for offset in range(count):
        index = (start_index + offset) % count
        if ue_order[index].ue_id in eligible_ue_ids:
            return index
    return None


class RoundRobin:
    """Frequency-domain Round Robin.

    Within each TTI, Resource Blocks are distributed one at a time, in
    order, cycling through the UEs in `observable_state.ues` — the
    canonical rotation order, taken exactly as given and never re-sorted by
    `ue_id`, so identifier text format never affects fairness (e.g. "ue-10"
    vs "ue-2").

    Eligibility: a UE is eligible for a TTI only if it has a Buffer entry in
    ObservableState with occupancy_bytes > 0; a UE with no Buffer entry is
    treated as ineligible. Only eligible UEs receive Resource Blocks, but
    the rotation still walks past ineligible UEs without serving them.

    Cursor rule: the search for the next Resource Block's UE always resumes
    right after `last_served_ue_id`'s position in `observable_state.ues`,
    provided that UE still exists among the observable UEs — even if that
    UE is currently ineligible itself. The rotation restarts at the first
    UE only when there is no prior state (last_served_ue_id is None) or
    when last_served_ue_id no longer exists among the observable UEs. A
    temporarily ineligible UE is skipped, never causing a restart.

    If there are no eligible UEs, or no Resource Blocks are available this
    TTI, this step returns zero decisions and the state is left unchanged.

    No hidden mutable state: this object holds no instance attributes.
    RoundRobinState is threaded explicitly through
    initial_state()/allocate() (ADR-008).
    """

    def initial_state(self) -> RoundRobinState:
        return RoundRobinState()

    def allocate(
        self, observable_state: ObservableState, scheduler_state: RoundRobinState
    ) -> SchedulingStepResult[RoundRobinState]:
        ue_order = observable_state.ues
        if not ue_order or not observable_state.resource_blocks:
            return SchedulingStepResult(decisions=(), scheduler_state=scheduler_state)

        eligible_ue_ids = {
            buffer.ue_id
            for buffer in observable_state.buffers
            if buffer.occupancy_bytes > 0
        }
        if not eligible_ue_ids:
            return SchedulingStepResult(decisions=(), scheduler_state=scheduler_state)

        last_served_ue_id = scheduler_state.last_served_ue_id
        if last_served_ue_id is None:
            search_start = 0
        else:
            last_served_index = next(
                (
                    index
                    for index, ue in enumerate(ue_order)
                    if ue.ue_id == last_served_ue_id
                ),
                None,
            )
            search_start = (
                0
                if last_served_index is None
                else (last_served_index + 1) % len(ue_order)
            )

        assignments: dict[str, list[str]] = {}
        pointer = search_start
        last_assigned_ue_id = last_served_ue_id
        for resource_block in observable_state.resource_blocks:
            index = _find_next_eligible_index(ue_order, eligible_ue_ids, pointer)
            ue_id = ue_order[index].ue_id
            assignments.setdefault(ue_id, []).append(resource_block.block_id)
            last_assigned_ue_id = ue_id
            pointer = (index + 1) % len(ue_order)

        decisions = tuple(
            AllocationDecision(
                tti=observable_state.tti,
                ue_id=ue_id,
                resource_block_ids=tuple(block_ids),
            )
            for ue_id, block_ids in assignments.items()
        )
        new_state = RoundRobinState(last_served_ue_id=last_assigned_ue_id)
        return SchedulingStepResult(decisions=decisions, scheduler_state=new_state)
