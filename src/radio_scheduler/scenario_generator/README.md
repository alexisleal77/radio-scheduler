# scenario_generator

Produces scheduling scenarios: network states over time (UEs, channel quality/CQI, buffer/traffic demand, available resource blocks, QoS class, etc.) that scheduling algorithms are evaluated against.

This module must not depend on `scheduling_interface` implementations — it only produces data, with no knowledge of how that data will be scheduled.

Status: not yet implemented. See [`docs/architecture.md`](../../docs/architecture.md).
