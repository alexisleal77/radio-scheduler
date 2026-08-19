from dataclasses import dataclass

from radio_scheduler.domain import AllocationDecision
from radio_scheduler.scheduling_interface import ObservableState, SchedulingStepResult

_EMA_ALPHA = 0.1


@dataclass(frozen=True)
class ProportionalFairState:
    """Explicit ProportionalFair state (ADR-008): each observed UE's
    exponential moving average of achieved throughput (proxied by CQI, per
    the domain model's v0.1 limitation), as a tuple of (ue_id, average)
    pairs — mirroring the domain's tuple-of-pairs convention rather than a
    dict."""

    average_throughput: tuple[tuple[str, float], ...] = ()


def _score(cqi: int, average: float) -> float:
    if cqi <= 0:
        return 0.0
    if average == 0.0:
        return float("inf")
    return cqi / average


class ProportionalFair:
    """Frequency-domain Proportional Fair.

    Because ChannelQuality is frequency-flat in the current domain model
    (one CQI value per UE per TTI, not per Resource Block), there is no
    per-Resource-Block signal to differentiate UEs within a TTI: the single
    top-scoring eligible UE takes every Resource Block available that TTI.
    This is an honest consequence of v0.1's CQI granularity, not a new gap.

    Eligibility and scoring: a UE is eligible only if it has both a CQI
    reading with cqi > 0 and a Buffer entry with occupancy_bytes > 0 this
    TTI — a UE missing either (including a UE with no Buffer entry at all,
    same treatment as RoundRobin) scores 0 and never wins. Eligible UEs are
    scored `cqi / average`, where `average` is that UE's tracked EMA of
    achieved throughput; a UE with average == 0 (never yet served) scores
    +inf, guaranteeing it is served before any UE with a nonzero average.
    Ties (including multiple +inf scores) are broken by canonical
    `observable_state.ues` order, the same principle used by RoundRobin.

    State update: every UE in `observable_state.ues` has its average
    updated this TTI — `new_avg = 0.9 * avg + 0.1 * achieved`, with
    achieved = its CQI if it was the served UE this TTI, else 0. Unlike
    RoundRobinState, this means the state must NOT be returned unchanged
    even when there are no eligible UEs or no Resource Blocks: every
    tracked UE's average still decays toward 0, since "nobody was served"
    is itself informative for PF's fairness bookkeeping.

    No hidden mutable state: this object holds no instance attributes.
    ProportionalFairState is threaded explicitly through
    initial_state()/allocate() (ADR-008).
    """

    def initial_state(self) -> ProportionalFairState:
        return ProportionalFairState()

    def allocate(
        self,
        observable_state: ObservableState,
        scheduler_state: ProportionalFairState,
    ) -> SchedulingStepResult[ProportionalFairState]:
        ue_order = observable_state.ues
        averages = dict(scheduler_state.average_throughput)
        cqi_by_ue_id = {cq.ue_id: cq.cqi for cq in observable_state.channel_qualities}
        eligible_ue_ids = {
            buffer.ue_id
            for buffer in observable_state.buffers
            if buffer.occupancy_bytes > 0
        }

        served_ue_id: str | None = None
        if ue_order and observable_state.resource_blocks:
            best_score = -1.0
            for ue in ue_order:
                if ue.ue_id not in eligible_ue_ids:
                    continue

                cqi = cqi_by_ue_id.get(ue.ue_id, 0)
                if cqi <= 0:
                    continue

                average = averages.get(ue.ue_id, 0.0)
                score = _score(cqi, average)
                if score > best_score:
                    best_score = score
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

        new_averages = tuple(
            (
                ue.ue_id,
                (1 - _EMA_ALPHA) * averages.get(ue.ue_id, 0.0)
                + _EMA_ALPHA
                * (
                    cqi_by_ue_id.get(ue.ue_id, 0)
                    if ue.ue_id == served_ue_id
                    else 0
                ),
            )
            for ue in ue_order
        )
        new_state = ProportionalFairState(average_throughput=new_averages)
        return SchedulingStepResult(decisions=decisions, scheduler_state=new_state)
