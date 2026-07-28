# reference_implementations

Concrete scheduling algorithms implementing `scheduling_interface`: Round Robin, Proportional Fair, MaxCQI, and eventually AI-generated algorithms.

Each algorithm lives in its own module and implements `scheduling_interface` only — it must not depend on other algorithms or reach into `scenario_generator` internals.

Status: not yet implemented. See [`docs/architecture.md`](../../docs/architecture.md).
