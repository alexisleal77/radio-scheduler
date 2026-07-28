# ADR-004: Implementation language and dependency tooling — Python + uv

## Status

Accepted

## Date

2026-07-28

## Context

`docs/architecture_review.md` deliberately deferred the implementation language, listing it as an unresolved decision to be made only after the architecturally significant questions it depends on were settled. `docs/adr/README.md` names the implementation language explicitly as an example of a decision that warrants an ADR.

By this point, the closed-loop simulation model (ADR-002), the configurable scheduling pipeline delay (ADR-003), the canonical serialization format (ADR-001), and the domain model (`docs/specification/domain-model-v0.1.md`) are all settled. Implementation of the first module, `scenario_generator`, requires a concrete language and a way to manage dependencies and environments — including a decision on how that environment is reproduced across machines and contributors, since reproducibility is a stated design principle of the project (`docs/architecture.md`, and Design Principle 4 of the domain model).

## Decision

Radio Scheduler is implemented in **Python**, using **uv** for dependency and environment management (virtual environment creation plus a committed lockfile).

## Alternatives considered

- **Go** (language) — stronger raw performance and static typing, good for the system-cost benchmarking goal. Rejected because its scientific/numeric ecosystem (no NumPy-equivalent) is far weaker, and algorithm prototyping is more verbose — a poor fit for a project whose reference implementations are meant to double as readable worked examples.
- **Rust** (language) — the best raw performance and memory safety of the candidates considered, ideal for precise system-cost measurement. Rejected because of its steep learning curve and slower prototyping speed, which would work against the project's incremental, small-step development style, and would reduce the readability of reference implementations as examples for future (including AI-generated) algorithm contributions.
- **Poetry** (tooling) — a mature, widely used alternative offering the same core capability (dependency resolution, lockfile, packaging). Rejected in favor of uv's speed and its emergence as the modern default for new Python projects, though it remains a reasonable fallback if uv proves inadequate.
- **pip + venv + requirements.txt** (tooling) — the simplest option, requiring no additional tool. Rejected because a plain `requirements.txt` does not by itself guarantee a fully resolved, hashed lockfile of transitive dependencies — weakening the reproducibility guarantee the project has already committed to elsewhere.

## Consequences

- Python's scientific ecosystem (NumPy, SciPy, pandas, etc.) becomes available for scenario generation, metrics computation, and benchmark reporting.
- Python's runtime performance is weaker than Go or Rust; system-cost benchmarking (execution time, CPU, memory — explicit project goals) must account for this when interpreting absolute numbers, e.g. through vectorization or an explicit, documented measurement methodology, rather than treating raw wall-clock time as directly comparable to a compiled-language baseline.
- `uv` becomes the standard tool for setting up the development environment; `CLAUDE.md`'s "Commands" section (currently a placeholder) should be updated with concrete `uv` commands once the project is initialized.
- A `pyproject.toml` and a committed `uv.lock` become part of the repository, giving every contributor (human, CI, or otherwise) an identical resolved environment.
- Because reference implementations are meant to be readable worked examples — including for future AI-generated algorithms — Python's readability is expected to lower the barrier to that stated project goal.

## Validation criteria

Two different machines running `uv sync` from the committed lockfile produce environments with identical resolved package versions; scenario generation output is reproducible across those environments given the same seed.

## Related documents

- [`docs/architecture_review.md`](../architecture_review.md) — original deferral of the implementation language decision.
- [`docs/adr/README.md`](README.md) — implementation language named as a canonical example warranting an ADR.
- [`docs/specification/domain-model-v0.1.md`](../specification/domain-model-v0.1.md) — Design Principle 4 (determinism), which this decision's lockfile requirement directly serves.
- [`ADR-001`](ADR-001-json-as-scenario-format.md) — canonical serialization format Scenario Generator output must follow.
