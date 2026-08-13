from dataclasses import dataclass

from radio_scheduler.domain import (
    Buffer,
    ChannelQuality,
    HARQState,
    ResourceBlock,
    TTI,
    UE,
)


@dataclass(frozen=True)
class ObservableState:
    """Everything a scheduler may observe at one TTI, and nothing else (ADR-008).

    Buffer already reflects the current TTI's Traffic Arrival: per ADR-002,
    Buffer occupancy at TTI n is "previous occupancy + new arrivals - what
    was successfully transmitted" — the current TTI's arrivals are folded
    into Buffer before it is observable. TrafficArrival for the current TTI
    is therefore deliberately absent here: including it alongside Buffer
    would represent the same quantity twice. TrafficArrival remains a
    Scenario-level (exogenous) concept, consumed only by the Simulation
    Loop when computing the next Buffer, never seen directly by a scheduler.

    HARQState is included because ADR-002 groups it with Buffer as
    "decision-dependent state," updated identically by the Simulation Loop
    and indexed the same way (per TTI, per UE).

    `ues` is the UE set observable/eligible for this step. In v0.1 this is
    the Scenario's full UE set, since the domain model has no notion of
    dynamic UE eligibility yet; the field exists independently so a future,
    narrower eligibility rule would not require reshaping ObservableState.

    Deliberately absent, per ADR-008: any other TTI's data, final
    scheduling-performance metrics, the previous AllocationDecision, the
    Scheduler's identity, the Run, any algorithm-specific internal state,
    and the pipeline delay `d`.
    """

    tti: TTI
    ues: tuple[UE, ...]
    resource_blocks: tuple[ResourceBlock, ...]
    channel_qualities: tuple[ChannelQuality, ...]
    buffers: tuple[Buffer, ...]
    harq_states: tuple[HARQState, ...]

    def __post_init__(self) -> None:
        ue_ids = tuple(ue.ue_id for ue in self.ues)
        if len(ue_ids) != len(set(ue_ids)):
            raise ValueError("ues must not contain duplicate ue_id values")
        observable_ue_ids = set(ue_ids)

        block_ids = tuple(rb.block_id for rb in self.resource_blocks)
        if len(block_ids) != len(set(block_ids)):
            raise ValueError(
                "resource_blocks must not contain duplicate block_id values"
            )
        for rb in self.resource_blocks:
            if rb.tti != self.tti:
                raise ValueError(
                    "resource_blocks must all belong to the current tti"
                )

        cq_ue_ids = tuple(cq.ue_id for cq in self.channel_qualities)
        if len(cq_ue_ids) != len(set(cq_ue_ids)):
            raise ValueError(
                "channel_qualities must not contain duplicate ue_id values"
            )
        for cq in self.channel_qualities:
            if cq.tti != self.tti:
                raise ValueError(
                    "channel_qualities must all belong to the current tti"
                )
            if cq.ue_id not in observable_ue_ids:
                raise ValueError(
                    "channel_qualities must reference an observable ue_id"
                )

        buffer_ue_ids = tuple(buf.ue_id for buf in self.buffers)
        if len(buffer_ue_ids) != len(set(buffer_ue_ids)):
            raise ValueError("buffers must not contain duplicate ue_id values")
        for buf in self.buffers:
            if buf.tti != self.tti:
                raise ValueError("buffers must all belong to the current tti")
            if buf.ue_id not in observable_ue_ids:
                raise ValueError("buffers must reference an observable ue_id")

        harq_ue_ids = tuple(harq.ue_id for harq in self.harq_states)
        if len(harq_ue_ids) != len(set(harq_ue_ids)):
            raise ValueError("harq_states must not contain duplicate ue_id values")
        for harq in self.harq_states:
            if harq.tti != self.tti:
                raise ValueError("harq_states must all belong to the current tti")
            if harq.ue_id not in observable_ue_ids:
                raise ValueError("harq_states must reference an observable ue_id")
