import json
import subprocess
import sys
import tempfile
from pathlib import Path


class CheckTimeoutError(Exception):
    """Raised when the candidate's check subprocess exceeds
    `stopping_policy.timeout_seconds`. A genuine OS-level interruption —
    `subprocess.run`'s own timeout handling kills the child process — not
    merely an in-process flag checked after the fact."""


def run_checks_in_subprocess(
    candidate_path: Path,
    exposed_checks: tuple[str, ...],
    timeout_seconds: float,
) -> list[dict]:
    """Runs `_check_runner` against `candidate_path` in a separate process,
    real timeout included. Returns the parsed list of check-result dicts
    on success. Raises `CheckTimeoutError` on timeout. If the subprocess
    exits without producing output for any other reason (crash before
    writing JSON), returns a single failed `build_validity` result
    carrying the subprocess's stderr — never silently empty."""
    with tempfile.TemporaryDirectory() as tmp:
        output_path = Path(tmp) / "check_results.json"
        try:
            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "radio_scheduler.harness6g._check_runner",
                    str(candidate_path),
                    str(output_path),
                    ",".join(exposed_checks),
                ],
                timeout=timeout_seconds,
                capture_output=True,
                text=True,
            )
        except subprocess.TimeoutExpired as exc:
            raise CheckTimeoutError(
                f"candidate check subprocess exceeded {timeout_seconds}s"
            ) from exc

        if not output_path.exists():
            return [
                {
                    "check_id": "build_validity",
                    "category": "build_validity",
                    "passed": False,
                    "detail": (
                        f"check runner produced no output (exit "
                        f"{completed.returncode}): {completed.stderr.strip()[-2000:]}"
                    ),
                }
            ]
        return json.loads(output_path.read_text())
