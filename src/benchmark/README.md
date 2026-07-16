# benchmark

Runs one or more schedulers (`reference_implementations`) against one or more scenarios (`scenario_generator`) and records:

- **Scheduling performance**: throughput, fairness, latency/QoS satisfaction, etc.
- **System cost**: execution time, CPU, memory, and scalability as the number of UEs/resource blocks grows.

Benchmarking measures and compares algorithms; it does not assert correctness (see `tests/` for that).

Status: not yet implemented. See [`docs/architecture.md`](../../docs/architecture.md).
