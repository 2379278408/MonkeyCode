import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

from run_gate import Check, build_check_plan, redact, run_checks


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
