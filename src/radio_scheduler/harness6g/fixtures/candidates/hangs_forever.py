"""Demo/replay fixture: a deliberately pathological candidate whose
allocate() never returns. Used only to prove
`stopping_policy.timeout_seconds` is enforced by real OS-process
termination (the parent's subprocess.run(..., timeout=...) kills the
check-runner process), not merely observed after the fact.
"""

from radio_scheduler.scheduling_interface import EmptySchedulerState


class HangsForever:
    def initial_state(self):
        return EmptySchedulerState()

    def allocate(self, observable_state, scheduler_state):
        while True:
            pass


def build_algorithm():
    return HangsForever()
