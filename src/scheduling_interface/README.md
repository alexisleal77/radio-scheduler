# scheduling_interface

Defines the contract every scheduling algorithm must implement: given the current network/scenario state, return a resource allocation decision.

This is the seam of the whole system — the only module that both `scenario_generator`-produced data and `reference_implementations` code are built against. Every algorithm (reference or AI-generated) implements this interface and nothing else is required to make it interchangeable with the others.

Status: not yet implemented. See [`docs/architecture.md`](../../docs/architecture.md).
