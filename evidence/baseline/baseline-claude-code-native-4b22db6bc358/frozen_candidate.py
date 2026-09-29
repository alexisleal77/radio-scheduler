from radio_scheduler.domain import AllocationDecision
from radio_scheduler.scheduling_interface import (
    EmptySchedulerState,
    ObservableState,
    SchedulingStepResult,
)


class MaxCqiCandidate:
    """Memory-less Max-CQI scheduling algorithm.

    Every Resource Block in a TTI is assigned to the eligible UE with the
    highest Channel Quality Indicator (ties broken by each UE's position in
    `observable_state.ues`, the canonical order). A UE is eligible for a TTI
    only if it has a Buffer entry in ObservableState with
    occupancy_bytes > 0; a UE with no Buffer entry, or with
    occupancy_bytes == 0, never receives a Resource Block. A UE with no
    ChannelQuality entry is treated as having no signal and is therefore
    never selected while any eligible UE with a reported CQI remains.

    No hidden mutable state: this object holds no instance attributes.
    EmptySchedulerState is threaded explicitly through
    initial_state()/allocate() (ADR-008), since Max-CQI needs no memory
    across TTIs.
    """

    def initial_state(self) -> EmptySchedulerState:
        return EmptySchedulerState()

    def allocate(
        self,
        observable_state: ObservableState,
        scheduler_state: EmptySchedulerState,
    ) -> SchedulingStepResult[EmptySchedulerState]:
        if not observable_state.ues or not observable_state.resource_blocks:
            return SchedulingStepResult(decisions=(), scheduler_state=scheduler_state)

        eligible_ue_ids = {
            buffer.ue_id
            for buffer in observable_state.buffers
            if buffer.occupancy_bytes > 0
        }
        if not eligible_ue_ids:
            return SchedulingStepResult(decisions=(), scheduler_state=scheduler_state)

        cqi_by_ue_id = {
            channel_quality.ue_id: channel_quality.cqi
            for channel_quality in observable_state.channel_qualities
        }
        ue_rank = {ue.ue_id: index for index, ue in enumerate(observable_state.ues)}

        best_ue_id = min(
            eligible_ue_ids,
            key=lambda ue_id: (-cqi_by_ue_id.get(ue_id, 0), ue_rank[ue_id]),
        )

        decisions = (
            AllocationDecision(
                tti=observable_state.tti,
                ue_id=best_ue_id,
                resource_block_ids=tuple(
                    rb.block_id for rb in observable_state.resource_blocks
                ),
            ),
        )
        return SchedulingStepResult(decisions=decisions, scheduler_state=scheduler_state)


def build_algorithm() -> MaxCqiCandidate:
    return MaxCqiCandidate()
