from dataclasses import dataclass
from typing import Generic, Protocol, TypeVar

from radio_scheduler.domain import AllocationDecision
from radio_scheduler.scheduling_interface.observable_state import ObservableState

StateT = TypeVar("StateT")


@dataclass(frozen=True)
class EmptySchedulerState:
    """Explicit, memory-less scheduler state (ADR-008 point 12).

    For algorithms with no historical memory (e.g. MaxCQI). A real,
    dedicated type — not None, an empty dict, or object() — so "no memory"
    is represented through the same initial_state()/allocate() contract as
    any other algorithm's state, rather than as a special case.
    """


@dataclass(frozen=True)
class SchedulingStepResult(Generic[StateT]):
    """One TTI's output from a SchedulingAlgorithm step (ADR-008).

    Carries the AllocationDecision values for the current TTI together with
    the algorithm's new internal state, to be threaded into the next call.
    No policy is enforced here: zero decisions, multiple decisions for the
    same UE, and partial Resource Block coverage are all structurally
    valid — those rules, if any, belong to a future conformance layer, not
    to this result type.
    """

    decisions: tuple[AllocationDecision, ...]
    scheduler_state: StateT


class SchedulingAlgorithm(Protocol[StateT]):
    """Structural contract every scheduling algorithm satisfies (ADR-008).

    Deliberately not named `Scheduler` — `radio_scheduler.domain.Scheduler`
    already identifies an algorithm by name/version (a domain entity); this
    Protocol is the distinct, behavioral contract an implementation
    satisfies, not another identity type.

    An implementing object may hold immutable configuration, but must not
    rely on hidden mutable state between calls: `allocate` receives and
    returns `StateT` explicitly, and calling it twice with the same
    `(observable_state, scheduler_state)` pair must produce the same
    result.
    """

    def initial_state(self) -> StateT:
        ...

    def allocate(
        self,
        observable_state: ObservableState,
        scheduler_state: StateT,
    ) -> "SchedulingStepResult[StateT]":
        ...
