import json
import subprocess
import tempfile
import uuid
from dataclasses import dataclass
from pathlib import Path

from radio_scheduler.baseline.configuration import BaselineConfiguration
from radio_scheduler.harness6g import (
    CheckTimeoutError,
    candidate_hash,
    default_scheduling_candidate_task,
    evaluate_public,
    freeze_candidate,
)

TASK_PROMPT_TEMPLATE = """Voce esta em um checkout git isolado (nao o repositorio de desenvolvimento) do projeto radio-scheduler.

Tarefa: implemente um algoritmo de escalonamento de radio que satisfaca o contrato SchedulingAlgorithm de src/radio_scheduler/scheduling_interface (leia esse diretorio e src/radio_scheduler/demo/scenarios.py para contexto de como ObservableState e AllocationDecision funcionam).

Escreva EXATAMENTE um arquivo novo em {editable_path} contendo:
1. Uma classe com os metodos initial_state(self) e allocate(self, observable_state, scheduler_state), retornando um SchedulingStepResult (importe de radio_scheduler.scheduling_interface e radio_scheduler.domain.AllocationDecision).
2. Uma funcao de nivel de modulo build_algorithm() que retorna uma instancia dessa classe.

Regra funcional obrigatoria: uma UE so pode receber um Resource Block em uma TTI se Buffer.occupancy_bytes > 0 para essa UE naquela TTI (verificavel em observable_state.buffers).

Nao modifique nenhum outro arquivo do repositorio. Nao rode testes nem instale dependencias — apenas escreva o arquivo {editable_path}.
"""


@dataclass(frozen=True)
class InvocationResult:
    """What one agent invocation produced, regardless of success — a
    baseline run must record a real outcome (including failure/timeout),
    never substitute a reference algorithm for a missing candidate."""

    succeeded: bool
    stdout: str
    stderr: str
    timed_out: bool


def default_invoke_claude_code(
    prompt: str, worktree_dir: Path, timeout_seconds: float
) -> InvocationResult:
    """Real, documented, non-interactive invocation: `claude -p`, run from
    the isolated worktree, with `--permission-mode bypassPermissions`
    (safe here because `worktree_dir` is a throwaway git worktree, never
    the development checkout) and tool access restricted to
    Read/Write/Edit. `--model` is deliberately not passed. Bounded by a
    real subprocess timeout, not merely observed after the fact."""
    try:
        completed = subprocess.run(
            [
                "claude",
                "-p",
                prompt,
                "--output-format",
                "json",
                "--permission-mode",
                "bypassPermissions",
                "--allowedTools",
                "Read,Write,Edit",
            ],
            cwd=worktree_dir,
            timeout=timeout_seconds,
            capture_output=True,
            text=True,
        )
        return InvocationResult(
            succeeded=completed.returncode == 0,
            stdout=completed.stdout,
            stderr=completed.stderr,
            timed_out=False,
        )
    except subprocess.TimeoutExpired as exc:
        return InvocationResult(
            succeeded=False,
            stdout=exc.stdout or "",
            stderr=exc.stderr or "",
            timed_out=True,
        )
    except FileNotFoundError:
        return InvocationResult(
            succeeded=False, stdout="", stderr="claude CLI not found on PATH", timed_out=False
        )


def run_baseline(
    config: BaselineConfiguration,
    repo_root: Path,
    evidence_root: Path,
    invoke_agent=default_invoke_claude_code,
) -> dict:
    """Runs one baseline configuration against the same canonical task
    HARNESS6G candidates satisfy, producing the common terminal record
    (V21 §13): `run_id, configuration_id, task_id, terminal_candidate,
    terminal_hash, termination_reason, evidence_manifest`.

    Flow: (1) create an isolated git worktree at `config.base_commit` —
    the development checkout is never touched; (2) invoke the agent
    (`invoke_agent`, real by default, injectable for tests) with a prompt
    describing the task and `config.editable_scope`; (3) verify via `git
    status --porcelain` that only `editable_scope` was touched — anything
    else is an `editable_scope_violation`, recorded, not silently
    ignored; (4) freeze the captured candidate and run it through
    `harness6g.evaluate_public` — the exact same evaluator entry
    HARNESS6G candidates use, never a separate or looser one; (5) always
    remove the worktree afterward, never mutating the development
    checkout.

    Every distinct way this can end is a named `termination_reason`,
    never papered over: `worktree_setup_failed`, `timeout`,
    `no_candidate_produced`, `editable_scope_violation`,
    `checks_timeout`, `checks_passed`, `checks_failed`.
    """
    run_id = f"baseline-{config.configuration_id}-{uuid.uuid4().hex[:12]}"
    run_dir = evidence_root / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    worktree_dir = Path(tempfile.mkdtemp(prefix="radio-scheduler-baseline-"))
    worktree_dir.rmdir()  # git worktree add requires the target path not to exist yet
    editable_path = config.editable_scope[0]

    record: dict = {
        "run_id": run_id,
        "configuration_id": config.configuration_id,
        "task_id": config.task_id,
        "task_version": config.task_version,
        "base_commit": config.base_commit,
        "interface_version": config.interface_version,
        "agent_version": config.agent_version,
        "model_identity": config.model_identity,
        "invocation_mode": config.invocation_mode,
        "terminal_candidate": None,
        "terminal_hash": None,
        "termination_reason": None,
        "evidence_manifest": None,
    }

    try:
        subprocess.run(
            ["git", "worktree", "add", "--detach", str(worktree_dir), config.base_commit],
            cwd=repo_root,
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as exc:
        record["termination_reason"] = f"worktree_setup_failed: {exc.stderr.strip()[-500:]}"
        (run_dir / "record.json").write_text(json.dumps(record, indent=2) + "\n")
        return record

    try:
        prompt = TASK_PROMPT_TEMPLATE.format(editable_path=editable_path)
        invocation = invoke_agent(prompt, worktree_dir, config.stopping_policy_timeout_seconds)
        (run_dir / "invocation_stdout.txt").write_text(invocation.stdout)
        (run_dir / "invocation_stderr.txt").write_text(invocation.stderr)

        if invocation.timed_out:
            record["termination_reason"] = "timeout"
            return record

        candidate_path = worktree_dir / editable_path
        if not candidate_path.is_file():
            record["termination_reason"] = "no_candidate_produced"
            return record

        status = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=worktree_dir,
            capture_output=True,
            text=True,
        )
        changed_paths = {line[3:].strip() for line in status.stdout.splitlines() if line.strip()}
        extra_paths = changed_paths - {editable_path}
        if extra_paths:
            record["termination_reason"] = "editable_scope_violation"
            record["scope_violation_paths"] = sorted(extra_paths)
            return record

        source_text = candidate_path.read_text()
        record["terminal_hash"] = candidate_hash(source_text)

        manifest = freeze_candidate(candidate_path, config.interface_version, run_dir)
        record["terminal_candidate"] = str(run_dir / "frozen_candidate.py")
        record["evidence_manifest"] = manifest

        task = default_scheduling_candidate_task()
        try:
            public_eval = evaluate_public(run_dir, task)
        except CheckTimeoutError:
            record["termination_reason"] = "checks_timeout"
            return record

        record["public_evaluation"] = public_eval
        all_passed = (
            public_eval["integrity_ok"]
            and bool(public_eval["categories"])
            and all(public_eval["categories"].values())
        )
        record["termination_reason"] = "checks_passed" if all_passed else "checks_failed"
        return record
    finally:
        (run_dir / "record.json").write_text(json.dumps(record, indent=2, default=str) + "\n")
        subprocess.run(
            ["git", "worktree", "remove", "--force", str(worktree_dir)],
            cwd=repo_root,
            capture_output=True,
            text=True,
        )
