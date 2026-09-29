# harness6g

Minimal, real (not merely documented) implementation of Delivery B of the
HARNESS6G integration: the engineering-harness flow that materializes a
candidate scheduling component inside a restricted scope, runs exposed
checks against it, records structured observations, and — on termination —
freezes a terminal candidate for a separate evaluator. See
[`docs/design.md`](../../../docs/design.md) §3 for how this fits alongside
the scheduling component and the experimental environment, and
[`docs/adr/ADR-011-harness6g-namespace-and-boundary.md`](../../../docs/adr/ADR-011-harness6g-namespace-and-boundary.md)
for why this lives here as a subpackage with a one-way dependency, not a
new top-level package.

**This module runs in demo/replay mode only.** No specialized model (e.g.
OTel 2.0) is qualified or connected — see
[`docs/proposal-traceability.md`](../../../docs/proposal-traceability.md)
for that row's explicit pending status. Every fixture candidate under
`fixtures/candidates/` is a hand-written technical fixture, never presented
as output of a qualified specialized model or as an LLM-generated
component.

## Flow

```
TaskSpec (task_spec.py)
  -> load_candidate_source() + build_candidate_algorithm() (candidate.py)
  -> run_checks_in_subprocess() (checks.py, via _check_runner.py)
  -> RunState / Observation / CheckResult (run_state.py)
  -> freeze_candidate() (freeze.py), on acceptance
  -> evaluate_public() (evaluator.py) — demo/public re-verification only
```

`orchestrator.run_harness6g()` ties this together over an ordered sequence
of candidate-revision source files, stopping at the first revision that
passes every exposed check (`termination_reason="checks_passed"`), when
`stopping_policy.max_revisions` is reached without one passing
(`"max_revisions_exceeded"`), when the supplied revision sequence itself
runs out first (`"revisions_exhausted"`), or the instant a single
revision's check subprocess exceeds `stopping_policy.timeout_seconds`
(`"timeout"` — a genuine OS-level process kill, not an in-process flag; see
`checks.CheckTimeoutError` and `_check_runner.py`).

## The four HARNESS6G acceptance categories, made concrete

| Category | Check | What it actually verifies |
|---|---|---|
| Build validity | `build_validity` | Candidate module imports and its `build_algorithm()` factory returns an object with callable `initial_state`/`allocate` (ADR-008 shape) — enforced by `candidate.build_candidate_algorithm`, not a separate check function. |
| Interface conformance | `interface_conformance` | Running the candidate through `simulation_loop.run()` on two demo scenarios never raises — reuses `simulation_loop`'s own decision validation (unknown/duplicate Resource Block, unknown UE, wrong TTI) for free. |
| Functional correctness | `served_ue_must_have_backlog` | A task-specific rule beyond the generic contract: a UE may only receive a Resource Block in a TTI where its Buffer occupancy is `> 0`. |
| Domain conformance | `no_eligibility_or_resources_yields_empty_decisions` | On the `no_eligibility_or_resources` demo scenario specifically: zero decisions in both boundary conditions (no eligible UE; no Resource Block). |

All four run against the exact same demo scenarios Delivery A already
uses (`radio_scheduler.demo.scenarios`) — never against protected material,
because none exists in this repository (§14 of the HARNESS6G proposal: this
project does not fabricate a protected evaluator to complete the picture).

## What is, and is not, isolated

- **Materialization boundary:** a candidate's source file must resolve
  inside `task_spec.editable_scope` (repository-relative directories) or
  `CandidateBuildError` is raised before any code runs.
- **Execution boundary:** every exposed-check run happens in a fresh OS
  subprocess (`_check_runner.py`, invoked by `checks.run_checks_in_subprocess`),
  bounded by a real `timeout_seconds` that `subprocess.run` enforces by
  killing the child process — proven by `hangs_forever.py` in
  `tests/test_harness6g.py`.
- **Not implemented:** filesystem/network sandboxing, memory/CPU limits
  (`task_spec.ResourcePolicy` fields are explicitly `enforced=False`),
  and a genuinely separate protected-evaluator process/permission
  boundary — `evaluator.evaluate_protected` always raises
  `ProtectedEvaluationUnavailable` rather than pretending to have one.

## Running the demonstration

```
uv run python scripts/harness6g_demo.py
```

Replays two fixture revisions — `broken_duplicate_rb.py` (rejected by
`interface_conformance`) then `valid_first_eligible.py` (accepted, frozen,
and re-verified via `evaluate_public`) — writing
`evidence/harness6g/<run_id>/evidence.json`, `frozen_manifest.json`, and
`frozen_candidate.py`.

## Status

Implemented (v0.1): task manifest + validation, scope-checked candidate
loading, subprocess-isolated checks with real timeout, freeze + integrity
verification, public/demo evaluator entry, protected-evaluator refusal
path. 24 tests in `tests/test_harness6g.py`. Not implemented: a live
connection to a specialized model (pending qualification), a genuinely
separate protected-evaluator process, and resource (memory/CPU) limits.
