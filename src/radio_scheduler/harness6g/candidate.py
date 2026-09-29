import hashlib
import importlib.util
from pathlib import Path

from radio_scheduler.scheduling_interface import SchedulingAlgorithm

_REPO_ROOT = Path(__file__).resolve().parents[3]


class CandidateBuildError(Exception):
    """Raised when a candidate source file is outside its task's
    editable_scope, or cannot be loaded / does not expose the required
    `build_algorithm()` factory returning a `SchedulingAlgorithm`-shaped
    object — this is "build validity" (HARNESS6G proposal §15)."""


def candidate_hash(source_text: str) -> str:
    return hashlib.sha256(source_text.encode("utf-8")).hexdigest()


def load_candidate_source(source_path: Path, editable_scope: tuple[str, ...]) -> str:
    """Reads candidate source text, refusing anything whose resolved path
    does not live inside one of `editable_scope`'s repository-relative
    directories — the materialization boundary this v0.1 harness enforces
    (`docs/proposal-traceability.md` names what is and is not a full
    sandbox)."""
    resolved = source_path.resolve()
    allowed = any(
        resolved == (_REPO_ROOT / scoped).resolve()
        or (_REPO_ROOT / scoped).resolve() in resolved.parents
        for scoped in editable_scope
    )
    if not allowed:
        raise CandidateBuildError(
            f"{source_path} is outside the task's editable_scope {editable_scope}"
        )
    if not resolved.is_file():
        raise CandidateBuildError(f"candidate source not found: {source_path}")
    return resolved.read_text()


def build_candidate_algorithm(source_path: Path) -> SchedulingAlgorithm:
    """Loads a candidate module under an isolated module name (derived from
    its own content hash, so two revisions never collide and neither is
    ever registered under a name another module could accidentally
    import) and returns the `SchedulingAlgorithm` its required
    `build_algorithm()` factory produces.

    Does not check `editable_scope` itself — callers that need the scope
    boundary enforced call `load_candidate_source` first (this function is
    also called from the isolated check-runner subprocess, which only
    ever receives an already-scope-checked path from its parent).
    """
    if not source_path.is_file():
        raise CandidateBuildError(f"candidate source not found: {source_path}")

    source_text = source_path.read_text()
    module_name = f"harness6g_candidate_{candidate_hash(source_text)[:16]}"
    spec = importlib.util.spec_from_file_location(module_name, source_path)
    if spec is None or spec.loader is None:
        raise CandidateBuildError(f"cannot load candidate module from {source_path}")
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except Exception as exc:
        raise CandidateBuildError(f"candidate module raised on import: {exc}") from exc

    factory = getattr(module, "build_algorithm", None)
    if factory is None or not callable(factory):
        raise CandidateBuildError(
            "candidate module must define a callable build_algorithm() factory"
        )

    try:
        algorithm = factory()
    except Exception as exc:
        raise CandidateBuildError(f"build_algorithm() raised: {exc}") from exc

    if not callable(getattr(algorithm, "initial_state", None)) or not callable(
        getattr(algorithm, "allocate", None)
    ):
        raise CandidateBuildError(
            "build_algorithm() must return an object with callable "
            "initial_state() and allocate() methods (SchedulingAlgorithm, "
            "per ADR-008)"
        )
    return algorithm
