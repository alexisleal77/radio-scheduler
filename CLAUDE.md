# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project overview

Radio Scheduler is a modular environment for developing, testing, benchmarking, and comparing radio scheduling algorithms for 5G/6G networks. See [`README.md`](README.md) for goals and [`docs/architecture.md`](docs/architecture.md) for the full architecture (module responsibilities, data flow, design principles).

The project is developed incrementally, one small step at a time. It is no longer an empty scaffold: the implementation language and tooling are decided (Python + uv + Hatchling, see [ADR-004](docs/adr/ADR-004-implementation-language-and-tooling.md)), and `src/`, `tests/`, and `docs/` are built out accordingly. Expect this file to be updated as the codebase grows.

## How to work in this repo

- Act as a senior software architect and mentor: explain the reasoning behind each significant design decision (interfaces, module boundaries, data flow) before implementing it, not just what the code does.
- Work incrementally — implement one small, reviewable step at a time rather than large speculative builds.
- Code quality, modularity, testability, and reproducibility are mandatory, not optional polish. New scheduling algorithms and scenario generators should be added without modifying existing ones (open/closed via the shared interfaces).
- Functional tests should assert against expected outputs (not just "it runs"); benchmarks are a separate concern from correctness tests and should report execution time, CPU, memory, scalability, and scheduling-performance metrics.

## Commands

Dependency/environment management is via `uv` (ADR-004). Tests use the standard-library `unittest`:

- Run the full suite: `uv run python -m unittest discover -s tests -v`
- Run a single file: `uv run python -m unittest tests.test_simulation_loop -v`
- Run a single test: `uv run python -m unittest tests.test_simulation_loop.DrainRuleTests.test_drain_is_applied_after_allocate_and_visible_starting_next_tti -v`

No lint or benchmark-runner command is configured yet; update this section when one is added.
