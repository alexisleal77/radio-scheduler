# scenario_generator

Produces scheduling scenarios: network states over time (UEs, channel quality/CQI, traffic demand, available resource blocks, QoS class) that scheduling algorithms are evaluated against. This module produces only **exogenous state** (ADR-002) — it contains no scheduling decisions, no buffer/HARQ state, and no knowledge of any scheduling algorithm.

## `ScenarioGeneratorConfig`

An immutable configuration (`generator.py`) describing how many TTIs, UEs, and Resource Blocks per TTI to generate, the QoS Class labels to assign, and the inclusive bounds used to draw Channel Quality (0–15) and Traffic Arrival (bytes) values. It validates itself structurally on construction (positive counts, well-formed QoS names, bounds within range and internally consistent) and raises `ValueError` on invalid input.

## `generate_scenario(config)`

Deterministically builds a `Scenario`:

- TTIs, UEs (QoS Class assigned by round-robin over `config.qos_class_names`), and Resource Blocks are generated without randomness.
- Channel Quality and Traffic Arrival are drawn from a single local `random.Random(config.seed)` instance — never global `random` state — in this fixed order: **all** Channel Quality values first, then **all** Traffic Arrival values, each pass iterating TTI ascending (outer loop) then UE ascending (inner loop).
- The same `config` (including the same `seed`) always produces a structurally equal `Scenario`.

See [`ADR-007`](../../../docs/adr/ADR-007-scenario-generator-reproducibility-contract.md) for the full reproducibility contract this generation order and PRNG usage follow.

## Example

```python
from radio_scheduler.scenario_generator import ScenarioGeneratorConfig, generate_scenario

config = ScenarioGeneratorConfig(
    seed=42,
    num_ues=2,
    num_ttis=3,
    resource_blocks_per_tti=2,
    qos_class_names=("GBR", "Best Effort"),
)
scenario = generate_scenario(config)
```

Status: v0.1 implemented. See [`docs/architecture.md`](../../../docs/architecture.md).
