# ADR-011: HARNESS6G namespace and boundary within Radio Scheduler

## Status

Accepted

## Date

2026-09-29

## Context

The HARNESS6G proposal (V21) requires an engineering-harness integration whose responsibilities — validating a task manifest, materializing a candidate scheduling algorithm inside a restricted scope, running exposed checks against it, recording structured observations, freezing a terminal candidate, and handing it to a separate evaluator — are distinct from both:

1. the scheduling *component* (`reference_implementations`, built against the `scheduling_interface` contract, ADR-008), and
2. the experimental *environment* that exercises it (`scenario_generator`, `simulation_loop`, `benchmark`).

This mirrors the distinction the primary advisor raised in the 2026-09-11 advising meeting (car vs. road/track): the harness is a third thing again — it is not the algorithm, and it is not the environment that runs the algorithm; it is the machinery that produces and gates a candidate *before* the environment ever sees it. The co-advisor separately asked that documents stop mixing components, general architecture, functionality, and implementation; the same request applies to code layout, not only prose.

At the same time, `radio-scheduler`'s packaging is deliberately minimal (ADR-004): a single distributable package, `src/radio_scheduler/`, with no `[tool.hatch.build]` package list in `pyproject.toml` (Hatchling auto-detects the one package). Introducing a second top-level distributable package (`src/harness6g/`) would require an explicit multi-package build configuration change with no current external consumer needing that split — HARNESS6G v0.1 is used only from within this repository (scripts/tests), not installed independently elsewhere.

## Decision

**`harness6g` is a subpackage of the existing package: `src/radio_scheduler/harness6g/`.** It is not a new top-level distributable package, and it is not folded into `scheduling_interface`, `simulation_loop`, `reference_implementations`, or `benchmark`.

The dependency direction is one-way and enforced by convention (checked by the validation criteria below, not by a build-time boundary):

- `radio_scheduler.harness6g` may import from `domain`, `scheduling_interface`, `simulation_loop`, `reference_implementations`, and `benchmark`.
- None of `domain`, `scheduling_interface`, `simulation_loop`, `reference_implementations`, or `benchmark` may import from `harness6g`.

A candidate scheduling algorithm materialized and frozen by `harness6g` must still satisfy the existing `SchedulingAlgorithm` contract (ADR-008) unchanged. `harness6g` does not define a competing or looser contract for candidates — it only adds materialization, checking, and provenance machinery *around* that same contract.

`harness6g`'s own tests live in `tests/test_harness6g.py`, alongside every other module's tests, under the single `unittest discover -s tests` root (`CLAUDE.md`) — no separate test runner or discovery root.

## Alternatives considered

- **Separate top-level package/distribution (`src/harness6g/`).** Rejected for v0.1: would need an explicit Hatchling multi-package build configuration and its own packaging metadata, for no current external consumer. Revisit if HARNESS6G ever needs to be installed or versioned independently of `radio-scheduler`.
- **Separate git repository.** Rejected: the proposal's own guidance frames the component/environment/harness separation as logical and documentary, not physical ("não exige mover todos os arquivos ou criar repositórios diferentes"). A separate repository would either duplicate `domain`/`scheduling_interface` types or take a hard cross-repository dependency on them, adding release-coordination overhead disproportionate to v0.1's scope.
- **Fold harness mechanisms into `scheduling_interface` or `simulation_loop`.** Rejected: conflates the contract a candidate implements (what the algorithm *is*) with the machinery that generates, checks, freezes, and evaluates candidates (what happens *around* the algorithm before the environment ever runs it) — the exact confusion the car/harness distinction warns against.

## Consequences

- Adding `harness6g` requires no change to `pyproject.toml`'s build configuration, since it lives inside the already-packaged `radio_scheduler` tree.
- A future split to a genuinely separate top-level package remains possible without changing the one-way dependency rule — only the import paths would change.
- Any import of `radio_scheduler.harness6g` from `domain`, `scheduling_interface`, `reference_implementations`, `simulation_loop`, or `benchmark` is an architecture violation under this ADR, even though nothing currently enforces it mechanically (see Validation criteria).
- `harness6g` fixtures (demo/replay candidates, sample task manifests) are technical fixtures for exercising the harness, not scientific artifacts — they must never be described as LLM-generated candidates from a qualified specialized model (see `docs/design.md` and `docs/demo.md`).

## Validation criteria

- `grep -rl "harness6g" src/radio_scheduler/domain src/radio_scheduler/scheduling_interface src/radio_scheduler/reference_implementations src/radio_scheduler/simulation_loop src/radio_scheduler/benchmark` returns nothing.
- Every candidate accepted by `harness6g`'s candidate loader satisfies the same structural check (`initial_state`/`allocate` signatures) that `scheduling_interface.SchedulingAlgorithm` already defines — no parallel/looser Protocol is introduced.
- `harness6g`'s tests run and are discovered by the same `uv run python -m unittest discover -s tests -v` command as every other module's tests, with no separate configuration.

## Related documents

- [`ADR-004`](ADR-004-implementation-language-and-tooling.md) — single-package Hatchling layout this decision keeps intact.
- [`ADR-005`](ADR-005-domain-module.md) — `domain` as the shared entity owner `harness6g` depends on like every other module.
- [`ADR-008`](ADR-008-scheduler-statefulness.md) — the `SchedulingAlgorithm` contract candidates must satisfy; `harness6g` adds machinery around it, not an alternative to it.
- [`docs/design.md`](../design.md) — component / experimental-environment / HARNESS6G architecture split this ADR makes concrete in code.
