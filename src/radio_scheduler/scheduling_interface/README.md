# scheduling_interface

Defines the structural contract every scheduling algorithm implements: given the network state observable at one TTI and the algorithm's own previous internal state, return that TTI's allocation decisions together with the algorithm's new internal state. See [`ADR-008`](../../../docs/adr/ADR-008-scheduler-statefulness.md) for the full architectural decision this module implements.

This is the seam of the whole system — the only module that both `scenario_generator`-produced data and `reference_implementations` code are built against.

## Public API

- **`ObservableState`** — everything a scheduling algorithm may observe at one TTI, and nothing else.
- **`EmptySchedulerState`** — explicit, memory-less algorithm state, for algorithms with no historical memory.
- **`SchedulingStepResult[StateT]`** — one step's output: the TTI's `AllocationDecision` values plus the algorithm's new internal state.
- **`SchedulingAlgorithm[StateT]`** — the structural (`typing.Protocol`) contract an algorithm implementation satisfies.

## `domain.Scheduler` vs. `SchedulingAlgorithm`

These are deliberately distinct types. `radio_scheduler.domain.Scheduler` is a domain entity that identifies *which* algorithm is being evaluated — its name and version, e.g. for recording in a `Run`. `SchedulingAlgorithm` is the *behavioral* contract — the shape an actual implementation must have (`initial_state()` and `allocate(...)`) to be usable by the Simulation Loop. One algorithm has both: an identity (`Scheduler`) and an implementation satisfying `SchedulingAlgorithm`.

## `ObservableState`

| Field | Type | Contents |
|---|---|---|
| `tti` | `TTI` | The current TTI. |
| `ues` | `tuple[UE, ...]` | UEs eligible/observable for this step. |
| `resource_blocks` | `tuple[ResourceBlock, ...]` | Resource Blocks available at this TTI. |
| `channel_qualities` | `tuple[ChannelQuality, ...]` | CQI readings for this TTI. |
| `buffers` | `tuple[Buffer, ...]` | Buffer occupancy per UE for this TTI. |
| `harq_states` | `tuple[HARQState, ...]` | Pending-retransmission state per UE for this TTI. |

`buffers` already reflects the current TTI's Traffic Arrival: per ADR-002, Buffer occupancy at TTI *n* is "previous occupancy + new arrivals − what was successfully transmitted," so the current TTI's arrival is folded into `Buffer` before it becomes observable. `TrafficArrival` is therefore never provided separately in `ObservableState`; doing so would represent the same quantity twice.

`ObservableState` contains only data for the **current** TTI: no other TTI's data, no final scheduling-performance metrics, no previous `AllocationDecision`, no `Scheduler` identity, no `Run`, no algorithm-specific internal state, and no pipeline delay.

## Explicit algorithm state

A scheduling algorithm never holds state between calls. Each step is:

```
(observable_state, scheduler_state) -> (decisions, new_scheduler_state)
```

`scheduler_state` is passed in and a new one is returned explicitly every call — never mutated in place — so the same `(observable_state, scheduler_state)` pair always produces the same result. `SchedulingStepResult` carries `decisions` and the new `scheduler_state` together.

The contract accepts **zero or more** `AllocationDecision` values per step. Policies such as requiring full Resource Block coverage, a minimum/maximum number of decisions, or UE eligibility rules are **not** imposed by this interface — none of that is defined yet.

## Minimal structural example

Not a reference implementation — just the smallest object satisfying the `SchedulingAlgorithm` shape, using only this module's public API:

```python
from radio_scheduler.scheduling_interface import EmptySchedulerState, SchedulingStepResult


class DoNothingAlgorithm:
    def initial_state(self) -> EmptySchedulerState:
        return EmptySchedulerState()

    def allocate(self, observable_state, scheduler_state):
        return SchedulingStepResult(decisions=(), scheduler_state=scheduler_state)
```

Status: v0.1 implemented. See [`docs/architecture.md`](../../../docs/architecture.md) and [`ADR-008`](../../../docs/adr/ADR-008-scheduler-statefulness.md).
