# reference_implementations

Concrete scheduling algorithms implementing `scheduling_interface`: Round Robin, Proportional Fair, MaxCQI, and eventually AI-generated algorithms.

Each algorithm lives in its own module and implements `scheduling_interface` only — it must not depend on other algorithms or reach into `scenario_generator` internals.

## Round Robin

Frequency-domain scheduler: within each TTI, Resource Blocks are distributed one at a time, in order, cycling through `observable_state.ues` in its given canonical order — never re-sorted by `ue_id`, so identifier text format never affects fairness. A UE is eligible for a TTI only if it has a Buffer entry with `occupancy_bytes > 0`. The rotation resumes right after the last-served UE's position, skipping temporarily ineligible UEs without resetting; it only restarts at the first UE when there is no prior state or the last-served UE is no longer observable. Its state (`RoundRobinState`) is threaded explicitly through `initial_state()`/`allocate()`.

## Proportional Fair

Frequency-domain scheduler that balances channel quality against fairness. A UE is eligible for a TTI only if it has both a Channel Quality reading with `cqi > 0` and a Buffer entry with `occupancy_bytes > 0`; a UE with no Buffer entry at all is treated as ineligible, the same as Round Robin. Each eligible UE is scored `cqi / average`, where `average` is that UE's tracked exponential moving average of achieved throughput (a UE never yet served, `average == 0`, scores `+inf` and is served first); ties are broken by canonical `observable_state.ues` order, the same principle used by Round Robin.

Because Channel Quality in the current domain model is frequency-flat — one CQI value per UE per TTI, not per Resource Block — there is no per-Resource-Block signal to differentiate UEs within a TTI: the single top-scoring eligible UE takes every Resource Block available that TTI. This is a consequence of the current CQI granularity, not a defect in the algorithm.

Every UE in `observable_state.ues` has its average updated every TTI — `new_average = 0.9 * average + 0.1 * achieved`, where `achieved` is that UE's CQI if it was served this TTI, else 0. This update runs even when no UE is served (no eligible UEs, or no Resource Blocks that TTI): every tracked average still decays toward 0, since "nobody was served" is itself informative for the fairness bookkeeping. Its state (`ProportionalFairState`) is threaded explicitly through `initial_state()`/`allocate()`.

## Status

Round Robin and Proportional Fair are implemented (v0.1). MaxCQI and future AI-generated algorithms are not yet implemented. See [`docs/architecture.md`](../../docs/architecture.md).
