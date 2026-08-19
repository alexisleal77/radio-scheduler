# reference_implementations

Concrete scheduling algorithms implementing `scheduling_interface`: Round Robin, Proportional Fair, MaxCQI, and eventually AI-generated algorithms.

Each algorithm lives in its own module and implements `scheduling_interface` only — it must not depend on other algorithms or reach into `scenario_generator` internals.

## Round Robin

Frequency-domain scheduler: within each TTI, Resource Blocks are distributed one at a time, in order, cycling through `observable_state.ues` in its given canonical order — never re-sorted by `ue_id`, so identifier text format never affects fairness. A UE is eligible for a TTI only if it has a Buffer entry with `occupancy_bytes > 0`. The rotation resumes right after the last-served UE's position, skipping temporarily ineligible UEs without resetting; it only restarts at the first UE when there is no prior state or the last-served UE is no longer observable. Its state (`RoundRobinState`) is threaded explicitly through `initial_state()`/`allocate()`.

## Proportional Fair

Frequency-domain scheduler that balances channel quality against fairness. A UE is eligible for a TTI only if it has both a Channel Quality reading with `cqi > 0` and a Buffer entry with `occupancy_bytes > 0`; a UE with no Buffer entry at all is treated as ineligible, the same as Round Robin. Each eligible UE is scored `cqi / average`, where `average` is that UE's tracked exponential moving average of achieved throughput (a UE never yet served, `average == 0`, scores `+inf` and is served first); ties are broken by canonical `observable_state.ues` order, the same principle used by Round Robin.

Because Channel Quality in the current domain model is frequency-flat — one CQI value per UE per TTI, not per Resource Block — there is no per-Resource-Block signal to differentiate UEs within a TTI: the single top-scoring eligible UE takes every Resource Block available that TTI. This is a consequence of the current CQI granularity, not a defect in the algorithm.

Every UE in `observable_state.ues` has its average updated every TTI — `new_average = 0.9 * average + 0.1 * achieved`, where `achieved` is that UE's CQI if it was served this TTI, else 0. This update runs even when no UE is served (no eligible UEs, or no Resource Blocks that TTI): every tracked average still decays toward 0, since "nobody was served" is itself informative for the fairness bookkeeping. Its state (`ProportionalFairState`) is threaded explicitly through `initial_state()`/`allocate()`.

## MaxCQI

Frequency-domain scheduler that, among UEs already eligible by demand, selects on channel quality. A UE is eligible for a TTI only if it has a Buffer entry with `occupancy_bytes > 0` — a UE with no Buffer entry at all is ineligible, the same as Round Robin and Proportional Fair. MaxCQI additionally requires a Channel Quality reading with `cqi > 0`, the same additional condition Proportional Fair applies; Round Robin, by contrast, never consults Channel Quality at all. Among eligible UEs, MaxCQI selects the one with the highest `cqi` this TTI; ties are broken by canonical `observable_state.ues` order, the same principle used by Round Robin and Proportional Fair.

Because Channel Quality in the current domain model is frequency-flat — one CQI value per UE per TTI, not per Resource Block — there is no per-Resource-Block signal to differentiate UEs within a TTI: the selected UE takes every Resource Block available that TTI, the same consequence already accepted for Proportional Fair.

MaxCQI's decision at a TTI depends only on that TTI's `ObservableState`: it carries no memory across TTIs, so it reuses `EmptySchedulerState` from `scheduling_interface` instead of defining its own state type.

## Status

Round Robin, Proportional Fair, and MaxCQI are implemented (v0.1). Future AI-generated algorithms are not yet implemented. See [`docs/architecture.md`](../../docs/architecture.md).
