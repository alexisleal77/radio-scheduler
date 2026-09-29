import unittest
from pathlib import Path

from radio_scheduler.harness6g import (
    CandidateBuildError,
    CheckTimeoutError,
    ProtectedEvaluationUnavailable,
    ResourcePolicy,
    StoppingPolicy,
    TaskSpec,
    build_candidate_algorithm,
    default_scheduling_candidate_task,
    evaluate_protected,
    evaluate_public,
    freeze_candidate,
    load_candidate_source,
    run_checks_in_subprocess,
    run_harness6g,
    verify_integrity,
)

FIXTURES_DIR = (
    Path(__file__).resolve().parent.parent
    / "src"
    / "radio_scheduler"
    / "harness6g"
    / "fixtures"
    / "candidates"
)
VALID_CANDIDATE = FIXTURES_DIR / "valid_first_eligible.py"
BROKEN_DUPLICATE_RB = FIXTURES_DIR / "broken_duplicate_rb.py"
BROKEN_BACKLOG = FIXTURES_DIR / "broken_serves_without_backlog.py"
HANGS_FOREVER = FIXTURES_DIR / "hangs_forever.py"


class TaskSpecValidationTests(unittest.TestCase):
    def test_default_task_is_valid(self):
        task = default_scheduling_candidate_task()
        self.assertTrue(task.exposed_checks)
        self.assertTrue(task.editable_scope)

    def test_rejects_empty_task_id(self):
        with self.assertRaises(ValueError):
            TaskSpec(
                task_id="",
                task_version="0.1",
                interface_version="v1",
                editable_scope=("x",),
                exposed_context=(),
                exposed_checks=("interface_conformance",),
                stopping_policy=StoppingPolicy(max_revisions=1, timeout_seconds=1.0),
                resource_policy=ResourcePolicy(),
            )

    def test_stopping_policy_rejects_non_positive_timeout(self):
        with self.assertRaises(ValueError):
            StoppingPolicy(max_revisions=1, timeout_seconds=0)

    def test_stopping_policy_rejects_zero_revisions(self):
        with self.assertRaises(ValueError):
            StoppingPolicy(max_revisions=0, timeout_seconds=1.0)


class CandidateScopeTests(unittest.TestCase):
    def test_in_scope_candidate_loads(self):
        source = load_candidate_source(VALID_CANDIDATE, ("src/radio_scheduler/harness6g/fixtures/candidates",))
        self.assertIn("build_algorithm", source)

    def test_out_of_scope_candidate_is_rejected(self):
        with self.assertRaises(CandidateBuildError):
            load_candidate_source(VALID_CANDIDATE, ("docs",))

    def test_missing_file_is_rejected(self):
        with self.assertRaises(CandidateBuildError):
            load_candidate_source(
                FIXTURES_DIR / "does_not_exist.py",
                ("src/radio_scheduler/harness6g/fixtures/candidates",),
            )


class CandidateBuildTests(unittest.TestCase):
    def test_valid_candidate_builds_a_scheduling_algorithm(self):
        algorithm = build_candidate_algorithm(VALID_CANDIDATE)
        self.assertTrue(callable(algorithm.initial_state))
        self.assertTrue(callable(algorithm.allocate))

    def test_missing_factory_is_rejected(self, tmp_path=None):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            bad_path = Path(tmp) / "no_factory.py"
            bad_path.write_text("x = 1\n")
            with self.assertRaises(CandidateBuildError):
                build_candidate_algorithm(bad_path)


class CheckSubprocessTests(unittest.TestCase):
    def test_valid_candidate_passes_every_exposed_check(self):
        task = default_scheduling_candidate_task()
        results = run_checks_in_subprocess(
            VALID_CANDIDATE, task.exposed_checks, task.stopping_policy.timeout_seconds
        )
        by_id = {r["check_id"]: r for r in results}
        for check_id in task.exposed_checks:
            with self.subTest(check_id=check_id):
                self.assertTrue(by_id[check_id]["passed"], by_id[check_id]["detail"])

    def test_duplicate_rb_candidate_fails_interface_conformance(self):
        task = default_scheduling_candidate_task()
        results = run_checks_in_subprocess(
            BROKEN_DUPLICATE_RB, task.exposed_checks, task.stopping_policy.timeout_seconds
        )
        by_id = {r["check_id"]: r for r in results}
        self.assertFalse(by_id["interface_conformance"]["passed"])

    def test_ignores_backlog_candidate_fails_domain_conformance(self):
        task = default_scheduling_candidate_task()
        results = run_checks_in_subprocess(
            BROKEN_BACKLOG, task.exposed_checks, task.stopping_policy.timeout_seconds
        )
        by_id = {r["check_id"]: r for r in results}
        self.assertFalse(
            by_id["no_eligibility_or_resources_yields_empty_decisions"]["passed"]
        )

    def test_hanging_candidate_is_really_interrupted_by_timeout(self):
        with self.assertRaises(CheckTimeoutError):
            run_checks_in_subprocess(HANGS_FOREVER, ("interface_conformance",), 1.0)


class FreezeAndIntegrityTests(unittest.TestCase):
    def test_freeze_then_verify_succeeds(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp) / "run"
            freeze_candidate(VALID_CANDIDATE, "scheduling_interface-v0.1", run_dir)
            self.assertTrue(verify_integrity(run_dir))

    def test_tampering_after_freeze_fails_integrity(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp) / "run"
            freeze_candidate(VALID_CANDIDATE, "scheduling_interface-v0.1", run_dir)
            (run_dir / "frozen_candidate.py").write_text("# tampered\n")
            self.assertFalse(verify_integrity(run_dir))

    def test_missing_run_dir_fails_integrity(self):
        self.assertFalse(verify_integrity(Path("/nonexistent/run/dir")))


class EvaluatorTests(unittest.TestCase):
    def test_evaluate_public_reports_all_categories_passing_for_valid_candidate(self):
        import tempfile

        task = default_scheduling_candidate_task()
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp) / "run"
            freeze_candidate(VALID_CANDIDATE, task.interface_version, run_dir)
            report = evaluate_public(run_dir, task)
            self.assertTrue(report["integrity_ok"])
            self.assertTrue(all(report["categories"].values()))

    def test_evaluate_public_refuses_on_broken_integrity(self):
        import tempfile

        task = default_scheduling_candidate_task()
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp) / "run"
            freeze_candidate(VALID_CANDIDATE, task.interface_version, run_dir)
            (run_dir / "frozen_candidate.py").write_text("# tampered\n")
            report = evaluate_public(run_dir, task)
            self.assertFalse(report["integrity_ok"])

    def test_evaluate_protected_always_refuses(self):
        with self.assertRaises(ProtectedEvaluationUnavailable):
            evaluate_protected(Path("/any/run/dir"), None)


class RunHarness6GOrchestrationTests(unittest.TestCase):
    def test_valid_candidate_is_accepted_and_frozen(self):
        import tempfile

        task = default_scheduling_candidate_task()
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp) / "run"
            evidence = run_harness6g(task, (VALID_CANDIDATE,), run_dir, mode="replay")
            self.assertEqual(evidence["termination_reason"], "checks_passed")
            self.assertIsNotNone(evidence["frozen_manifest"])
            self.assertTrue(verify_integrity(run_dir))

    def test_only_broken_revisions_exhausts_without_freezing(self):
        import tempfile

        task = default_scheduling_candidate_task()
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp) / "run"
            evidence = run_harness6g(
                task, (BROKEN_DUPLICATE_RB, BROKEN_BACKLOG), run_dir, mode="replay"
            )
            self.assertEqual(evidence["termination_reason"], "revisions_exhausted")
            self.assertIsNone(evidence["frozen_manifest"])
            self.assertEqual(evidence["correction_count"], 2)

    def test_more_revisions_than_allowed_reports_max_revisions_exceeded(self):
        import tempfile

        task = TaskSpec(
            task_id="t",
            task_version="0.1",
            interface_version="v1",
            editable_scope=("src/radio_scheduler/harness6g/fixtures/candidates",),
            exposed_context=(),
            exposed_checks=("interface_conformance",),
            stopping_policy=StoppingPolicy(max_revisions=1, timeout_seconds=10.0),
            resource_policy=ResourcePolicy(),
        )
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp) / "run"
            evidence = run_harness6g(
                task,
                (BROKEN_DUPLICATE_RB, VALID_CANDIDATE),
                run_dir,
                mode="replay",
            )
            self.assertEqual(evidence["termination_reason"], "max_revisions_exceeded")
            self.assertEqual(len(evidence["observations"]), 1)

    def test_timeout_stops_the_run_immediately(self):
        import tempfile

        task = TaskSpec(
            task_id="t",
            task_version="0.1",
            interface_version="v1",
            editable_scope=("src/radio_scheduler/harness6g/fixtures/candidates",),
            exposed_context=(),
            exposed_checks=("interface_conformance",),
            stopping_policy=StoppingPolicy(max_revisions=3, timeout_seconds=1.0),
            resource_policy=ResourcePolicy(),
        )
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp) / "run"
            evidence = run_harness6g(
                task, (HANGS_FOREVER, VALID_CANDIDATE), run_dir, mode="replay"
            )
            self.assertEqual(evidence["termination_reason"], "timeout")
            self.assertEqual(len(evidence["observations"]), 1)
            self.assertIsNone(evidence["frozen_manifest"])

    def test_rejects_invalid_mode(self):
        import tempfile

        task = default_scheduling_candidate_task()
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp) / "run"
            with self.assertRaises(ValueError):
                run_harness6g(task, (VALID_CANDIDATE,), run_dir, mode="autonomous")


if __name__ == "__main__":
    unittest.main()
