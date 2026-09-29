import subprocess
import tempfile
import unittest
from pathlib import Path

from radio_scheduler.baseline import (
    InvocationResult,
    claude_code_native_configuration,
    run_baseline,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
VALID_CANDIDATE_SOURCE = (
    REPO_ROOT
    / "src"
    / "radio_scheduler"
    / "harness6g"
    / "fixtures"
    / "candidates"
    / "valid_first_eligible.py"
).read_text()


def _current_commit() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, capture_output=True, text=True, check=True
    ).stdout.strip()


def _writes_valid_candidate(prompt, worktree_dir, timeout_seconds):
    (worktree_dir / "candidate.py").write_text(VALID_CANDIDATE_SOURCE)
    return InvocationResult(succeeded=True, stdout="ok", stderr="", timed_out=False)


def _writes_nothing(prompt, worktree_dir, timeout_seconds):
    return InvocationResult(succeeded=True, stdout="ok", stderr="", timed_out=False)


def _writes_candidate_and_an_extra_file(prompt, worktree_dir, timeout_seconds):
    (worktree_dir / "candidate.py").write_text(VALID_CANDIDATE_SOURCE)
    (worktree_dir / "extra_untracked_file.py").write_text("# not authorized\n")
    return InvocationResult(succeeded=True, stdout="ok", stderr="", timed_out=False)


def _times_out(prompt, worktree_dir, timeout_seconds):
    return InvocationResult(succeeded=False, stdout="", stderr="", timed_out=True)


class BaselineConfigurationTests(unittest.TestCase):
    def test_records_real_agent_version_and_does_not_force_a_model(self):
        config = claude_code_native_configuration(base_commit=_current_commit())
        self.assertEqual(config.configuration_id, "claude-code-native")
        self.assertIn("unspecified", config.model_identity)
        self.assertTrue(config.agent_version)


class RunBaselineTests(unittest.TestCase):
    def setUp(self):
        self.base_commit = _current_commit()
        self._tmp = tempfile.TemporaryDirectory()
        self.evidence_root = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def _config(self):
        return claude_code_native_configuration(base_commit=self.base_commit)

    def test_valid_candidate_is_accepted_and_fed_to_the_common_evaluator(self):
        record = run_baseline(
            self._config(), REPO_ROOT, self.evidence_root, invoke_agent=_writes_valid_candidate
        )
        self.assertEqual(record["termination_reason"], "checks_passed")
        self.assertIsNotNone(record["terminal_candidate"])
        self.assertIsNotNone(record["terminal_hash"])
        self.assertTrue(record["public_evaluation"]["integrity_ok"])
        self.assertTrue(all(record["public_evaluation"]["categories"].values()))

    def test_missing_candidate_is_recorded_not_substituted(self):
        record = run_baseline(
            self._config(), REPO_ROOT, self.evidence_root, invoke_agent=_writes_nothing
        )
        self.assertEqual(record["termination_reason"], "no_candidate_produced")
        self.assertIsNone(record["terminal_candidate"])

    def test_scope_violation_is_detected_and_recorded(self):
        record = run_baseline(
            self._config(),
            REPO_ROOT,
            self.evidence_root,
            invoke_agent=_writes_candidate_and_an_extra_file,
        )
        self.assertEqual(record["termination_reason"], "editable_scope_violation")
        self.assertIn("extra_untracked_file.py", record["scope_violation_paths"])

    def test_timeout_is_recorded_not_silently_dropped(self):
        record = run_baseline(
            self._config(), REPO_ROOT, self.evidence_root, invoke_agent=_times_out
        )
        self.assertEqual(record["termination_reason"], "timeout")

    def test_worktree_is_always_removed_afterward(self):
        before = subprocess.run(
            ["git", "worktree", "list"], cwd=REPO_ROOT, capture_output=True, text=True
        ).stdout
        run_baseline(
            self._config(), REPO_ROOT, self.evidence_root, invoke_agent=_writes_valid_candidate
        )
        after = subprocess.run(
            ["git", "worktree", "list"], cwd=REPO_ROOT, capture_output=True, text=True
        ).stdout
        self.assertEqual(before, after)

    def test_run_record_is_written_to_evidence_root(self):
        record = run_baseline(
            self._config(), REPO_ROOT, self.evidence_root, invoke_agent=_writes_valid_candidate
        )
        record_path = self.evidence_root / record["run_id"] / "record.json"
        self.assertTrue(record_path.is_file())


if __name__ == "__main__":
    unittest.main()
