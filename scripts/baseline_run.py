"""Baseline entry point (Delivery C of the HARNESS6G V21 integration): runs
the claude-code-native configuration — Claude Code with its native
model/runtime, invoked non-interactively — against the exact same
canonical task HARNESS6G candidates satisfy, inside an isolated git
worktree, and feeds the captured candidate into the same evaluator entry
(radio_scheduler.harness6g.evaluate_public).

This performs one REAL, bounded invocation of the `claude` CLI — not a
replay, not a stub (tests/test_baseline.py exercises the orchestration
logic with a stub agent instead, to keep the automated test suite free of
real, costly agent invocations). See docs/demo.md for interpretation.

Thin wrapper: all worktree/invocation/capture/freeze/evaluation logic
lives in radio_scheduler.baseline and radio_scheduler.harness6g; this
script only orchestrates run_baseline() and prints a summary.
"""

import subprocess
from pathlib import Path

from radio_scheduler.baseline import claude_code_native_configuration, run_baseline

REPO_ROOT = Path(__file__).resolve().parent.parent
EVIDENCE_ROOT = REPO_ROOT / "evidence" / "baseline"


def _current_commit() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()


def main() -> None:
    config = claude_code_native_configuration(base_commit=_current_commit())
    print(f"configuration_id: {config.configuration_id}")
    print(f"agent_version: {config.agent_version}")
    print(f"model_identity: {config.model_identity}")
    print(f"base_commit: {config.base_commit}")
    print(f"invocation_mode: {config.invocation_mode}")
    print(f"timeout_seconds: {config.stopping_policy_timeout_seconds}")
    print("\nInvocando o agente (invocacao real, pode levar ate ~2 minutos)...\n")

    record = run_baseline(config, REPO_ROOT, EVIDENCE_ROOT)

    print(f"run_id: {record['run_id']}")
    print(f"motivo de termino: {record['termination_reason']}")
    if record.get("terminal_hash"):
        print(f"hash do candidato terminal: {record['terminal_hash']}")
    if record.get("scope_violation_paths"):
        print(f"caminhos fora do escopo autorizado: {record['scope_violation_paths']}")
    if record.get("public_evaluation"):
        print(f"avaliacao publica/demo (categorias): {record['public_evaluation']['categories']}")

    print(f"\nRegistro completo: {EVIDENCE_ROOT / record['run_id'] / 'record.json'}")


if __name__ == "__main__":
    main()
