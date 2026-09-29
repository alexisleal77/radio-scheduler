"""Demonstration entry point for Delivery A (HARNESS6G integration):
runs Round Robin, Proportional Fair, and MaxCQI over the same small,
hand-built demo scenarios (radio_scheduler.demo.scenarios), records
per-TTI decisions and computational-cost benchmarks, and writes a
structured JSON result plus a Portuguese-language report to evidence/demo/.

Thin wrapper: all scheduling, simulation, and benchmark logic lives in
already-tested src/ modules. This script only orchestrates
radio_scheduler.demo.run_demo() and writes its output — it implements no
scheduling or benchmarking logic of its own.
"""

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from radio_scheduler.demo import render_report_pt, result_to_dict, run_demo

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "evidence" / "demo"


def _git_commit() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], text=True, stderr=subprocess.DEVNULL
        ).strip()
    except Exception:
        return "unknown"


def main() -> None:
    results = run_demo()

    metadata = {
        "commit": _git_commit(),
        "command": "uv run python scripts/demo.py",
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    payload = {
        "metadata": metadata,
        "results": [result_to_dict(result) for result in results],
    }
    results_path = OUTPUT_DIR / "results.json"
    results_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")

    report_path = OUTPUT_DIR / "relatorio.md"
    report_path.write_text(render_report_pt(results, metadata) + "\n")

    print(f"Escrito: {results_path}")
    print(f"Escrito: {report_path}")


if __name__ == "__main__":
    main()
