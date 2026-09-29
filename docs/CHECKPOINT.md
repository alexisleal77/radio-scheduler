# Checkpoint — HARNESS6G V21 integration delivery (2026-09-29)

## Where this is

- Branch: `harness6g/v0.1-delivery`, based on `main` at `9be0277` (unchanged;
  never merged automatically, per the master prompt's own instruction).
- HEAD at this checkpoint: `25bf6b2`.
- Working tree: clean except `AGENTS.md` (a pre-existing, untracked
  Codex-facing guidance file — never modified this session).
- Push status: **not yet pushed** at the time this file was written; see
  "Next step" below for the exact command, or the final chat report for
  whether it was pushed by the time this session ended.

## Commits on this branch, in order

1. `f7f7680` — docs: correct `scripts/` implementation status (README.md,
   docs/architecture.md said `run_benchmark.py` didn't exist; it did).
2. `03cb539` — docs(adr): ADR-011, HARNESS6G namespace and boundary.
3. `1866fe4` — docs(design): `docs/design.md` (component / environment /
   HARNESS6G architectures, ADR classification table).
4. `5ac41dd` — feat(demo): Delivery A (`radio_scheduler.demo`,
   `scripts/demo.py`, `evidence/demo/`). 190 tests (181 + 9).
5. `5e06ec9` — feat(harness6g): Delivery B (`radio_scheduler.harness6g`,
   `scripts/harness6g_demo.py`, `evidence/harness6g/`). 214 tests (190 + 24).
6. `25bf6b2` — feat(baseline): Delivery C (`radio_scheduler.baseline`,
   `scripts/baseline_run.py`, `evidence/baseline/`, one real `claude -p`
   invocation). 221 tests (214 + 7).

## Commands run and their actual results

```
uv run python -m unittest discover -s tests -v   # 221 tests, OK (final run)
uv run python scripts/demo.py                     # wrote evidence/demo/{results.json,relatorio.md}
uv run python scripts/harness6g_demo.py           # wrote evidence/harness6g/demo-20260929T230957Z/
uv run python scripts/baseline_run.py             # wrote evidence/baseline/baseline-claude-code-native-4b22db6bc358/
```

Test count progression this session: 181 (start) → 190 → 214 → 221. Every
full-suite run passed; none was edited to hide a regression.

## Directed audit — findings and resolution

| Finding | Action | Resolved in |
|---|---|---|
| README.md / docs/architecture.md said `scripts/` unimplemented | Corrected wording | `f7f7680` |
| No harness/candidate/baseline existed | Built `harness6g` and `baseline` from scratch | `5e06ec9`, `25bf6b2` |
| `domain` module has no README | Not addressed — out of scope for this delivery, not a demo blocker | Left open (see below) |

## What is done vs. still open (Definition-of-Done honesty)

**Done, with evidence:**
- Checkpoint confirmed, prior work preserved, no destructive git operation
  used.
- Component / environment / HARNESS6G architectures distinguished in
  `docs/design.md`, with ADRs classified (ADR-011 added for HARNESS6G's
  own boundary decision — the only new ADR this delivery required).
- Round Robin, Proportional Fair, MaxCQI run over identical scenarios with
  independent initial state (`scripts/demo.py`), oracle-asserted decisions,
  real computational-cost measurements, structured JSON + Portuguese
  report.
- A minimal harness flow actually runs: candidate → checks → freeze,
  proven with one accepted and one deliberately rejected (duplicate
  Resource Block) candidate, plus a proven real-timeout case.
- Candidate origin (replay vs. live) is explicit everywhere it appears;
  no fixture is presented as LLM-generated.
- The specialized-model adapter's status (not qualified/connected) is
  explicit in `docs/proposal-traceability.md`.
- The baseline entry is executable and was exercised with one real, live
  `claude -p` invocation — not only a stub — landing in the same evaluator
  contract as HARNESS6G candidates.
- A joint results table exists (`docs/demo.md` §4); adding a configuration
  does not require changing the task, contract, or evaluator.
- Public/demo checks and protected evaluation are structurally separate
  (`evaluate_public` vs. `evaluate_protected`, the latter always refusing);
  nothing here is presented as the final protected experiment.
- Frozen-candidate integrity is verified before evaluation
  (`verify_integrity`), in both the harness and baseline flows.
- Relevant tests plus the full suite were run at each delivery boundary
  and at this checkpoint; results reported above, not summarized away.
- Reproducible commands, a Portuguese report/guide (`docs/demo.md`), and a
  presentation script for advisors all exist.
- Evidence is tied to versions/hashes/configuration (git commit,
  `frozen_manifest.json` content hash, `BenchmarkResult` provenance
  fields).

**Still open, named explicitly (not silently dropped):**
- No specialized model (e.g. OTel 2.0) is qualified or connected —
  `harness6g` runs in demo/replay mode only.
- No protected evaluator process/package exists; `evaluate_protected`
  always refuses by design, not by omission.
- Only one baseline configuration (`claude-code-native`) has a real,
  executed invocation; a second (`codex`) is designed for in
  `baseline/README.md` but not implemented.
- `domain` module still has no `README.md` (pre-existing gap, not
  reopened or fixed by this delivery).
- The final comparative experiment (task/repetition counts, statistical
  plan, formal protected acceptance protocol) is explicitly out of this
  delivery's scope, reserved for the V21 protocol and advisor review.
- The `docs/adr/` physical-foldering request (car/road/harness
  subdirectories) was raised mid-session and deliberately deferred at the
  user's own choice — flat `docs/adr/` plus the classification table in
  `docs/design.md` §4 is the current, intentional state, not an oversight.

## Exact point to resume from

1. If picking up mid-review: read this file, then
   `docs/proposal-traceability.md`'s "Open, decision-dependent items" —
   those are the only legitimate next-step candidates; do not restart the
   audit.
2. Immediate candidates, in order of how self-contained they are:
   - Push `harness6g/v0.1-delivery` to `origin` if not already done (`main`
     stays untouched; this is a normal, non-force push to a new branch).
   - Decide, with the user, whether to act on the deferred ADR-foldering
     request now.
   - Add `domain/README.md` (pure documentation, no design question).
   - Implement a second baseline adapter (e.g. `codex`) following the
     pattern documented in `src/radio_scheduler/baseline/README.md`.
3. Anything touching the specialized-model connection, the protected
   evaluator, or the final experiment's statistical design needs an
   explicit decision from Alexis (and, where architecturally significant,
   advisor review) before any code is written — per this project's
   established ADR-before-implementation rhythm.
