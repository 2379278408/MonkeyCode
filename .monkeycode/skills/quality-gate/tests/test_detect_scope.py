import sys
import unittest
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

from detect_scope import classify_paths


class DetectScopeTests(unittest.TestCase):
    def test_frontend_with_docs_remains_frontend(self):
        result = classify_paths(["frontend/src/app.tsx", "docs/change.md"])
        self.assertEqual(result["scope"], "frontend")
        self.assertEqual(result["categories"], ["docs", "frontend"])

    def test_frontend_and_backend_is_mixed(self):
        result = classify_paths(["frontend/src/app.tsx", "backend/main.go"])
        self.assertEqual(result["scope"], "mixed")

    def test_workflow_files_are_docs(self):
        result = classify_paths([".monkeycode/workflow.yaml"])
        self.assertEqual(result["scope"], "docs")
        self.assertEqual(result["categories"], ["docs"])

    def test_empty_paths_is_none(self):
        self.assertEqual(classify_paths([])["scope"], "none")


if __name__ == "__main__":
    unittest.main()
