import random
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
class ScenarioGeneratorConfig:
    """Minimal input configuration for the future generate_scenario() (ADR-007).

    Governs only exogenous-state generation (ADR-002): UE count, TTI count,
    Resource Blocks per TTI, QoS Class labels, and the bounds used to draw
    Channel Quality and Traffic Arrival values. This is a generator input,
    not a domain entity — it does not live in radio_scheduler.domain and is
    not subject to Design Principle 3 (entities are pure data); the
    structural validation in __post_init__ belongs to the generator's input
    boundary. Validation is limited to obvious structural checks (positive
    counts, lower <= upper bounds, non-empty QoS collection); it does not
    encode telecom-specific rules beyond what ADR-006 already documents.
    """

    seed: int
    num_ues: int
    num_ttis: int
    resource_blocks_per_tti: int
    qos_class_names: tuple[str, ...]
    cqi_min: int = 1
    cqi_max: int = 15
    traffic_arrival_min_bytes: int = 0
    traffic_arrival_max_bytes: int = 1500

    def __post_init__(self) -> None:
        if self.num_ues <= 0:
            raise ValueError("num_ues must be positive")
        if self.num_ttis <= 0:
            raise ValueError("num_ttis must be positive")
        if self.resource_blocks_per_tti <= 0:
            raise ValueError("resource_blocks_per_tti must be positive")
        if not self.qos_class_names:
            raise ValueError("qos_class_names must not be empty")
        for name in self.qos_class_names:
            if not isinstance(name, str):
                raise ValueError("qos_class_names must contain only strings")
            if not name.strip():
                raise ValueError(
                    "qos_class_names must not contain empty or "
                    "whitespace-only strings"
                )
        if not 0 <= self.cqi_min <= 15:
            raise ValueError("cqi_min must be between 0 and 15")
        if not 0 <= self.cqi_max <= 15:
            raise ValueError("cqi_max must be between 0 and 15")
        if self.cqi_min > self.cqi_max:
            raise ValueError("cqi_min must not be greater than cqi_max")
        if self.traffic_arrival_min_bytes < 0:
            raise ValueError("traffic_arrival_min_bytes must be non-negative")
        if self.traffic_arrival_max_bytes < 0:
            raise ValueError("traffic_arrival_max_bytes must be non-negative")
        if self.traffic_arrival_min_bytes > self.traffic_arrival_max_bytes:
            raise ValueError(
                "traffic_arrival_min_bytes must not be greater than "
                "traffic_arrival_max_bytes"
            )


def generate_scenario(config: ScenarioGeneratorConfig) -> Scenario:
    """Deterministic structure plus Channel Quality and Traffic Arrival.

    TTIs, UEs, QoS assignment, and Resource Blocks are deterministic (no
    randomness). Channel Quality and Traffic Arrival are drawn from a single
    local `random.Random(seed)` instance, in the fixed order documented in
    ADR-007 point 2: TTI ascending (outer loop), then UE ascending (inner
    loop); within that order, all Channel Quality values are drawn first,
    then all Traffic Arrival values, preserving the same (tti, ue) pair
    order for each. No global `random` state is read or modified. A
    `size_bytes` of 0 is a valid, explicit TrafficArrival record — it is
    never omitted.

    Identifier convention (no prior documented convention found in ADR-002,
    ADR-006, ADR-007, or the domain model — only that ids are `str`, per
    ADR-006): `ue_id` is `"ue-{index}"`, zero-based, unique across the whole
    Scenario. `block_id` is `"rb-{tti_index}-{block_index}"`, zero-based,
    unique across the whole Scenario — not just within its own TTI — so that
    a `block_id` alone (e.g. in `AllocationDecision.resource_block_ids`,
    which carries no TTI field) unambiguously identifies one Resource Block
    without relying on external (tti, block_id) pairing. This is a local,
    reversible formatting detail and does not meet docs/adr/README.md's bar
    for an ADR.
    """
    ttis = tuple(TTI(index=i) for i in range(config.num_ttis))

    ues = tuple(
        UE(
            ue_id=f"ue-{i}",
            qos_class=QoSClass(
                name=config.qos_class_names[i % len(config.qos_class_names)]
            ),
        )
        for i in range(config.num_ues)
    )

    resource_blocks = tuple(
        ResourceBlock(tti=tti, block_id=f"rb-{tti.index}-{j}")
        for tti in ttis
        for j in range(config.resource_blocks_per_tti)
    )

    rng = random.Random(config.seed)
    channel_qualities = tuple(
        ChannelQuality(
            tti=tti,
            ue_id=ue.ue_id,
            cqi=rng.randint(config.cqi_min, config.cqi_max),
        )
        for tti in ttis
        for ue in ues
    )

    traffic_arrivals = tuple(
        TrafficArrival(
            tti=tti,
            ue_id=ue.ue_id,
            size_bytes=rng.randint(
                config.traffic_arrival_min_bytes,
                config.traffic_arrival_max_bytes,
            ),
        )
        for tti in ttis
        for ue in ues
    )

    return Scenario(
        seed=config.seed,
        ttis=ttis,
        ues=ues,
        resource_blocks=resource_blocks,
        channel_qualities=channel_qualities,
        traffic_arrivals=traffic_arrivals,
    )
