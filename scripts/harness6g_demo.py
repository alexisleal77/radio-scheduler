"""HARNESS6G v0.1 demonstration entry point (Delivery B): runs the
task -> candidate -> checks -> feedback -> termination -> freeze flow in
REPLAY mode over a fixed sequence of pre-recorded candidate revisions
(src/radio_scheduler/harness6g/fixtures/candidates/) — no specialized
model is invoked or claimed here. Revision 0 is a deliberately broken
candidate (duplicate Resource Block assignment), rejected by
interface_conformance; revision 1 is a correct candidate, accepted and
frozen, then re-verified through the public/demo evaluator entry.

Thin wrapper: all materialization/check/freeze/evaluation logic lives in
radio_scheduler.harness6g; this script only orchestrates run_harness6g()
and evaluate_public(), printing a small Portuguese summary alongside the
JSON evidence run_harness6g() already writes to evidence/harness6g/.
"""

from datetime import datetime, timezone
from pathlib import Path

from radio_scheduler.harness6g import (
    default_scheduling_candidate_task,
    evaluate_public,
    run_harness6g,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
FIXTURES_DIR = REPO_ROOT / "src" / "radio_scheduler" / "harness6g" / "fixtures" / "candidates"
EVIDENCE_ROOT = REPO_ROOT / "evidence" / "harness6g"


def main() -> None:
    task = default_scheduling_candidate_task()
    run_id = "demo-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir = EVIDENCE_ROOT / run_id

    revisions = (
        FIXTURES_DIR / "broken_duplicate_rb.py",
        FIXTURES_DIR / "valid_first_eligible.py",
    )
    evidence = run_harness6g(task, revisions, run_dir, mode="replay")

    print(
        "HARNESS6G v0.1 — execucao de demonstracao (modo replay; nenhum "
        "modelo especializado foi invocado)"
    )
    print(f"run_id: {run_id}")
    print(f"task_id: {evidence['task_id']} v{evidence['task_version']}")
    print(f"motivo de termino: {evidence['termination_reason']}")
    print()

    for observation in evidence["observations"]:
        candidate_hash = observation["candidate_hash"][:12] or "(sem hash)"
        print(f"Revisao {observation['revision_index']} (hash {candidate_hash}):")
        for check in observation["check_results"]:
            status = "PASSOU" if check["passed"] else "FALHOU"
            print(f"  [{status}] {check['check_id']} ({check['category']}): {check['detail']}")
        print()

    if evidence["frozen_manifest"]:
        print(f"Candidato terminal congelado em: {evidence['frozen_candidate_path']}")
        print(f"hash sha256: {evidence['frozen_manifest']['content_sha256']}")
        eval_report = evaluate_public(run_dir, task)
        print(
            "Avaliacao publica/demo (nao e aceitacao protegida final): "
            f"integridade_ok={eval_report['integrity_ok']}, "
            f"categorias={eval_report['categories']}"
        )
    else:
        print("Nenhum candidato foi congelado nesta execucao.")

    print(f"\nEvidencia completa: {run_dir / 'evidence.json'}")


if __name__ == "__main__":
    main()
