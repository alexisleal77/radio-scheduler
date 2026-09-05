# scripts

Operational entry points: running a benchmark suite, generating a report, regenerating a scenario set, etc.

Scripts are thin wrappers around `src/` — they should not contain scheduling or benchmarking logic themselves.

Status: `run_benchmark.py` is implemented — a fixed, no-CLI-args example that generates a small scenario, benchmarks Round Robin against it via `benchmark.benchmark_run()`, and prints a readable summary (`uv run python scripts/run_benchmark.py`). No other scripts yet. See [`docs/architecture.md`](../docs/architecture.md).
