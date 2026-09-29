"""Standalone entry point invoked as a subprocess — never imported directly
by the harness's own process — to build a candidate SchedulingAlgorithm and
run the exposed checks against it in isolation. Running the candidate's
code in a separate OS process (not just a thread) is what makes
`checks.CheckTimeoutError` a genuine interruption: the parent's
`subprocess.run(..., timeout=...)` kills this process on timeout, it does
not merely stop waiting for it.

Usage:
    python -m radio_scheduler.harness6g._check_runner \
        <candidate_path> <output_json_path> <comma_separated_check_ids>
"""

import json
import sys
from pathlib import Path

from radio_scheduler.demo.scenarios import build_demo_scenarios
from radio_scheduler.harness6g.candidate import CandidateBuildError, build_candidate_algorithm
from radio_scheduler.simulation_loop import run

_CATEGORY_BY_CHECK_ID = {
    "interface_conformance": "interface_conformance",
    "served_ue_must_have_backlog": "functional_correctness",
    "no_eligibility_or_resources_yields_empty_decisions": "domain_conformance",
}


def _scenario(scenario_id, demo_scenarios):
    for demo_scenario in demo_scenarios:
        if demo_scenario.scenario_id == scenario_id:
            return demo_scenario.scenario
    raise KeyError(scenario_id)


def _check_build_validity(candidate_path):
    try:
        algorithm = build_candidate_algorithm(candidate_path)
        return algorithm, {
            "check_id": "build_validity",
            "category": "build_validity",
            "passed": True,
            "detail": "candidate module loaded and build_algorithm() returned a "
            "valid object",
        }
    except CandidateBuildError as exc:
        return None, {
            "check_id": "build_validity",
            "category": "build_validity",
            "passed": False,
            "detail": str(exc),
        }


def _check_interface_conformance(algorithm, demo_scenarios):
    try:
        for scenario_id in ("ue_competition", "cqi_difference"):
            run(_scenario(scenario_id, demo_scenarios), algorithm)
        return {
            "check_id": "interface_conformance",
            "category": "interface_conformance",
            "passed": True,
            "detail": "simulation_loop.run() completed without a contract "
            "violation on ue_competition and cqi_difference",
        }
    except Exception as exc:
        return {
            "check_id": "interface_conformance",
            "category": "interface_conformance",
            "passed": False,
            "detail": f"{type(exc).__name__}: {exc}",
        }


def _check_served_ue_must_have_backlog(algorithm, demo_scenarios):
    """Task rule (beyond what simulation_loop's own structural validation
    already enforces): a UE may only receive a Resource Block in a TTI
    where its Buffer occupancy (post-arrival, pre-decision) is > 0."""
    try:
        violations = []
        for scenario_id in ("ue_competition", "cqi_difference"):
            scenario = _scenario(scenario_id, demo_scenarios)
            result = run(scenario, algorithm)

            arrivals_by_tti: dict[int, dict[str, int]] = {}
            for arrival in scenario.traffic_arrivals:
                arrivals_by_tti.setdefault(arrival.tti.index, {})[
                    arrival.ue_id
                ] = arrival.size_bytes

            occupancy = {ue.ue_id: 0 for ue in scenario.ues}
            for tti_index in sorted({tti.index for tti in scenario.ttis}):
                for ue in scenario.ues:
                    occupancy[ue.ue_id] += arrivals_by_tti.get(tti_index, {}).get(
                        ue.ue_id, 0
                    )
                for decision in result.decisions:
                    if decision.tti.index != tti_index or not decision.resource_block_ids:
                        continue
                    if occupancy.get(decision.ue_id, 0) <= 0:
                        violations.append(
                            f"{scenario_id} tti={tti_index} ue={decision.ue_id} "
                            "served with zero backlog"
                        )
                    occupancy[decision.ue_id] = 0

        passed = not violations
        return {
            "check_id": "served_ue_must_have_backlog",
            "category": "functional_correctness",
            "passed": passed,
            "detail": "ok" if passed else "; ".join(violations),
        }
    except Exception as exc:
        return {
            "check_id": "served_ue_must_have_backlog",
            "category": "functional_correctness",
            "passed": False,
            "detail": f"{type(exc).__name__}: {exc}",
        }


def _check_no_eligibility_or_resources(algorithm, demo_scenarios):
    try:
        scenario = _scenario("no_eligibility_or_resources", demo_scenarios)
        result = run(scenario, algorithm)
        passed = result.decisions == ()
        return {
            "check_id": "no_eligibility_or_resources_yields_empty_decisions",
            "category": "domain_conformance",
            "passed": passed,
            "detail": "ok" if passed else f"expected zero decisions, got {result.decisions!r}",
        }
    except Exception as exc:
        return {
            "check_id": "no_eligibility_or_resources_yields_empty_decisions",
            "category": "domain_conformance",
            "passed": False,
            "detail": f"{type(exc).__name__}: {exc}",
        }


_ALL_CHECKS = {
    "interface_conformance": _check_interface_conformance,
    "served_ue_must_have_backlog": _check_served_ue_must_have_backlog,
    "no_eligibility_or_resources_yields_empty_decisions": _check_no_eligibility_or_resources,
}


def main() -> None:
    candidate_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2])
    requested = sys.argv[3].split(",") if len(sys.argv) > 3 and sys.argv[3] else list(_ALL_CHECKS)

    demo_scenarios = build_demo_scenarios()
    results = []

    algorithm, build_result = _check_build_validity(candidate_path)
    results.append(build_result)

    for check_id in requested:
        if check_id not in _ALL_CHECKS:
            continue
        if algorithm is None:
            results.append(
                {
                    "check_id": check_id,
                    "category": _CATEGORY_BY_CHECK_ID[check_id],
                    "passed": False,
                    "detail": "skipped: candidate failed build_validity",
                }
            )
        else:
            results.append(_ALL_CHECKS[check_id](algorithm, demo_scenarios))

    output_path.write_text(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
