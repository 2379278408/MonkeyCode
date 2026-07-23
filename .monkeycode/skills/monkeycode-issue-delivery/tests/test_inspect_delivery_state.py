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
            "git_authorized": False,
            "pr_url": None,
        }
        values.update(overrides)
        return argparse.Namespace(**values)

    def quality_report(self, status: str = "passed") -> Path:
        path = self.repo / "quality.json"
        path.write_text(json.dumps({"status": status}), encoding="utf-8")
        return path

    def issue_branch(self) -> None:
        self.git("switch", "-c", "260722-fix-issue-910")

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
        self.issue_branch()
        result = inspect_state(
            self.args(
                issue_url="https://github.com/chaitin/MonkeyCode/issues/910",
                design_approved=True,
                quality_report=self.quality_report(),
            )
        )
        self.assertEqual(result["state"], "verified")

    def test_passing_quality_and_acceptance_waits_for_review(self):
        self.issue_branch()
        self.assertEqual(inspect_state(self.accepted_args())["state"], "preview-accepted")

    def test_ready_review_is_reviewed(self):
        self.issue_branch()
        result = inspect_state(self.accepted_args(review_verdict="ready"))
        self.assertEqual(result["state"], "reviewed")

    def test_authorization_request_waits_for_authorization(self):
        self.issue_branch()
        result = inspect_state(
            self.accepted_args(review_verdict="ready", authorization_requested=True)
        )
        self.assertEqual(result["state"], "ready-for-authorization")

    def test_authorized_delivery_is_ready_to_integrate(self):
        self.issue_branch()
        result = inspect_state(
            self.accepted_args(
                review_verdict="ready",
                authorization_requested=True,
                git_authorized=True,
            )
        )
        self.assertEqual(result["state"], "ready-to-integrate")

    def test_pr_url_marks_delivery_opened(self):
        result = inspect_state(
            self.args(pr_url="https://github.com/chaitin/MonkeyCode/pull/911")
        )
        self.assertEqual(result["state"], "pr-opened")

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


if __name__ == "__main__":
    unittest.main()
