from pathlib import Path

from radio_scheduler.harness6g.checks import run_checks_in_subprocess
from radio_scheduler.harness6g.freeze import verify_integrity
from radio_scheduler.harness6g.task_spec import TaskSpec


class ProtectedEvaluationUnavailable(Exception):
    """Raised by `evaluate_protected` whenever no protected evaluation
    package/protocol is configured. The formal/protected evaluation path
    must refuse to run rather than silently fall back to public checks
    (HARNESS6G proposal §14-15) — this project has no protected material at all, so this
    exception is the only thing `evaluate_protected` can ever do."""


def evaluate_public(run_dir: Path, task_spec: TaskSpec) -> dict:
    """Demo/public evaluation entry: verifies the frozen candidate's
    integrity, then re-runs the same exposed checks against it —
    deliberately the *same* checks already run during materialization
    (HARNESS6G proposal §14: no protected material exists to separate from here). This
    is explicitly a demonstration verification, never the protected final
    acceptance the HARNESS6G protocol reserves for a separately-controlled
    evaluator."""
    if not verify_integrity(run_dir):
        return {"mode": "public_demo", "integrity_ok": False, "categories": {}}

    frozen_source = run_dir / "frozen_candidate.py"
    results = run_checks_in_subprocess(
        frozen_source,
        task_spec.exposed_checks,
        task_spec.stopping_policy.timeout_seconds,
    )
    categories: dict[str, bool] = {}
    for result in results:
        category = result["category"]
        categories[category] = categories.get(category, True) and result["passed"]
    return {
        "mode": "public_demo",
        "integrity_ok": True,
        "categories": categories,
        "checks": results,
    }


def evaluate_protected(run_dir: Path, protected_package_path: Path | None) -> dict:
    """Always refuses in this repository: there is no protected evaluator
    package, protocol, or isolation mechanism implemented — building one
    would require executing untrusted candidate code outside the
    generator's own reach (HARNESS6G proposal §14), which this v0.1 harness does not
    attempt. Exists so the formal path fails loudly instead of silently
    degrading to the public checks above."""
    raise ProtectedEvaluationUnavailable(
        "no protected evaluation package or protocol is configured for "
        "this repository; formal acceptance cannot proceed here — see "
        "docs/proposal-traceability.md for what remains dependent on "
        "advisor/protocol decisions"
    )
