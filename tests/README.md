# tests

Functional tests that check schedulers and scenario generators against expected outputs for fixed, deterministic scenarios.

This is about correctness, not performance — a separate concern from `src/radio_scheduler/benchmark/`.

## Running the suite

```
uv run python -m unittest discover -s tests -v
```

## Coverage

- `test_scenario_generator.py` — covers `radio_scheduler.scenario_generator`: `ScenarioGeneratorConfig` structural validation (positive counts, QoS name well-formedness, CQI/traffic bounds, immutability) and `generate_scenario()` (structural counts, determinism, fixed generation order for Channel Quality/Traffic Arrival/Resource Blocks, identifier uniqueness and format, QoS round-robin assignment, value bounds, edge cases, and isolation from global `random` state).
- `test_scheduling_interface.py` — covers `radio_scheduler.scheduling_interface`: `ObservableState`'s temporal coherence (every referenced record belongs to the current TTI), UE reference validity, uniqueness constraints, and immutability; `EmptySchedulerState` and `SchedulingStepResult`'s structural behavior; and explicit, threaded algorithm state, including a memory-less algorithm built with `EmptySchedulerState`.
- `test_round_robin.py` — covers `RoundRobin`: eligibility by `Buffer.occupancy_bytes > 0`, rotation in canonical `observable_state.ues` order (never re-sorted by `ue_id` text), cursor resume/reset rules, empty-result cases (no eligible UEs or no Resource Blocks), state immutability and purity, and import from the `reference_implementations` package root.
- `test_proportional_fair.py` — covers `ProportionalFair`: dual eligibility (`ChannelQuality.cqi > 0` and `Buffer.occupancy_bytes > 0`, enforced by explicit exclusion rather than score coercion), `cqi / average` scoring with `+inf` for never-served UEs, canonical tie-break, single-winner-takes-all-Resource-Blocks under frequency-flat CQI, and the EMA state update applied to every UE every TTI, including TTIs with no eligible UEs or no Resource Blocks.
- `test_max_cqi.py` — covers `MaxCQI`: the same dual eligibility condition as `ProportionalFair`, highest-`cqi` selection with canonical tie-break, frequency-flat single-winner allocation, reuse of `EmptySchedulerState` in place of a dedicated state type, and a dedicated cross-algorithm differentiation suite asserting `MaxCQI` behaves observably differently from `RoundRobin` and `ProportionalFair` on identical inputs.
- `test_simulation_loop.py` — covers `radio_scheduler.simulation_loop.run()`: TTI ordering and duplicate-index rejection, exactly one `initial_state()` call per run, the per-TTI arrival/decision/drain sequencing (including the binary drain rule's exact causal ordering, verified with a dedicated recording test double), decision validation (TTI match, known `ue_id`/`resource_block_id`s, no Resource Block assigned twice), rejection of any `pipeline_delay` other than `0`, determinism, `Scenario` immutability, and an end-to-end run of the same `Scenario` through `RoundRobin`, `ProportionalFair`, and `MaxCQI`.

As of this writing, the suite has 135 tests across these six files — this reflects the current state, not a fixed target; it grows as new modules are implemented.

`benchmark` is not yet implemented and has no tests yet. See [`docs/architecture.md`](../docs/architecture.md).
