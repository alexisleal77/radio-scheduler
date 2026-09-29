# baseline

Delivery C of the HARNESS6G V21 integration: an executable entry point for
the *scientific* baseline the V21 protocol compares HARNESS6G against — a
general-purpose coding agent with its native model/runtime — as distinct
from Round Robin/Proportional Fair/MaxCQI, which are algorithm baselines
used to exercise the environment (see `docs/design.md` §3 and the
distinction table in the V21 prompt's §13).

## What this is, concretely

`claude_code_native_configuration()` (`configuration.py`) describes one
baseline configuration: Claude Code, invoked non-interactively (`claude
-p`), with no `--model` forced — this project does not presume or select
which model is active. `run_baseline()` (`runner.py`):

1. Creates an isolated `git worktree` at a given `base_commit` — the
   development checkout is never touched.
2. Invokes the agent with a prompt describing the same task HARNESS6G
   candidates satisfy (`radio_scheduler.harness6g.default_scheduling_candidate_task`),
   scoped to write exactly one file (`editable_scope`).
3. Verifies via `git status --porcelain` that only that file was touched —
   anything else is an `editable_scope_violation`, recorded explicitly.
4. Freezes the captured candidate and evaluates it through
   `radio_scheduler.harness6g.evaluate_public` — **the exact same
   evaluator entry HARNESS6G candidates use**, not a separate or looser
   one.
5. Always removes the worktree afterward.

Every distinct outcome is a named `termination_reason` —
`worktree_setup_failed`, `timeout`, `no_candidate_produced`,
`editable_scope_violation`, `checks_timeout`, `checks_passed`,
`checks_failed` — never silently collapsed into "it didn't work," and a
missing/failed candidate is recorded as such, never substituted with a
reference algorithm.

## Real invocation vs. tested orchestration

`tests/test_baseline.py` exercises `run_baseline()`'s orchestration logic
(scope-violation detection, missing-candidate handling, timeout handling,
worktree cleanup) with a **stubbed** `invoke_agent` callable — no real
agent call, no API cost, safe to run on every commit.

`scripts/baseline_run.py` performs the **real** invocation:

```
uv run python scripts/baseline_run.py
```

This actually calls the `claude` CLI (bounded by a real subprocess
timeout, default 120s) and costs real time/API usage — it is not part of
`unittest discover` for that reason. One real run's full evidence
(`record.json`, `frozen_candidate.py`, `frozen_manifest.json`, raw
invocation stdout/stderr) is committed under
`evidence/baseline/<run_id>/` as proof the entry actually works end to
end, not only in a stub.

## Adding another configuration

Per the V21 prompt's own guidance, one operational baseline suffices for
this delivery; adding another is meant to be a small adapter, not a
change to the task, interface, or evaluator. Concretely: write a new
`*_configuration()` function returning a `BaselineConfiguration` with a
different `configuration_id`/`agent_version`/`invocation_mode`, and a new
`invoke_*()` callable with the same `(prompt, worktree_dir,
timeout_seconds) -> InvocationResult` shape as
`default_invoke_claude_code` — `run_baseline()` itself does not change.
The `codex` CLI is already present in this environment and is the
natural next candidate for such an adapter; it is not implemented here,
to keep this delivery to the one operational baseline the prompt asks
for.

## Status

Implemented and exercised with one real, live invocation (v0.1):
`claude-code-native` configuration, isolated-worktree capture, scope
violation detection, common-evaluator hand-off. Not implemented: a
second live configuration adapter (documented above as the natural next
step), and any resource (memory/CPU) limit on the invoked agent beyond
the wall-clock timeout.
