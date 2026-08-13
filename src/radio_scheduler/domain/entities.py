from dataclasses import dataclass


@dataclass(frozen=True)
class TTI:
    """Ordinal position of a TTI within a Scenario, starting at 0."""

    index: int


@dataclass(frozen=True)
class QoSClass:
    """Free-text service-level label for a UE (e.g. "GBR", "Best Effort")."""

    name: str


@dataclass(frozen=True)
class ChannelQuality:
    """3GPP CQI reading (0-15) for one UE at one TTI. Exogenous state (ADR-002)."""

    tti: TTI
    ue_id: str
    cqi: int


@dataclass(frozen=True)
class TrafficArrival:
    """New data entering a UE's Buffer at one TTI. Exogenous state (ADR-002)."""

    tti: TTI
    ue_id: str
    size_bytes: int


@dataclass(frozen=True)
class ResourceBlock:
    """A schedulable unit of radio capacity available at one TTI."""

    tti: TTI
    block_id: str


@dataclass(frozen=True)
class UE:
    """A device being scheduled, identified within a Scenario."""

    ue_id: str
    qos_class: QoSClass


@dataclass(frozen=True)
class Buffer:
    """Unsent data queued for a UE at one TTI. Decision-dependent state (ADR-002)."""

    tti: TTI
    ue_id: str
    occupancy_bytes: int


@dataclass(frozen=True)
class HARQState:
    """Outstanding retransmission need for a UE at one TTI. Decision-dependent state
    (ADR-002); simplified to a single pending flag for v0.1 (ADR-006)."""

    tti: TTI
    ue_id: str
    retransmission_pending: bool


@dataclass(frozen=True)
class Scenario:
    """A network operating condition: exogenous state (ADR-002), generated
    independently of any scheduling decision. Carries its seed so it is
    reproducible from the data alone (Design Principle 4)."""

    seed: int
    ttis: tuple[TTI, ...]
    ues: tuple[UE, ...]
    resource_blocks: tuple[ResourceBlock, ...]
    channel_qualities: tuple[ChannelQuality, ...]
    traffic_arrivals: tuple[TrafficArrival, ...]


@dataclass(frozen=True)
class AllocationDecision:
    """A Scheduler's output for one TTI within a Run: the Resource Blocks assigned
    to one UE."""

    tti: TTI
    ue_id: str
    resource_block_ids: tuple[str, ...]


@dataclass(frozen=True)
class Scheduler:
    """Identity of a scheduling algorithm being evaluated (e.g. Round Robin,
    Proportional Fair, MaxCQI)."""

    name: str
    version: str


@dataclass(frozen=True)
class Run:
    """One execution of a Scheduler against a Scenario, with a configurable
    scheduling pipeline delay (ADR-003, default 1 TTI)."""

    scenario: Scenario
    scheduler: Scheduler
    decisions: tuple[AllocationDecision, ...]
    pipeline_delay: int = 1


@dataclass(frozen=True)
class SchedulingPerformanceMetric:
    """Aggregated scheduling performance for a Run (system-cost metrics such as
    execution time/CPU/memory are explicitly out of scope for the domain model)."""

    throughput_bps: float
    fairness_index: float
    average_latency_ttis: float
