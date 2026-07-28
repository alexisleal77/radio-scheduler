from dataclasses import dataclass


@dataclass(frozen=True)
class TTI:
    """Ordinal position of a TTI within a Scenario, starting at 0."""

    index: int
