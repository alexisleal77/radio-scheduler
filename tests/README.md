# tests

Functional tests that check schedulers and scenario generators against expected outputs for fixed, deterministic scenarios.

This is about correctness, not performance — a separate concern from `src/radio_scheduler/benchmark/`.

## Running the suite

```
uv run python -m unittest discover -s tests -v
```

## Coverage

- `test_scenario_generator.py` — covers `radio_scheduler.scenario_generator` (as of this writing: 22 tests): `ScenarioGeneratorConfig` structural validation (positive counts, QoS name well-formedness, CQI/traffic bounds, immutability) and `generate_scenario()` (structural counts, determinism, fixed generation order for Channel Quality/Traffic Arrival/Resource Blocks, identifier uniqueness and format, QoS round-robin assignment, value bounds, edge cases, and isolation from global `random` state).

Other modules (`scheduling_interface`, `reference_implementations`, `benchmark`) are not yet implemented and have no tests yet. See [`docs/architecture.md`](../docs/architecture.md).
