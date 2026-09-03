from dataclasses import dataclass
from typing import Generic, TypeVar

from radio_scheduler.domain import AllocationDecision, Buffer, Scenario
from radio_scheduler.scheduling_interface import ObservableState, SchedulingAlgorithm

StateT = TypeVar("StateT")


@dataclass(frozen=True)
class SimulationResult(Generic[StateT]):
    """The full output of running a SchedulingAlgorithm against a Scenario
    (ADR-009): every AllocationDecision produced across all TTIs, in TTI
    order, plus the algorithm's final internal state. Deliberately not
    `domain.Run` — `Run` also carries a `Scheduler` identity (name/version)
    that `run()` has no way to know; a caller combines this result with a
    `Scheduler` identity to build a `Run` if needed."""

    decisions: tuple[AllocationDecision, ...]
    final_scheduler_state: StateT


def run(
    scenario: Scenario,
    algorithm: SchedulingAlgorithm[StateT],
    pipeline_delay: int = 0,
) -> SimulationResult[StateT]:
    """Runs `algorithm` against every TTI of `scenario`, in ascending TTI
    order, closing the loop between exogenous state (Scenario) and
    decision-dependent state (Buffer) per ADR-002.

    `pipeline_delay` must be 0 — v0.1 supports no other value (ADR-009).
    Under `d=0`, a TTI is processed causally: this TTI's Traffic Arrival is
    applied to Buffer, an ObservableState is built from that pre-decision
    Buffer, `algorithm.allocate()` is called exactly once, the returned
    decisions are validated, and only then is the Buffer of every UE the
    (validated) decisions served drained to 0 — a UE with at least one
    Resource Block this TTI has its entire post-arrival backlog cleared
    (the binary, capacity-free drain rule of ADR-009), all before the next
    TTI is processed. No queue of pending decisions is built or needed.

    `algorithm.initial_state()` is called exactly once, before any TTI is
    processed — including when `scenario.ttis` is empty, in which case
    `algorithm.allocate()` is never called and the returned
    `SimulationResult.final_scheduler_state` is that initial state,
    unchanged.

    `ObservableState.harq_states` is always `()` in v0.1 (ADR-009: no
    transmission-failure model exists to derive it from).

    Raises `ValueError` before processing any TTI if `pipeline_delay != 0`
    or if `scenario.ttis` contains a duplicate TTI index. Raises
    `ValueError` mid-run, with no partial `SimulationResult` returned, if
    `algorithm.allocate()` returns a decision that fails validation (see
    `_validate_decisions`) — the same treatment as an exception raised by
    `algorithm.allocate()` itself, which is never caught here.
    """
    if pipeline_delay != 0:
        raise ValueError(
            f"pipeline_delay must be 0 in v0.1 (got {pipeline_delay}); "
            "see ADR-009 for why d >= 1 is not yet supported"
        )

    ttis = tuple(sorted(scenario.ttis, key=lambda tti: tti.index))
    seen_tti_indices: set[int] = set()
    for tti in ttis:
        if tti.index in seen_tti_indices:
            raise ValueError(f"duplicate TTI index in scenario.ttis: {tti.index}")
        seen_tti_indices.add(tti.index)

    scheduler_state = algorithm.initial_state()
    occupancy_bytes = {ue.ue_id: 0 for ue in scenario.ues}
    all_decisions: list[AllocationDecision] = []

    for tti in ttis:
        arrivals_by_ue_id = {
            arrival.ue_id: arrival.size_bytes
            for arrival in scenario.traffic_arrivals
            if arrival.tti == tti
        }
        for ue in scenario.ues:
            occupancy_bytes[ue.ue_id] += arrivals_by_ue_id.get(ue.ue_id, 0)

        observable_state = ObservableState(
            tti=tti,
            ues=scenario.ues,
            resource_blocks=tuple(
                rb for rb in scenario.resource_blocks if rb.tti == tti
            ),
            channel_qualities=tuple(
                cq for cq in scenario.channel_qualities if cq.tti == tti
            ),
            buffers=tuple(
                Buffer(
                    tti=tti,
                    ue_id=ue.ue_id,
                    occupancy_bytes=occupancy_bytes[ue.ue_id],
                )
                for ue in scenario.ues
            ),
            harq_states=(),
        )

        step = algorithm.allocate(observable_state, scheduler_state)
        _validate_decisions(step.decisions, observable_state)

        served_ue_ids = {
            decision.ue_id
            for decision in step.decisions
            if decision.resource_block_ids
        }
        for ue_id in served_ue_ids:
            occupancy_bytes[ue_id] = 0

        scheduler_state = step.scheduler_state
        all_decisions.extend(step.decisions)

    return SimulationResult(
        decisions=tuple(all_decisions),
        final_scheduler_state=scheduler_state,
    )


def _validate_decisions(
    decisions: tuple[AllocationDecision, ...],
    observable_state: ObservableState,
) -> None:
    """Rejects a decision that: refers to a TTI other than the current one;
    references a ue_id not in `observable_state.ues`; references a
    resource_block_id not in `observable_state.resource_blocks`; or
    assigns the same resource_block_id more than once, whether within one
    decision's own `resource_block_ids` or across separate decisions in
    this same TTI."""
    ue_ids = {ue.ue_id for ue in observable_state.ues}
    block_ids = {rb.block_id for rb in observable_state.resource_blocks}
    assigned_block_ids: set[str] = set()

    for decision in decisions:
        if decision.tti != observable_state.tti:
            raise ValueError(
                f"decision.tti {decision.tti} does not match current TTI "
                f"{observable_state.tti}"
            )
        if decision.ue_id not in ue_ids:
            raise ValueError(f"decision references unknown ue_id {decision.ue_id!r}")
        for block_id in decision.resource_block_ids:
            if block_id not in block_ids:
                raise ValueError(
                    f"decision references unknown resource_block_id {block_id!r}"
                )
            if block_id in assigned_block_ids:
                raise ValueError(
                    f"resource_block_id {block_id!r} assigned more than once "
                    f"in TTI {observable_state.tti}"
                )
            assigned_block_ids.add(block_id)
