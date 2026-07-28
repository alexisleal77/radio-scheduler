from dataclasses import dataclass


@dataclass(frozen=True)
class TTI:
    """Ordinal position of a TTI within a Scenario, starting at 0."""

    index: int


@dataclass(frozen=True)
class QoSClass:
    """Free-text service-level label for a UE (e.g. "GBR", "Best Effort")."""

    name: str
