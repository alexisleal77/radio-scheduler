# Demonstration guide

Exact commands to reproduce every piece of evidence this delivery
produced, what to expect, how to interpret it, and a short script for
presenting it to advisors. See `docs/design.md` for the architecture
behind these commands and `docs/proposal-traceability.md` for how each
piece maps to a V21 commitment.

## 0. Environment check

```
uv run python -m unittest discover -s tests -v
```

Expected: all tests pass (221 as of this delivery — see
`docs/CHECKPOINT.md` for the exact count and command output at the
checkpoint commit). This is the same command named in `CLAUDE.md`/`AGENTS.md`.

## 1. Delivery A — demonstrable Radio Scheduler run

```
uv run python scripts/demo.py
```

Writes `evidence/demo/results.json` and `evidence/demo/relatorio.md`.
Runs Round Robin, Proportional Fair, and MaxCQI over three small,
hand-built scenarios (`ue_competition`, `cqi_difference`,
`no_eligibility_or_resources` — see
`src/radio_scheduler/demo/scenarios.py` for why each was chosen), records
the exact per-TTI decision trace, and benchmarks computational cost via
the existing `benchmark.benchmark_run()`.

**How to interpret it:** the decision trace is deterministic and must
match `tests/test_demo.py`'s oracle exactly (re-running the script never
changes *which* UE gets served — only wall-time/CPU/memory numbers can
vary run to run, since those are real measurements of this machine, not
data). The report's own "Limitações conhecidas" section is not
boilerplate — it names exactly what this benchmark does not measure
(throughput, fairness, packet latency).

## 2. Delivery B — HARNESS6G engineering-harness flow (replay mode)

```
uv run python scripts/harness6g_demo.py
```

Writes `evidence/harness6g/demo-<timestamp>/{evidence.json,
frozen_manifest.json, frozen_candidate.py}`. Replays two fixture
candidates in order: `broken_duplicate_rb.py` (rejected —
`interface_conformance` fails with the exact `ValueError` `simulation_loop`
raises for a duplicated Resource Block) then `valid_first_eligible.py`
(accepted, frozen, then re-verified through `evaluate_public`).

**How to interpret it:** this is **replay mode** — no specialized model
was invoked; both candidates are hand-written fixtures
(`src/radio_scheduler/harness6g/fixtures/candidates/`), used only to
prove the materialize→check→freeze→evaluate pipeline actually runs and
actually rejects a bad candidate, not to claim an LLM produced them. The
timeout mechanism (`hangs_forever.py`) is proven in
`tests/test_harness6g.py::CheckSubprocessTests::test_hanging_candidate_is_really_interrupted_by_timeout`
rather than in this script, to keep the demo's own runtime short.

## 3. Delivery C — baseline entry (real, live invocation)

```
uv run python scripts/baseline_run.py
```

Real invocation — costs API usage and wall-clock time (bounded to 120s by
`stopping_policy_timeout_seconds`), unlike the two commands above. Creates
an isolated `git worktree` at the current commit, invokes `claude -p`
non-interactively with a prompt describing the same task HARNESS6G
candidates satisfy, captures whatever file it wrote, verifies no other
file was touched, freezes the candidate, and evaluates it through the
same `evaluate_public()` HARNESS6G uses.

**Evidence already committed** from one such run:
`evidence/baseline/baseline-claude-code-native-4b22db6bc358/`. That run's
agent produced a self-contained, memory-less Max-CQI-style scheduler
(`frozen_candidate.py`) that passed all four acceptance categories.

**How to interpret it:** this is one operational baseline configuration,
invoked once. It demonstrates that the entry works end to end — task in,
real agent, real candidate, same evaluator — not a statistically
meaningful comparison. See `docs/proposal-traceability.md`'s SRQ3/H1 rows
for what remains explicitly out of scope here.

## 4. Joint results table

| Configuration | Origin/mode | Termination | Categories (public/demo) | Evidence |
|---|---|---|---|---|
| HARNESS6G replay, revision 0 (`broken_duplicate_rb.py`) | replay | rejected (interface_conformance fails) | build_validity ✅ / interface_conformance ❌ / functional_correctness ❌ / domain_conformance ❌ | `evidence/harness6g/demo-20260929T230957Z/evidence.json` |
| HARNESS6G replay, revision 1 (`valid_first_eligible.py`) | replay | checks_passed, frozen | all four ✅ | same file |
| Baseline `claude-code-native` | live invocation | checks_passed, frozen | all four ✅ | `evidence/baseline/baseline-claude-code-native-4b22db6bc358/record.json` |

Adding another baseline configuration (e.g. a `codex` adapter — the CLI is
already present in this environment, see `src/radio_scheduler/baseline/README.md`)
adds a row to this table without changing the task, the interface, or the
evaluator.

## 5. Known limitations (repeated here deliberately — see `docs/proposal-traceability.md` for the full list)

- Computational-cost benchmark only; no radio-performance metrics
  (throughput, fairness, packet latency).
- `harness6g`'s isolation is a scope check plus a subprocess timeout, not
  full sandboxing; no memory/CPU bound is enforced.
- No specialized model is connected to HARNESS6G; only one baseline
  configuration has been exercised with a real invocation.
- No protected evaluator exists in this repository — every check shown
  above is explicitly public/demo, never final protected acceptance.

## Presentation script (for advisors)

1. **The component and its contract** — `docs/design.md` §1: show
   `SchedulingAlgorithm` (`scheduling_interface/scheduling_algorithm.py`)
   and one reference implementation.
2. **The experimental environment** — `docs/design.md` §2: run
   `scripts/demo.py`, show the decision trace and computational-cost
   numbers for the three scenarios.
3. **A concrete execution** — open `evidence/demo/relatorio.md` and walk
   through one scenario's table.
4. **The candidate flow** — run `scripts/harness6g_demo.py` live, showing
   one rejection and one acceptance in the same run.
5. **The V21 commitments implemented** — `docs/proposal-traceability.md`,
   scanning the "Implemented and executed" rows and naming the
   "dependent on decision/infrastructure" ones explicitly (protected
   evaluator, specialized model, final comparative protocol).
6. **The baseline entry** — `evidence/baseline/.../record.json`, and the
   joint table in §4 above.
7. **Open scientific decisions** — read directly from
   `docs/proposal-traceability.md`'s last section: qualifying a
   specialized model, building a genuinely separate protected evaluator,
   and the final experiment's task/repetition/statistical plan, all
   reserved for review with the thesis advisors.
