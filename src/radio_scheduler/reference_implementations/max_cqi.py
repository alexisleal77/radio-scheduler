from radio_scheduler.domain import AllocationDecision
from radio_scheduler.scheduling_interface import (
    EmptySchedulerState,
    ObservableState,
    SchedulingStepResult,
)


class MaxCQI:
    """Frequency-domain MaxCQI.

    Greedy channel-quality selection: within each TTI, the single eligible
    UE with the highest ChannelQuality.cqi reading takes every Resource
    Block available that TTI. Unlike RoundRobin (rotation) or
    ProportionalFair (fairness-weighted score), MaxCQI carries no memory of
    past TTIs and makes no attempt at fairness — it is named for the CQI
    index it selects on, not for a throughput quantity, since the current
    domain model has no CQI-to-rate conversion (ADR-006).

    Eligibility: a UE is eligible only if it has both a ChannelQuality
    reading with cqi > 0 and a Buffer entry with occupancy_bytes > 0 this
    TTI. A UE missing either — including a UE with no Buffer entry, or no
    ChannelQuality entry, at all — is excluded before comparison, never
    merely coerced to a neutral value.

    Selection: among eligible UEs, the one with the strictly highest cqi
    this TTI. Ties (including no eligible UE having been served before —
    MaxCQI has no such notion) are broken by canonical
    `observable_state.ues` order, the same principle used by RoundRobin and
    ProportionalFair — never by `ue_id` text.

    Because ChannelQuality is frequency-flat in the current domain model
    (one CQI value per UE per TTI, not per Resource Block), there is no
    per-Resource-Block signal to differentiate UEs within a TTI: the single
    selected UE takes every Resource Block available that TTI. This is the
    same honest consequence of v0.1's CQI granularity already accepted for
    ProportionalFair, not a new gap.

    If there are no eligible UEs, or no Resource Blocks are available this
    TTI, this step returns zero decisions.

    No historical state: MaxCQI's decision at a TTI depends only on that
    TTI's ObservableState, so it reuses `EmptySchedulerState` from
    `scheduling_interface` (ADR-008 point 12) rather than defining a
    dedicated, equally-empty state type.

    No hidden mutable state: this object holds no instance attributes.
    """

    def initial_state(self) -> EmptySchedulerState:
        return EmptySchedulerState()

    def allocate(
        self,
        observable_state: ObservableState,
        scheduler_state: EmptySchedulerState,
    ) -> SchedulingStepResult[EmptySchedulerState]:
        cqi_by_ue_id = {cq.ue_id: cq.cqi for cq in observable_state.channel_qualities}
        eligible_ue_ids = {
            buffer.ue_id
            for buffer in observable_state.buffers
            if buffer.occupancy_bytes > 0
        }

        served_ue_id: str | None = None
        if observable_state.resource_blocks:
            best_cqi = 0
            for ue in observable_state.ues:
                if ue.ue_id not in eligible_ue_ids:
                    continue

                cqi = cqi_by_ue_id.get(ue.ue_id, 0)
                if cqi <= 0:
                    continue

                if cqi > best_cqi:
                    best_cqi = cqi
                    served_ue_id = ue.ue_id

        decisions: tuple[AllocationDecision, ...] = ()
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
