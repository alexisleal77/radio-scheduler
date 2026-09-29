from dataclasses import dataclass

from radio_scheduler.domain import (
    ChannelQuality,
    QoSClass,
    ResourceBlock,
    Scenario,
    TrafficArrival,
    TTI,
    UE,
)


@dataclass(frozen=True)
class DemoScenario:
    """One small, hand-built Scenario for Delivery A's demonstration, plus
    the rationale for why it was chosen (not a random sample from
    `scenario_generator`) — every value is picked so the expected
    `AllocationDecision` set for each reference implementation can be
    computed by hand and asserted as an oracle in `tests/test_demo.py`."""

    scenario_id: str
    description: str
    scenario: Scenario


def _build_scenario(
    *,
    seed: int,
    ue_ids: tuple[str, ...],
    num_ttis: int,
    resource_blocks_per_tti: dict[int, int] | int,
    cqi_by_tti_ue: dict[tuple[int, str], int] | int,
    arrivals_by_tti_ue: dict[tuple[int, str], int],
) -> Scenario:
    """Hand-built Scenario (not via `generate_scenario`) for precise,
    reviewable control over per-(TTI, UE) Channel Quality, Traffic Arrival,
    and per-TTI Resource Block count — the same pattern already used in
    `tests/test_simulation_loop.py`'s `make_scenario`, extended with
    per-TTI Resource Block counts and per-(TTI, UE) CQI, both needed by
    these specific demo scenarios."""
    ttis = tuple(TTI(index=i) for i in range(num_ttis))
    ues = tuple(UE(ue_id=ue_id, qos_class=QoSClass(name="GBR")) for ue_id in ue_ids)

    def rb_count(tti_index: int) -> int:
        if isinstance(resource_blocks_per_tti, int):
            return resource_blocks_per_tti
        return resource_blocks_per_tti.get(tti_index, 0)

    resource_blocks = tuple(
        ResourceBlock(tti=tti, block_id=f"rb-{tti.index}-{j}")
        for tti in ttis
        for j in range(rb_count(tti.index))
    )

    def cqi_value(tti_index: int, ue_id: str) -> int:
        if isinstance(cqi_by_tti_ue, int):
            return cqi_by_tti_ue
        return cqi_by_tti_ue.get((tti_index, ue_id), 0)

    channel_qualities = tuple(
        ChannelQuality(tti=tti, ue_id=ue.ue_id, cqi=cqi_value(tti.index, ue.ue_id))
        for tti in ttis
        for ue in ues
    )

    traffic_arrivals = tuple(
        TrafficArrival(
            tti=tti,
            ue_id=ue.ue_id,
            size_bytes=arrivals_by_tti_ue.get((tti.index, ue.ue_id), 0),
        )
        for tti in ttis
        for ue in ues
    )

    return Scenario(
        seed=seed,
        ttis=ttis,
        ues=ues,
        resource_blocks=resource_blocks,
        channel_qualities=channel_qualities,
        traffic_arrivals=traffic_arrivals,
    )


def _ue_competition_scenario() -> Scenario:
    """Two UEs, tied CQI (10) every TTI, both with backlog every TTI: the
    three reference implementations disagree on who gets served without
    any Channel Quality difference to justify it, isolating each
    algorithm's own tie-break/fairness policy (RR's rotation, PF's
    average-throughput fairness, MaxCQI's memory-less greedy pick)."""
    return _build_scenario(
        seed=101,
        ue_ids=("ue-0", "ue-1"),
        num_ttis=2,
        resource_blocks_per_tti=2,
        cqi_by_tti_ue=10,
        arrivals_by_tti_ue={
            (0, "ue-0"): 100,
            (0, "ue-1"): 100,
            (1, "ue-0"): 50,
            (1, "ue-1"): 50,
        },
    )


def _cqi_difference_scenario() -> Scenario:
    """Two UEs, one Resource Block, one TTI, both cold-start (no scheduling
    history) and both with backlog: only Channel Quality differs (ue-0=3,
    ue-1=12). MaxCQI must pick ue-1 (highest CQI); Round Robin must pick
    ue-0 (first in rotation, CQI-blind); Proportional Fair, with both
    UEs' average throughput still at 0, scores both +inf and also picks
    ue-0 by canonical tie-break — a genuine, documented v0.1 property
    (fairness dominates CQI at cold start), not an oversight."""
    return _build_scenario(
        seed=102,
        ue_ids=("ue-0", "ue-1"),
        num_ttis=1,
        resource_blocks_per_tti=1,
        cqi_by_tti_ue={(0, "ue-0"): 3, (0, "ue-1"): 12},
        arrivals_by_tti_ue={(0, "ue-0"): 100, (0, "ue-1"): 100},
    )


def _no_eligibility_or_resources_scenario() -> Scenario:
    """Two UEs, two TTIs, exercising the two distinct boundary conditions
    that must each independently yield zero decisions: TTI 0 has a
    Resource Block available but no UE has any backlog (no eligible UE);
    TTI 1 has backlog for both UEs but zero Resource Blocks available (no
    resource to allocate). Neither condition should ever raise — both are
    valid, expected states for every reference implementation."""
    return _build_scenario(
        seed=103,
        ue_ids=("ue-0", "ue-1"),
        num_ttis=2,
        resource_blocks_per_tti={0: 1, 1: 0},
        cqi_by_tti_ue=10,
        arrivals_by_tti_ue={(0, "ue-0"): 0, (0, "ue-1"): 0, (1, "ue-0"): 100, (1, "ue-1"): 100},
    )


def build_demo_scenarios() -> tuple[DemoScenario, ...]:
    """The fixed set of small demo scenarios for Delivery A, each chosen to
    reveal a specific, explainable difference in behavior between Round
    Robin, Proportional Fair, and MaxCQI, or a shared boundary-condition
    invariant all three must satisfy."""
    return (
        DemoScenario(
            scenario_id="ue_competition",
            description=(
                "Duas UEs, CQI empatado (10) em toda TTI, ambas com backlog em "
                "toda TTI — isola a política de cada algoritmo (rotação do RR, "
                "justiça por média de throughput do PF, escolha gulosa e sem "
                "memória do MaxCQI) sem nenhuma diferença de qualidade de canal "
                "para justificá-la."
            ),
            scenario=_ue_competition_scenario(),
        ),
        DemoScenario(
            scenario_id="cqi_difference",
            description=(
                "Duas UEs, um Resource Block, uma TTI, ambas em cold-start: só "
                "o CQI difere (ue-0=3, ue-1=12). Mostra o MaxCQI escolhendo por "
                "CQI puro, enquanto RR e PF (em cold-start) escolhem por ordem "
                "canônica, CQI-cego."
            ),
            scenario=_cqi_difference_scenario(),
        ),
        DemoScenario(
            scenario_id="no_eligibility_or_resources",
            description=(
                "Duas condições de contorno distintas: TTI 0 tem Resource Block "
                "mas nenhuma UE elegível (sem backlog); TTI 1 tem UEs elegíveis "
                "mas nenhum Resource Block disponível. As três implementações "
                "devem retornar zero decisões em ambos os casos, sem erro."
            ),
            scenario=_no_eligibility_or_resources_scenario(),
        ),
    )
