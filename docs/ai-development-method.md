# AI development method

The co-advisor asked, in the 2026-09-11 advising meeting, that the LLM
used to *build* this project be distinguished from the LLM that will
*integrate the researched system* (HARNESS6G's candidate-generation loop),
and that the method of using the development agent be recorded. The
primary advisor agreed. This document is that record. It distinguishes three
roles this repository now involves — never conflating them:

| Role | What it does | Where its record lives |
|---|---|---|
| Claude Code, this development session | Builds and corrects the environment and prototype (this file) | This document, git history, `docs/CHECKPOINT.md` |
| HARNESS6G's candidate-generation model | Would produce and revise scheduling-algorithm candidates under `harness6g`'s controlled flow | `docs/proposal-traceability.md` — currently **demo/replay mode**, no specialized model connected |
| The baseline configuration | A general-purpose coding agent (also, concretely, Claude Code — but invoked as a separate, isolated subprocess, not this session) executing the same task | `evidence/baseline/*/record.json`, `src/radio_scheduler/baseline/README.md` |

Using Claude Code to build this project does **not** mean a specialized
model has been integrated into HARNESS6G, and running the baseline
configuration from inside this development session does **not** constitute
a valid final comparison run — both are named explicitly wherever they
appear, per the HARNESS6G proposal's own §4-5 instructions.

## Method for history before this session

This document does not reconstruct prompts, interventions, token
consumption, or decisions from sessions before this one — none of that is
recorded verbatim anywhere in this repository, and inventing it would
misrepresent history as more precisely tracked than it was. What is
verifiable from existing evidence:

- **Git history** (`git log`): every commit message states what changed
  and, in the ADR/spec commits, why. The rhythm visible in that history —
  ADR before implementation for architecturally significant decisions
  (e.g. ADR-009 before `simulation_loop`, ADR-010 before `benchmark`),
  feature and docs as separate commits, incremental single-module
  commits — is the one this session continued.
- **The ADRs themselves** (`docs/adr/`): each records a decision, the
  alternatives weighed, and consequences, as they were reasoned through at
  the time.
- **Known gap:** no per-prompt or per-intervention log exists for
  sessions before this one. If that granularity is needed for the thesis'
  own methodology chapter, it has to be reconstructed from git history's
  own resolution (commit-level, not prompt-level) or tracked going
  forward from here — not fabricated retroactively.

## Method for this session (2026-09-29), recorded going forward

**Trigger.** The user (Alexis Leal) pasted a master prompt ("Prompt mestre
para Claude Code: Radio Scheduler e integração inicial com HARNESS6G",
referencing the HARNESS6G thesis proposal document) instructing continuation from
the real checkpoint, an audit, and delivery of three concrete artifacts
(a demonstrable Radio Scheduler run, a minimal engineering-harness
integration, and an executable baseline entry) without per-increment
confirmation for this scope specifically — a deliberate, explicit,
scoped exception to this repository's usual micro-step/explain-before-edit
rhythm (recorded as the prior default in this session's own working-rules
memory), not a permanent change to it.

**Sequence actually followed** (mirrors the master prompt's own §18):

1. Checkpoint confirmation: `git status`/`log`/`branch -vv` against
   `origin/main`, confirming HEAD at `9be0277`, clean tree except one
   untracked `AGENTS.md` (a Codex-facing guidance file, left untouched).
2. Directed audit: read `README.md`, `docs/architecture.md`,
   `docs/adr/README.md`, ran the full test suite (181 tests, passing) and
   `scripts/run_benchmark.py` for real, found and fixed one documentation
   divergence (`scripts/` described as unimplemented when
   `run_benchmark.py` already existed).
3. A new delivery branch, `harness6g/v0.1-delivery`, created off `main`;
   `main` itself never touched.
4. Design consolidation: `docs/design.md` (component / environment /
   HARNESS6G architectures, Mermaid diagrams) and `ADR-011` (HARNESS6G's
   namespace and one-way dependency), written and committed *before* any
   `harness6g` code, continuing this project's established ADR-first
   rhythm for architecturally significant decisions.
5. One user-directed pause: mid-session, the user asked to physically
   reorganize `docs/adr/` into car/road/harness subfolders — a change the
   master prompt itself had explicitly advised against (to avoid breaking
   ADR history/numbering/links). This was flagged back to the user as a
   direct tension rather than silently resolved either way; the user chose
   to defer it ("pula esta parte, depois a gente vê"), so the ADR
   directory was left flat, classified only by the table in
   `docs/design.md` §4, and the folder reorganization remains unstarted by
   explicit deferral.
6. Delivery A, B, C implemented and tested incrementally, each as its own
   commit(s), full test suite run after each (190, then 214, then 221
   tests — see `docs/CHECKPOINT.md` for the exact commands and outputs).
7. This document, `docs/proposal-traceability.md`, `docs/demo.md`, and
   `docs/CHECKPOINT.md` written last, closing the delivery.

**Human interventions during this session**, each recorded with what
triggered it:

- User relaxed the standing micro-step/explain-before-edit/diff-after-every-change
  rhythm for this repository's *default* going forward (not only for this
  task), stating the project needs to move faster — recorded in this
  session's own working-rules memory with the date and scope of the
  change.
- User authorized continuous execution for this specific delivery via the
  master prompt itself (superseding, for this scope, even the
  per-increment confirmation that would otherwise apply).
- User interrupted mid-implementation to insist tool-permission prompts
  not block progress ("não me peça mais nenhuma autorização"), then
  immediately clarified the scope of that instruction to filesystem access
  strictly within this repository ("só acesse as pastas do radio
  scheduler") — both honored: no path outside
  `/home/alexis/Projetos/radio-scheduler` was read or written during this
  session.
- The ADR-foldering deferral described in step 5 above.

No other correction or rejection occurred during this session's
implementation work; the checks below are what actually verifies the
delivered mechanisms, not a claim that no other decision point existed.

## What a developer needs to specify, provide, execute, and verify

To generate and evaluate one scheduling-algorithm candidate in this
environment, concretely:

1. **Specify** a `TaskSpec` (`task_id`, `task_version`, `interface_version`,
   `editable_scope`, `exposed_context`, `exposed_checks`,
   `stopping_policy`, `resource_policy`) — or reuse
   `harness6g.default_scheduling_candidate_task()`, the one task this
   delivery demonstrates.
2. **Provide** one or more candidate source files, each exposing a
   module-level `build_algorithm()` factory returning an object with
   `initial_state()`/`allocate()` (the same `SchedulingAlgorithm` shape
   every reference implementation already satisfies) — via live
   generation, a replayed sequence, or a single imported file. The mode
   must be named (`"live"`, `"replay"`, or `"import"`) when calling
   `run_harness6g()`; it is never left implicit.
3. **Execute** either:
   - `radio_scheduler.harness6g.run_harness6g(task_spec, candidate_revisions, run_dir, mode)`
     for the HARNESS6G-side flow, or
   - `radio_scheduler.baseline.run_baseline(config, repo_root, evidence_root)`
     for a general-purpose-agent baseline configuration.
4. **Verify** by reading the written evidence directory: `evidence.json` /
   `record.json` for the termination reason and per-check results,
   `radio_scheduler.harness6g.verify_integrity(run_dir)` before trusting
   any frozen candidate, and
   `radio_scheduler.harness6g.evaluate_public(run_dir, task_spec)` for the
   four HARNESS6G acceptance categories — understanding that this is a
   demo/public verification, not the protected, final acceptance the HARNESS6G proposal
   protocol reserves for a separately-controlled evaluator
   (`evaluate_protected()` always refuses in this repository; see
   `docs/proposal-traceability.md`).
