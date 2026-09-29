import json
from datetime import datetime, timezone
from pathlib import Path

from radio_scheduler.harness6g.candidate import (
    CandidateBuildError,
    candidate_hash,
    load_candidate_source,
)
from radio_scheduler.harness6g.checks import CheckTimeoutError, run_checks_in_subprocess
from radio_scheduler.harness6g.freeze import freeze_candidate
from radio_scheduler.harness6g.run_state import CheckResult, Observation, RunState
from radio_scheduler.harness6g.task_spec import TaskSpec

_VALID_MODES = ("live", "replay", "import")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def run_harness6g(
    task_spec: TaskSpec,
    candidate_revisions: tuple[Path, ...],
    run_dir: Path,
    mode: str,
) -> dict:
    """Runs the task -> context -> candidate -> checks -> feedback ->
    termination -> freeze flow (HARNESS6G proposal §10) over a fixed, ordered sequence of
    candidate source-file revisions.

    `mode` must be one of "live" (a real candidate-generating invocation
    fed each revision as it is produced), "replay" (a pre-recorded
    sequence of revisions, demonstrating the mechanism without a
    qualified specialized model), or "import" (a single externally
    produced candidate, captured as-is). Recorded verbatim in the
    returned evidence dict so no run is ever ambiguous about its origin
    (HARNESS6G proposal §12) — this function itself never invokes a model; the caller is
    responsible for how `candidate_revisions` was produced.

    Stops as soon as one revision passes every exposed check
    ("checks_passed"), after `task_spec.stopping_policy.max_revisions` is
    reached without one passing ("max_revisions_exceeded"), when the
    supplied sequence itself runs out first ("revisions_exhausted"), or
    the instant any single revision's check subprocess exceeds
    `stopping_policy.timeout_seconds` ("timeout" — the run stops
    immediately, it does not try further revisions).
    """
    if mode not in _VALID_MODES:
        raise ValueError(f"mode must be one of {_VALID_MODES} (got {mode!r})")

    state = RunState()
    accepted_source: Path | None = None
    revisions_to_try = candidate_revisions[: task_spec.stopping_policy.max_revisions]

    for index, candidate_path in enumerate(revisions_to_try):
        try:
            source_text = load_candidate_source(candidate_path, task_spec.editable_scope)
        except CandidateBuildError as exc:
            observation = Observation(
                revision_index=index,
                candidate_hash="",
                check_results=(
                    CheckResult("build_validity", "build_validity", False, str(exc)),
                ),
                timestamp=_now(),
            )
            state = RunState(
                observations=state.observations + (observation,),
                correction_count=state.correction_count + 1,
            )
            continue

        source_hash = candidate_hash(source_text)
        try:
            raw_results = run_checks_in_subprocess(
                candidate_path,
                task_spec.exposed_checks,
                task_spec.stopping_policy.timeout_seconds,
            )
        except CheckTimeoutError as exc:
            observation = Observation(
                revision_index=index,
                candidate_hash=source_hash,
                check_results=(
                    CheckResult("timeout", "timeout", False, str(exc)),
                ),
                timestamp=_now(),
            )
            state = RunState(
                observations=state.observations + (observation,),
                correction_count=state.correction_count + 1,
                termination_reason="timeout",
            )
            break

        check_results = tuple(
            CheckResult(r["check_id"], r["category"], r["passed"], r["detail"])
            for r in raw_results
        )
        observation = Observation(
            revision_index=index,
            candidate_hash=source_hash,
            check_results=check_results,
            timestamp=_now(),
        )
        all_passed = bool(check_results) and all(c.passed for c in check_results)
        state = RunState(
            observations=state.observations + (observation,),
            correction_count=state.correction_count + (0 if all_passed else 1),
        )

        if all_passed:
            accepted_source = candidate_path
            state = RunState(
                observations=state.observations,
                correction_count=state.correction_count,
                termination_reason="checks_passed",
            )
            break

    if state.termination_reason is None:
        if len(candidate_revisions) > len(revisions_to_try):
            state = RunState(
                observations=state.observations,
                correction_count=state.correction_count,
                termination_reason="max_revisions_exceeded",
            )
        else:
            state = RunState(
                observations=state.observations,
                correction_count=state.correction_count,
                termination_reason="revisions_exhausted",
            )

    evidence: dict = {
        "task_id": task_spec.task_id,
        "task_version": task_spec.task_version,
        "interface_version": task_spec.interface_version,
        "mode": mode,
        "termination_reason": state.termination_reason,
        "correction_count": state.correction_count,
        "observations": [
            {
                "revision_index": o.revision_index,
                "candidate_hash": o.candidate_hash,
                "timestamp": o.timestamp,
                "check_results": [
                    {
                        "check_id": c.check_id,
                        "category": c.category,
                        "passed": c.passed,
                        "detail": c.detail,
                    }
                    for c in o.check_results
                ],
            }
            for o in state.observations
        ],
        "frozen_manifest": None,
        "frozen_candidate_path": None,
    }

    if accepted_source is not None:
        manifest = freeze_candidate(accepted_source, task_spec.interface_version, run_dir)
        evidence["frozen_manifest"] = manifest
        evidence["frozen_candidate_path"] = str(run_dir / "frozen_candidate.py")

    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "evidence.json").write_text(json.dumps(evidence, indent=2) + "\n")
    return evidence
