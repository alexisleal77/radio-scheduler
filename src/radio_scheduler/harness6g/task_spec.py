from dataclasses import dataclass


@dataclass(frozen=True)
class StoppingPolicy:
    """When a HARNESS6G run must stop trying revisions (V21 §10 point 7).
    Provisional technical parameters for this demonstration, not a
    scientifically approved protocol setting (V21 prompt §12) — recorded
    verbatim in every run's evidence package rather than hidden."""

    max_revisions: int
    timeout_seconds: float

    def __post_init__(self) -> None:
        if self.max_revisions < 1:
            raise ValueError("max_revisions must be >= 1")
        if self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")


@dataclass(frozen=True)
class ResourcePolicy:
    """Provisional technical resource bound (V21 prompt §12). v0.1 enforces
    only wall-clock time per check, via the check subprocess's own
    `timeout_seconds` (StoppingPolicy) being a real OS-level interruption.
    Memory/CPU bounding is explicitly not enforced — `enforced=False`
    fields exist so an evidence reader never has to infer a false
    guarantee from silence."""

    memory_bound_enforced: bool = False
    cpu_bound_enforced: bool = False


@dataclass(frozen=True)
class TaskSpec:
    """Versioned task manifest validated before any candidate code executes
    (V21 §10 points 1-2). `editable_scope` is a tuple of repository-relative
    directory paths a candidate's source file must resolve inside — the
    only materialization boundary this v0.1 harness enforces (no
    filesystem/network sandbox beyond that containment check plus the
    check-subprocess boundary in `checks.py`; see `docs/design.md` §3 and
    `docs/proposal-traceability.md` for what is and is not implemented).
    """

    task_id: str
    task_version: str
    interface_version: str
    editable_scope: tuple[str, ...]
    exposed_context: tuple[str, ...]
    exposed_checks: tuple[str, ...]
    stopping_policy: StoppingPolicy
    resource_policy: ResourcePolicy

    def __post_init__(self) -> None:
        if not self.task_id:
            raise ValueError("task_id must not be empty")
        if not self.task_version:
            raise ValueError("task_version must not be empty")
        if not self.interface_version:
            raise ValueError("interface_version must not be empty")
        if not self.editable_scope:
            raise ValueError("editable_scope must not be empty")
        if not self.exposed_checks:
            raise ValueError("exposed_checks must not be empty")


def default_scheduling_candidate_task(
    editable_scope: tuple[str, ...] = (
        "src/radio_scheduler/harness6g/fixtures/candidates",
    ),
) -> TaskSpec:
    """The one task this v0.1 harness demonstrates: implement a
    `SchedulingAlgorithm` (scheduling_interface v0.1) exposed via a
    module-level `build_algorithm()` factory, satisfying the three exposed
    checks below. `exposed_context` names what a candidate-generating
    process is told about — never the protected evaluator or anything
    beyond `scheduling_interface`'s own public contract and the same demo
    scenarios Delivery A already uses."""
    return TaskSpec(
        task_id="radio-scheduler-candidate-v0.1",
        task_version="0.1.0",
        interface_version="scheduling_interface-v0.1",
        editable_scope=editable_scope,
        exposed_context=(
            "docs/design.md#1-architecture-of-the-scheduling-component-the-car",
            "src/radio_scheduler/scheduling_interface/",
            "src/radio_scheduler/demo/scenarios.py",
        ),
        exposed_checks=(
            "interface_conformance",
            "served_ue_must_have_backlog",
            "no_eligibility_or_resources_yields_empty_decisions",
        ),
        stopping_policy=StoppingPolicy(max_revisions=3, timeout_seconds=10.0),
        resource_policy=ResourcePolicy(),
    )
