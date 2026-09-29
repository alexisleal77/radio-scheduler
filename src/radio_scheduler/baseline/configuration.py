import subprocess
from dataclasses import dataclass

from radio_scheduler.harness6g import default_scheduling_candidate_task


@dataclass(frozen=True)
class BaselineConfiguration:
    """Everything the HARNESS6G proposal's common entry contract requires to be
    accepted and recorded for one baseline configuration, before any
    invocation happens (HARNESS6G proposal §13's `configuration_id, task_id, ...` list).
    """

    configuration_id: str
    task_id: str
    task_version: str
    base_commit: str
    interface_version: str
    editable_scope: tuple[str, ...]
    exposed_context: tuple[str, ...]
    exposed_checks: tuple[str, ...]
    stopping_policy_timeout_seconds: float
    resource_policy_notes: str
    agent_version: str
    model_identity: str
    invocation_mode: str


def _claude_cli_version() -> str:
    try:
        completed = subprocess.run(
            ["claude", "--version"], capture_output=True, text=True, timeout=10
        )
        return completed.stdout.strip() or "unknown"
    except Exception as exc:
        return f"unavailable ({exc})"


def claude_code_native_configuration(
    base_commit: str,
    editable_scope: tuple[str, ...] = ("candidate.py",),
    timeout_seconds: float = 120.0,
) -> BaselineConfiguration:
    """The one baseline configuration exercised in this delivery: Claude
    Code with its native model/runtime, invoked non-interactively
    (`claude -p`) inside an isolated git worktree checked out at
    `base_commit`. `model_identity` is deliberately not forced via
    `--model` — this project does not presume or select which model is
    active (HARNESS6G proposal §13); it is recorded as "unspecified" rather than
    guessed.
    """
    task = default_scheduling_candidate_task()
    return BaselineConfiguration(
        configuration_id="claude-code-native",
        task_id=task.task_id,
        task_version=task.task_version,
        base_commit=base_commit,
        interface_version=task.interface_version,
        editable_scope=editable_scope,
        exposed_context=task.exposed_context,
        exposed_checks=task.exposed_checks,
        stopping_policy_timeout_seconds=timeout_seconds,
        resource_policy_notes=(
            "single bounded invocation; no memory/CPU limit enforced; "
            "wall-clock bounded by stopping_policy_timeout_seconds via a "
            "real subprocess timeout"
        ),
        agent_version=_claude_cli_version(),
        model_identity=(
            "unspecified (session/account default; --model was not passed, "
            "per instruction not to presume or select an active model)"
        ),
        invocation_mode="cli_print_isolated_worktree",
    )
