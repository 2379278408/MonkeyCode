import argparse
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

from inspect_delivery_state import inspect_state


class InspectDeliveryStateTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.repo = Path(directory.name)
        self.git("init", "-b", "main")
        self.git("config", "user.name", "Test User")
        self.git("config", "user.email", "test@example.com")
        (self.repo / "README.md").write_text("initial\n", encoding="utf-8")
        self.git("add", "README.md")
        self.git("commit", "-m", "initial")
        self.git("remote", "add", "origin", "https://github.com/chaitin/MonkeyCode.git")
        self.git("remote", "add", "fork", "https://github.com/example/MonkeyCode.git")

    def git(self, *args: str) -> None:
        subprocess.run(
            ["git", "-C", str(self.repo), *args],
            check=True,
            capture_output=True,
            text=True,
        )

    def args(self, **overrides):
        values = {
            "repo": self.repo,
            "base_branch": "main",
            "issue_url": None,
            "design_approved": False,
            "quality_report": None,
            "manual_acceptance": "pending",
            "review_verdict": "pending",
            "authorization_requested": False,
            "required_actions": [],
            "authorized_actions": [],
            "pr_url": None,
        }
        values.update(overrides)
        return argparse.Namespace(**values)

    def quality_report(self, status: str = "passed") -> Path:
        path = self.repo / "quality.json"
        path.write_text(
            json.dumps(
                {
                    "status": status,
                    "scope": "frontend",
                    "paths": ["frontend/src/App.tsx"],
                    "checks": [{"name": "test", "exit_code": 0}],
                    "blockers": [],
                    "evidence": {"completed_checks": ["test"], "failed_checks": []},
                }
            ),
            encoding="utf-8",
        )
        return path

    def issue_branch(self) -> None:
        self.git("switch", "-c", "260722-fix-issue-910")

    def implemented_branch(self) -> None:
        self.issue_branch()
        (self.repo / "change.txt").write_text("change\n", encoding="utf-8")

    def accepted_args(self, **overrides):
        values = {
            "issue_url": "https://github.com/chaitin/MonkeyCode/issues/910",
            "design_approved": True,
            "quality_report": self.quality_report(),
            "manual_acceptance": "passed",
        }
        values.update(overrides)
        return self.args(**values)

    def test_without_issue_is_intake_ready(self):
        self.assertEqual(inspect_state(self.args())["state"], "intake-ready")

    def test_issue_on_main_is_issue_ready(self):
        result = inspect_state(
            self.args(issue_url="https://github.com/chaitin/MonkeyCode/issues/910")
        )
        self.assertEqual(result["state"], "issue-ready")

    def test_feature_branch_without_changes_is_workspace_ready(self):
        self.issue_branch()
        result = inspect_state(
            self.args(issue_url="https://github.com/chaitin/MonkeyCode/issues/910")
        )
        self.assertEqual(result["state"], "workspace-ready")

    def test_approved_design_without_changes_is_design_approved(self):
        self.issue_branch()
        result = inspect_state(
            self.args(
                issue_url="https://github.com/chaitin/MonkeyCode/issues/910",
                design_approved=True,
            )
        )
        self.assertEqual(result["state"], "design-approved")

    def test_changes_with_approved_design_are_implemented(self):
        self.issue_branch()
        (self.repo / "change.txt").write_text("change\n", encoding="utf-8")
        result = inspect_state(
            self.args(
                issue_url="https://github.com/chaitin/MonkeyCode/issues/910",
                design_approved=True,
            )
        )
        self.assertEqual(result["state"], "implemented")

    def test_passing_quality_is_verified(self):
        self.implemented_branch()
        result = inspect_state(
            self.args(
                issue_url="https://github.com/chaitin/MonkeyCode/issues/910",
                design_approved=True,
                quality_report=self.quality_report(),
            )
        )
        self.assertEqual(result["state"], "verified")

    def test_passing_quality_and_acceptance_waits_for_review(self):
        self.implemented_branch()
        self.assertEqual(inspect_state(self.accepted_args())["state"], "preview-accepted")

    def test_ready_review_is_reviewed(self):
        self.implemented_branch()
        result = inspect_state(self.accepted_args(review_verdict="ready"))
        self.assertEqual(result["state"], "reviewed")

    def test_authorization_request_waits_for_authorization(self):
        self.implemented_branch()
        result = inspect_state(
            self.accepted_args(
                review_verdict="ready",
                authorization_requested=True,
                required_actions=["commit", "push", "pr-create"],
            )
        )
        self.assertEqual(result["state"], "ready-for-authorization")

    def test_authorized_delivery_is_ready_to_integrate(self):
        self.implemented_branch()
        actions = ["commit", "push", "pr-create"]
        result = inspect_state(
            self.accepted_args(
                review_verdict="ready",
                authorization_requested=True,
                required_actions=actions,
                authorized_actions=actions,
            )
        )
        self.assertEqual(result["state"], "ready-to-integrate")

    def test_partial_authorization_remains_ready_for_authorization(self):
        self.implemented_branch()
        result = inspect_state(
            self.accepted_args(
                review_verdict="ready",
                authorization_requested=True,
                required_actions=["commit", "push", "pr-create"],
                authorized_actions=["commit"],
            )
        )
        self.assertEqual(result["state"], "ready-for-authorization")
        self.assertEqual(result["pending_actions"], ["pr-create", "push"])

    def test_invalid_quality_report_does_not_verify_delivery(self):
        self.implemented_branch()
        report = self.repo / "invalid-quality.json"
        report.write_text(json.dumps({"status": "passed"}), encoding="utf-8")
        result = inspect_state(
            self.args(
                issue_url="https://github.com/chaitin/MonkeyCode/issues/910",
                design_approved=True,
                quality_report=report,
            )
        )
        self.assertEqual(result["state"], "implemented")
        self.assertEqual(result["quality_status"], "invalid")

    def test_staged_approval_replay_reaches_pr_opened(self):
        self.issue_branch()
        (self.repo / "change.txt").write_text("change\n", encoding="utf-8")
        self.git("add", "change.txt")
        self.git("commit", "-m", "fix: replay issue 910")
        shared = {
            "review_verdict": "ready",
            "authorization_requested": True,
            "required_actions": ["commit", "push", "pr-create"],
        }

        waiting = inspect_state(self.accepted_args(**shared))
        authorized = inspect_state(
            self.accepted_args(
                **shared,
                authorized_actions=["commit", "push", "pr-create"],
            )
        )
        opened = inspect_state(
            self.accepted_args(
                **shared,
                authorized_actions=["commit", "push", "pr-create"],
                pr_url="https://github.com/chaitin/MonkeyCode/pull/911",
            )
        )

        self.assertEqual(waiting["state"], "ready-for-authorization")
        self.assertEqual(authorized["state"], "ready-to-integrate")
        self.assertEqual(opened["state"], "pr-opened")

    def test_pr_url_without_delivery_evidence_is_blocked(self):
        result = inspect_state(
            self.args(pr_url="https://github.com/chaitin/MonkeyCode/pull/911")
        )
        self.assertEqual(result["state"], "intake-ready")
        self.assertEqual(
            result["blockers"],
            ["pr-url requires the complete authorized delivery chain"],
        )

    def test_passing_quality_without_issue_is_blocked(self):
        result = inspect_state(self.args(quality_report=self.quality_report()))
        self.assertEqual(result["state"], "intake-ready")
        self.assertEqual(
            result["blockers"],
            ["quality report requires issue, workspace, design, and implementation evidence"],
        )

    def test_reports_fork_remote(self):
        result = inspect_state(self.args())
        self.assertEqual(result["remotes"]["origin"], "https://github.com/chaitin/MonkeyCode.git")
        self.assertEqual(result["remotes"]["fork"], "https://github.com/example/MonkeyCode.git")

    def test_redacts_credentials_from_remote_urls(self):
        self.git(
            "remote",
            "set-url",
            "fork",
            "https://oauth2:secret-token@github.com/example/MonkeyCode.git",
        )
        result = inspect_state(self.args())
        self.assertEqual(result["remotes"]["fork"], "https://github.com/example/MonkeyCode.git")

    def test_reports_distinct_push_url_for_fork(self):
        self.git(
            "remote",
            "set-url",
            "--add",
            "--push",
            "fork",
            "https://github.com/example/MonkeyCode-write.git",
        )
        result = inspect_state(self.args())
        self.assertEqual(
            result["remotes"]["fork"],
            "https://github.com/example/MonkeyCode-write.git",
        )


if __name__ == "__main__":
    unittest.main()
