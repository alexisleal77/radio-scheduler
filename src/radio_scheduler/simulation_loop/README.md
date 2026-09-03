# simulation_loop

Closes the loop between the exogenous state a `Scenario` provides (ADR-002) and the decision-dependent state (`Buffer`) a scheduling algorithm's decisions produce. This is the module named but left unassigned by ADR-002/ADR-003, and the missing piece that lets `scenario_generator`, `scheduling_interface`, and `reference_implementations` be exercised together, end-to-end, for the first time. See [`ADR-009`](../../../docs/adr/ADR-009-simulation-loop-v0.1.md) for the full decision this module implements.

## `run(scenario, algorithm, pipeline_delay=0)`

A free function — not a stateful object — that runs any `SchedulingAlgorithm` against every TTI of a `Scenario`, in ascending TTI order, and returns a `SimulationResult`.

For each TTI, in order:

1. The TTI's `TrafficArrival` is applied to each UE's running `Buffer` occupancy.
2. An `ObservableState` is built from that pre-decision `Buffer`, plus the TTI's `ResourceBlock` and `ChannelQuality` records filtered from the `Scenario`, `scenario.ues` unfiltered, and `harq_states=()`.
3. `algorithm.allocate()` is called exactly once.
4. The returned decisions are validated (see below) before anything else happens.
5. Only then, every UE that received at least one Resource Block this TTI has its `Buffer` drained to `0` — the binary, capacity-free rule ADR-009 adopts for v0.1, since the domain model has no CQI-to-rate or per-Resource-Block capacity model to compute a more realistic transmitted-bytes figure.

`algorithm.initial_state()` is called exactly once, before any TTI is processed — including when `scenario.ttis` is empty, in which case `algorithm.allocate()` is never called at all.

## `pipeline_delay`

v0.1 supports only `pipeline_delay=0`; any other value raises `ValueError` before any TTI is processed. Under `d=0`, a decision computed for a TTI is fully applied (Buffer drained) before that same TTI ends — no queue of pending decisions is built. Support for `pipeline_delay >= 1` is explicitly deferred (ADR-009): it requires a "service pending" mechanism that does not exist yet.

## Decision validation

Before a TTI's decisions are applied to `Buffer`, each one is checked:

- `decision.tti` matches the TTI just processed.
- `decision.ue_id` is one of `observable_state.ues`.
- Every `resource_block_id` in `decision.resource_block_ids` is one of `observable_state.resource_blocks`.
- No `resource_block_id` is assigned more than once in the same TTI, whether within one decision or across separate decisions.

Any violation raises `ValueError`; no partial `SimulationResult` is returned. An exception raised by `algorithm.allocate()` itself propagates unmodified, for the same reason.

## `SimulationResult`

```python
@dataclass(frozen=True)
class SimulationResult(Generic[StateT]):
    decisions: tuple[AllocationDecision, ...]
    final_scheduler_state: StateT
```

All `AllocationDecision` values produced across the run, concatenated in TTI order, plus the algorithm's final internal state. Deliberately not `domain.Run` — `Run` also carries a `Scheduler` identity (name/version) that `run()` has no way to know; a caller combines this result with a `Scheduler` identity to build a `Run` if needed. There is no `SimulationStepResult`: `scheduling_interface`'s own `SchedulingStepResult` already fills that per-TTI role internally.

## v0.1 limitations

- `HARQState` is never populated (`harq_states=()` always) — no transmission-failure model exists to derive it from, and no `reference_implementations` algorithm reads it yet.
- The binary drain rule is not a claim about real transmission capacity — it is the minimal rule that makes `Buffer` genuinely decision-dependent without inventing a CQI-to-rate model.
- No scheduling-performance or system-cost metrics are computed here — that is `benchmark`'s responsibility, once it exists.

Status: v0.1 implemented. See [`docs/architecture.md`](../../../docs/architecture.md) and [`ADR-009`](../../../docs/adr/ADR-009-simulation-loop-v0.1.md).
