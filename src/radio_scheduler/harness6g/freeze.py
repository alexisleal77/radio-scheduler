import hashlib
import json
import platform
from pathlib import Path


def compute_manifest(frozen_source_path: Path, interface_version: str) -> dict:
    source_text = frozen_source_path.read_text()
    return {
        "content_sha256": hashlib.sha256(source_text.encode("utf-8")).hexdigest(),
        "interface_version": interface_version,
        "python_implementation": platform.python_implementation(),
        "python_version": platform.python_version(),
        "platform": platform.platform(),
    }


def freeze_candidate(source_path: Path, interface_version: str, run_dir: Path) -> dict:
    """Copies the accepted candidate's source into `run_dir` (so later
    changes to the original file can never retroactively alter what was
    evaluated) and writes a manifest carrying its content hash plus the
    dependency/interface identity it was frozen under (HARNESS6G proposal §10 point 5,
    §12's "congelamento com manifesto e hash")."""
    run_dir.mkdir(parents=True, exist_ok=True)
    frozen_source_path = run_dir / "frozen_candidate.py"
    frozen_source_path.write_text(source_path.read_text())
    manifest = compute_manifest(frozen_source_path, interface_version)
    (run_dir / "frozen_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest


def verify_integrity(run_dir: Path) -> bool:
    """Recomputes the frozen candidate's content hash and compares it to
    its manifest — must be called, and must return True, before any
    evaluation of a frozen candidate (HARNESS6G proposal §12's "verificação de
    integridade antes de qualquer avaliação posterior")."""
    manifest_path = run_dir / "frozen_manifest.json"
    frozen_source_path = run_dir / "frozen_candidate.py"
    if not manifest_path.exists() or not frozen_source_path.exists():
        return False
    manifest = json.loads(manifest_path.read_text())
    recomputed = hashlib.sha256(
        frozen_source_path.read_text().encode("utf-8")
    ).hexdigest()
    return recomputed == manifest.get("content_sha256")
