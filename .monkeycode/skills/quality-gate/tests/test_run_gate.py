import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

from detect_scope import classify_paths
from run_gate import GatePlanError, Check, build_check_plan, redact, redact_command, run_checks


CONFIG = {
    "common": {"diff_check": "git diff --check"},
    "frontend": {
        "root": "frontend",
        "targeted_test_ts": "tsx --test",
        "targeted_test_mjs": "node --test",
        "lint_changed": "pnpm exec eslint",
        "build_online": "pnpm run build:online",
    },
    "backend": {
        "root": "backend",
        "targeted_test": "go test",
        "related_test": "go test ./...",
        "build": "go build ./...",
    },
}


class RunGateTests(unittest.TestCase):
    def test_issue_910_frontend_replay(self):
        paths = [
            "frontend/src/pages/console/user/task/task-detail.tsx",
            "frontend/test/task-restart-dialog-keyboard.test.mjs",
            "docs/superpowers/specs/example.md",
        ]
        detected = classify_paths(paths)

        plan = build_check_plan(
            CONFIG,
            detected["scope"],
            paths,
            ["frontend/test/task-restart-dialog-keyboard.test.mjs"],
            [],
        )

        self.assertEqual(detected["scope"], "frontend")
        self.assertEqual(
            [check.argv for check in plan],
            [
                ["node", "--test", "test/task-restart-dialog-keyboard.test.mjs"],
                [
                    "pnpm",
                    "exec",
                    "eslint",
                    "src/pages/console/user/task/task-detail.tsx",
                    "test/task-restart-dialog-keyboard.test.mjs",
                ],
                ["pnpm", "run", "build:online"],
                ["git", "diff", "--check"],
            ],
        )

    def test_frontend_plan_uses_extension_specific_runner(self):
        plan = build_check_plan(
            CONFIG,
            "frontend",
            ["frontend/src/App.tsx"],
            ["frontend/test/app.test.mjs"],
            [],
        )
        commands = [check.argv for check in plan]
        self.assertIn(["node", "--test", "test/app.test.mjs"], commands)
        self.assertIn(["pnpm", "exec", "eslint", "src/App.tsx"], commands)
        self.assertIn(["pnpm", "run", "build:online"], commands)

    def test_backend_plan_runs_targeted_related_and_build(self):
        plan = build_check_plan(
            CONFIG,
            "backend",
            ["backend/command/task.go"],
            [],
            ["./command -run TestTask"],
        )
        commands = [check.argv for check in plan]
        self.assertEqual(commands[0], ["go", "test", "./command", "-run", "TestTask"])
        self.assertEqual(commands[1], ["go", "test", "./..."])
        self.assertEqual(commands[2], ["go", "build", "./..."])
        self.assertEqual(commands[3], ["git", "diff", "--check"])

    def test_redacts_sensitive_values(self):
        text = "token=abc password: secret Authorization: Bearer xyz"
        self.assertNotIn("abc", redact(text))
        self.assertNotIn("secret", redact(text))
        self.assertNotIn("xyz", redact(text))

    def test_redacts_sensitive_command_arguments_and_urls(self):
        command = redact_command(
            [
                "tool",
                "--token",
                "plain-secret",
                "--password=visible-secret",
                "https://oauth2:url-secret@example.com/repo.git",
            ]
        )
        rendered = " ".join(command)
        self.assertNotIn("plain-secret", rendered)
        self.assertNotIn("visible-secret", rendered)
        self.assertNotIn("url-secret", rendered)
        self.assertIn("https://example.com/repo.git", rendered)

    def test_rejects_target_path_outside_frontend_root(self):
        with self.assertRaises(GatePlanError):
            build_check_plan(
                CONFIG,
                "frontend",
                ["frontend/src/App.tsx"],
                ["frontend/../outside.test.mjs"],
                [],
            )

    def test_cli_returns_structured_error_for_missing_targeted_test(self):
        repo = Path(__file__).resolve().parents[4]
        completed = subprocess.run(
            [
                sys.executable,
                str(SCRIPT_DIR / "run_gate.py"),
                "--repo",
                str(repo),
                "--scope",
                "frontend",
                "--path",
                "frontend/src/App.tsx",
                "--dry-run",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        report = json.loads(completed.stdout)
        self.assertEqual(completed.returncode, 2)
        self.assertEqual(report["status"], "failed")
        self.assertEqual(report["error"]["category"], "GatePlanError")

    def test_cli_returns_structured_error_for_unsupported_test_extension(self):
        repo = Path(__file__).resolve().parents[4]
        completed = subprocess.run(
            [
                sys.executable,
                str(SCRIPT_DIR / "run_gate.py"),
                "--repo",
                str(repo),
                "--scope",
                "frontend",
                "--path",
                "frontend/src/App.tsx",
                "--target-test",
                "frontend/test/app.test.tsx",
                "--dry-run",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        report = json.loads(completed.stdout)
        self.assertEqual(completed.returncode, 2)
        self.assertEqual(report["status"], "failed")
        self.assertNotIn("Traceback", completed.stderr)

    def test_dry_run_redacts_command_in_complete_json_report(self):
        repo = Path(__file__).resolve().parents[4]
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        config = Path(directory.name) / "workflow.yaml"
        config.write_text("common:\n  diff_check: tool --token command-secret\n", encoding="utf-8")
        completed = subprocess.run(
            [
                sys.executable,
                str(SCRIPT_DIR / "run_gate.py"),
                "--repo",
                str(repo),
                "--config",
                str(config),
                "--scope",
                "docs",
                "--path",
                "docs/example.md",
                "--dry-run",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        report = json.loads(completed.stdout)
        self.assertEqual(completed.returncode, 0)
        self.assertEqual(report["checks"][0]["command"], ["tool", "--token", "[REDACTED]"])
        self.assertNotIn("command-secret", completed.stdout)

    def test_rejects_configured_root_outside_repository(self):
        config = {**CONFIG, "frontend": {**CONFIG["frontend"], "root": "../frontend"}}
        with self.assertRaises(GatePlanError):
            build_check_plan(
                config,
                "frontend",
                ["frontend/src/App.tsx"],
                ["frontend/test/app.test.mjs"],
                [],
            )

    def test_failed_check_stops_following_checks(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        checks = [
            Check("fail", [sys.executable, "-c", "raise SystemExit(2)"], Path(directory.name)),
            Check("later", [sys.executable, "-c", "print('later')"], Path(directory.name)),
        ]
        report = run_checks(checks)
        self.assertEqual(report["status"], "failed")
        self.assertEqual(len(report["checks"]), 1)
        self.assertEqual(report["checks"][0]["exit_code"], 2)


if __name__ == "__main__":
    unittest.main()
