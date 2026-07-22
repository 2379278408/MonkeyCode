import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

from workflow_config import WorkflowConfigError, load_workflow, require_string


class WorkflowConfigTests(unittest.TestCase):
    def write_config(self, content: str) -> Path:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        path = Path(directory.name) / "workflow.yaml"
        path.write_text(content, encoding="utf-8")
        return path

    def test_loads_nested_maps_lists_and_scalars(self):
        path = self.write_config(
            """schema_version: 1
base_branch: main
pull_request:
  require_manual_acceptance_for_ui: true
preview:
  allowed_dependency_roots:
    - frontend/node_modules
"""
        )

        config = load_workflow(path)

        self.assertEqual(config["schema_version"], 1)
        self.assertTrue(config["pull_request"]["require_manual_acceptance_for_ui"])
        self.assertEqual(config["preview"]["allowed_dependency_roots"], ["frontend/node_modules"])

    def test_require_string_reports_missing_key(self):
        with self.assertRaisesRegex(WorkflowConfigError, "frontend.build_online"):
            require_string({"frontend": {}}, "frontend.build_online")

    def test_rejects_tabs(self):
        path = self.write_config("frontend:\n\troot: frontend\n")
        with self.assertRaisesRegex(WorkflowConfigError, "tabs"):
            load_workflow(path)


if __name__ == "__main__":
    unittest.main()
