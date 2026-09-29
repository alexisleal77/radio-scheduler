from dataclasses import dataclass


@dataclass(frozen=True)
class CheckResult:
    """One exposed check's outcome for one candidate revision (HARNESS6G proposal §15's
    four acceptance categories: build_validity, interface_conformance,
    functional_correctness, domain_conformance)."""

    check_id: str
    category: str
    passed: bool
    detail: str


@dataclass(frozen=True)
class Observation:
    """One candidate revision's structured observation: its content hash
    (empty string if it never got far enough to be read) and every
    exposed check's result, tied together for the evidence package (HARNESS6G proposal
    §10 point 6)."""

    revision_index: int
    candidate_hash: str
    check_results: tuple[CheckResult, ...]
    timestamp: str


@dataclass(frozen=True)
class RunState:
    """Explicit, immutable execution state for one HARNESS6G run — mirrors
    this project's established convention (ADR-007, ADR-008) of never
    holding hidden mutable state: the orchestrator threads a new RunState
    through each revision rather than mutating one in place.

    `termination_reason` is `None` only while the run is still in
    progress; every terminated run's evidence package carries a non-`None`
    value (HARNESS6G proposal §10 point 7 — termination policy and its actually-recorded
    reason)."""

    observations: tuple[Observation, ...] = ()
    correction_count: int = 0
    termination_reason: str | None = None
