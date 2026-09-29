# HARNESS6G V21 — proposal traceability

Links every V21 commitment this delivery addresses to a concrete mechanism,
file, and piece of evidence — never a document alone standing in for a
working mechanism. States used below: **implemented and executed**
(mechanism exists and has actually been run, with evidence to show for
it), **implemented, not executed** (code exists but has not been run for
real evidence), **planned** (named, not yet built), **dependent on
decision/infrastructure** (blocked on something outside this repository's
control — an advisor decision, a protected package, a qualified model).

This is a snapshot as of commit `25bf6b2` on branch `harness6g/v0.1-delivery`
(2026-09-29). It does not reopen or restate the V21 document's own content,
chapters, questions, or hypothesis — see `HARNESS6G_v21_FINAL.pdf` for
those; chapters 4-6 remain provisional there, and nothing here changes
that.

## SRQ1 — task specification, software boundary, acceptance criteria

| Requirement | Mechanism | File | Evidence | State |
|---|---|---|---|---|
| Task specification, versioned | `TaskSpec` (`task_id`, `task_version`, `interface_version`) | `src/radio_scheduler/harness6g/task_spec.py` | `tests/test_harness6g.py::TaskSpecValidationTests` | Implemented and executed |
| Software boundary (what a candidate is) | `SchedulingAlgorithm` Protocol (ADR-008), unchanged for candidates | `src/radio_scheduler/scheduling_interface/scheduling_algorithm.py` | Reused by every check (`_check_runner.py`) and by the real baseline candidate | Implemented and executed |
| Acceptance criteria, four categories | `build_validity`, `interface_conformance`, `served_ue_must_have_backlog` (functional_correctness), `no_eligibility_or_resources_yields_empty_decisions` (domain_conformance) | `src/radio_scheduler/harness6g/_check_runner.py` | `evidence/harness6g/demo-*/evidence.json`, `evidence/baseline/*/record.json` (both show all four categories) | Implemented and executed |

## SRQ2 — harness responsibilities and execution records

| Requirement | Mechanism | File | Evidence | State |
|---|---|---|---|---|
| Context authorized to the candidate | `TaskSpec.exposed_context` (points only at `scheduling_interface` and the public demo scenarios — never protected material) | `task_spec.py` | `default_scheduling_candidate_task()` | Implemented and executed |
| State (revisions, corrections) | `RunState`, `Observation`, explicit and immutable, threaded per revision | `run_state.py`, `orchestrator.py` | `tests/test_harness6g.py::RunHarness6GOrchestrationTests` | Implemented and executed |
| Tools / materialization scope | Scope-checked candidate loading (`editable_scope` containment) | `candidate.py` | `tests/test_harness6g.py::CandidateScopeTests`; baseline's own `git status --porcelain` scope check in `baseline/runner.py` | Implemented and executed |
| Feedback (structured, per check) | `CheckResult` list per revision, JSON from the isolated check subprocess | `_check_runner.py`, `checks.py` | `evidence/harness6g/demo-*/evidence.json` | Implemented and executed |
| Termination policy and actual reason | Five distinct `termination_reason` values (`checks_passed`, `revisions_exhausted`, `max_revisions_exceeded`, `timeout`, plus scope/build failures folded into per-revision observations) | `orchestrator.py` | `tests/test_harness6g.py` (one test per reason) | Implemented and executed |
| Provenance (hashes, interface identity) | `freeze_candidate` manifest: content sha256, interface version, Python/platform identity | `freeze.py` | `evidence/harness6g/demo-*/frozen_manifest.json` | Implemented and executed |

Everything in this section runs in **demo/replay mode**: no specialized
model (e.g. OTel 2.0) is connected. See "Open, decision-dependent items"
below.

## SRQ3 — terminal results from both configurations, common evaluation

| Requirement | Mechanism | File | Evidence | State |
|---|---|---|---|---|
| Candidate materialization (HARNESS6G side) | `run_harness6g()` over fixture revisions | `harness6g/orchestrator.py` | `evidence/harness6g/demo-*/` | Implemented and executed (replay mode) |
| Candidate materialization (baseline side) | `run_baseline()`, isolated git worktree, real `claude -p` invocation | `baseline/runner.py` | `evidence/baseline/baseline-claude-code-native-4b22db6bc358/` | Implemented and executed (one real, live invocation) |
| Common configuration-identity contract (`configuration_id, task_id, task_version, base_commit, interface_version, editable_scope, exposed_context, exposed_checks, stopping_policy, resource_policy, agent_version, model_identity, invocation_mode`) | `BaselineConfiguration` | `baseline/configuration.py` | `record.json` in the evidence above | Implemented and executed |
| Common terminal-record contract (`run_id, configuration_id, task_id, terminal_candidate, terminal_hash, termination_reason, evidence_manifest`) | `run_baseline()`'s returned `record` dict | `baseline/runner.py` | Same `record.json` | Implemented and executed |
| Same evaluator for both configurations | `evaluate_public()` called identically from the baseline runner and available to any HARNESS6G run | `harness6g/evaluator.py` | Both evidence directories show identical `"categories"` keys, produced by the same function | Implemented and executed |
| Joint demonstration table (configuration/origin/mode/evidence) | `docs/demo.md`'s results table | `docs/demo.md` | — | Implemented and executed |
| **Protected evaluation** (separate from the generator, final acceptance) | `evaluate_protected()` — always raises `ProtectedEvaluationUnavailable` | `harness6g/evaluator.py` | `tests/test_harness6g.py::EvaluatorTests::test_evaluate_protected_always_refuses` | **Dependent on decision/infrastructure** — no protected package or isolated evaluator process exists; none is fabricated here |
| Final comparative experiment (H1) | — | — | — | **Planned** — reserved for the V21 protocol and advisor review; this delivery's checks/tests are demo/public evidence, never presented as H1 support |

## Other V21 §10 commitments (cutting across SRQ1-3)

| Requirement | Mechanism | File | Evidence | State |
|---|---|---|---|---|
| Editable-scope / permitted-actions manifest | `TaskSpec.editable_scope` + `ResourcePolicy` (explicit `enforced=False` fields, not silent) | `task_spec.py` | `harness6g/README.md` "What is, and is not, isolated" | Implemented and executed |
| Revisions with parentage, changed files, hashes | `Observation.candidate_hash` per revision index | `run_state.py` | `evidence/harness6g/demo-*/evidence.json` | Implemented and executed |
| Frozen terminal candidate per execution | `freeze_candidate` + `verify_integrity` | `freeze.py` | Both evidence directories | Implemented and executed |
| Evidence package linking task/revisions/checks/candidate | `evidence.json` (HARNESS6G) / `record.json` (baseline) | `orchestrator.py`, `baseline/runner.py` | Both evidence directories | Implemented and executed |

## Known v0.1 limitations (never silently omitted)

- `pipeline_delay` supports only `0` (ADR-009); `d >= 1` remains future work.
- `Buffer` drain is binary, not a physical-capacity model (ADR-009); CQI
  has no rate/capacity conversion (ADR-006) — Proportional Fair's use of
  CQI as an achieved-throughput proxy is documented, not presented as a
  real measurement.
- `benchmark` measures computational cost only (ADR-010) — no
  `SchedulingPerformanceMetric` (throughput/fairness/latency) is computed
  anywhere in this delivery.
- `harness6g`'s isolation is a materialization-scope check plus a
  subprocess timeout — not filesystem/network sandboxing, not a
  memory/CPU bound (`ResourcePolicy.memory_bound_enforced = False`,
  `cpu_bound_enforced = False`).
- Only one baseline configuration (`claude-code-native`) has been
  exercised with a real invocation; a second (e.g. `codex`) is designed
  for but not implemented (`baseline/README.md`).

## Open, decision-dependent items (not part of this delivery's Definition of Done)

- Qualifying and connecting a specialized model (e.g. OTel 2.0) to
  HARNESS6G's candidate-generation loop.
- Building a genuinely separate protected-evaluator process/permission
  boundary and a protected test package.
- The final comparative experiment: task/repetition counts, statistical
  plan, and formal acceptance protocol — reserved for review with
  Cristiano Bonato Both and Antonio M. Alberti per the V21 document's own
  chapters 4-6.
