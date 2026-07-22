# MonkeyCode Issue Delivery Workflow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 MonkeyCode 仓库内实现可版本化的 Issue 到 PR 编排 skill、统一质量门禁 skill 和项目工作流配置。

**Architecture:** `.monkeycode/workflow.yaml` 保存项目确定性配置；`quality-gate` 负责范围探测和有限时长质量命令；`monkeycode-issue-delivery` 负责状态推导、授权门禁和现有 skill 路由。两个 skill 使用 Python 标准库脚本，避免新增运行时依赖，并通过 `unittest` fixture 验证。

**Tech Stack:** Python 3.11+ 标准库、YAML 子集配置、Git CLI、GitHub CLI、Markdown skill 规范、`unittest`

## Global Constraints

- skill 源码必须位于 `.monkeycode/skills/<skill-name>/` 并纳入版本控制。
- 项目配置必须位于 `.monkeycode/workflow.yaml`。
- 第一版采用 `staged-approval`，创建 Issue、commit、push 和创建 PR 均需要明确授权。
- 所有脚本必须使用 Python 标准库，不新增项目依赖。
- 所有外部命令必须通过参数数组执行，禁止 `shell=True`。
- 脚本输出必须隐藏 token、password、secret、authorization 和 API key 值。
- `quality-gate` 不负责启动长期运行服务。
- `monkeycode-issue-delivery` 不直接实现设计、产品代码、预览、审查和 Git 集成能力。
- 提交信息、PR 标题、PR 正文和用户交付报告使用中文。
- `.skill` 包属于构建产物，不提交到仓库。

---

## File Map

### Project configuration

- Create: `.monkeycode/workflow.yaml` — MonkeyCode 分支、质量命令、预览和 PR 策略。

### quality-gate

- Create: `.monkeycode/skills/quality-gate/SKILL.md` — 触发说明、执行流程和资源路由。
- Create: `.monkeycode/skills/quality-gate/references/result-schema.md` — JSON 输出契约。
- Create: `.monkeycode/skills/quality-gate/scripts/workflow_config.py` — YAML 子集读取和字段校验。
- Create: `.monkeycode/skills/quality-gate/scripts/detect_scope.py` — Git 变更范围分类。
- Create: `.monkeycode/skills/quality-gate/scripts/run_gate.py` — 质量命令编排、执行和脱敏报告。
- Create: `.monkeycode/skills/quality-gate/tests/test_workflow_config.py` — 配置读取测试。
- Create: `.monkeycode/skills/quality-gate/tests/test_detect_scope.py` — 范围分类测试。
- Create: `.monkeycode/skills/quality-gate/tests/test_run_gate.py` — 命令计划、失败和脱敏测试。

### monkeycode-issue-delivery

- Create: `.monkeycode/skills/monkeycode-issue-delivery/SKILL.md` — 双入口交付编排流程。
- Create: `.monkeycode/skills/monkeycode-issue-delivery/references/state-machine.md` — 状态和进入条件。
- Create: `.monkeycode/skills/monkeycode-issue-delivery/references/issue-template.md` — 中文 Issue 模板。
- Create: `.monkeycode/skills/monkeycode-issue-delivery/references/pr-report-template.md` — 中文 PR 与交付汇报模板。
- Create: `.monkeycode/skills/monkeycode-issue-delivery/scripts/inspect_delivery_state.py` — 本地交付状态推导。
- Create: `.monkeycode/skills/monkeycode-issue-delivery/tests/test_inspect_delivery_state.py` — 状态迁移和 fork remote 测试。

---

### Task 1: Workflow Configuration Parser

**Files:**
- Create: `.monkeycode/workflow.yaml`
- Create: `.monkeycode/skills/quality-gate/scripts/workflow_config.py`
- Test: `.monkeycode/skills/quality-gate/tests/test_workflow_config.py`

**Interfaces:**
- Produces: `load_workflow(path: Path) -> dict[str, object]`
- Produces: `require_string(config: dict[str, object], dotted_key: str) -> str`
- Produces: `WorkflowConfigError`

- [ ] **Step 1: Initialize and inspect the quality-gate template**

Run:

```bash
ls /tmp/opencode
python3 /root/.codingmatrix/project-tpl/.ai-ready/skills/skill-creator/scripts/init_skill.py quality-gate --path /tmp/opencode/skill-scaffolds
```

Expected: `/tmp/opencode/skill-scaffolds/quality-gate/` exists for template inspection. Create only the required project files listed in this plan; leave template-only sample files outside the repository.

- [ ] **Step 2: Write failing configuration tests**

Create `.monkeycode/skills/quality-gate/tests/test_workflow_config.py`:

```python
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
```

- [ ] **Step 3: Run the test and verify the expected failure**

Run:

```bash
python3 .monkeycode/skills/quality-gate/tests/test_workflow_config.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'workflow_config'`.

- [ ] **Step 4: Implement the YAML subset parser**

Create `.monkeycode/skills/quality-gate/scripts/workflow_config.py`:

```python
from __future__ import annotations

from pathlib import Path
from typing import Any


class WorkflowConfigError(ValueError):
    pass


def _scalar(value: str) -> object:
    value = value.strip()
    if value in {"true", "false"}:
        return value == "true"
    if value.isdigit():
        return int(value)
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def _parse_block(lines: list[tuple[int, str]], index: int, indent: int) -> tuple[object, int]:
    is_list = lines[index][1].startswith("- ")
    container: object = [] if is_list else {}

    while index < len(lines):
        current_indent, text = lines[index]
        if current_indent < indent:
            break
        if current_indent > indent:
            raise WorkflowConfigError(f"unexpected indentation near: {text}")

        if is_list:
            if not text.startswith("- "):
                raise WorkflowConfigError(f"mixed list and mapping near: {text}")
            assert isinstance(container, list)
            container.append(_scalar(text[2:]))
            index += 1
            continue

        if text.startswith("- ") or ":" not in text:
            raise WorkflowConfigError(f"invalid mapping entry: {text}")
        key, raw_value = text.split(":", 1)
        key = key.strip()
        if not key:
            raise WorkflowConfigError("empty mapping key")
        assert isinstance(container, dict)
        index += 1
        if raw_value.strip():
            container[key] = _scalar(raw_value)
            continue
        if index >= len(lines) or lines[index][0] <= current_indent:
            container[key] = {}
            continue
        child, index = _parse_block(lines, index, current_indent + 2)
        container[key] = child

    return container, index


def load_workflow(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise WorkflowConfigError(f"workflow config not found: {path}")

    parsed_lines: list[tuple[int, str]] = []
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        if "\t" in raw_line:
            raise WorkflowConfigError("tabs are not supported in workflow config")
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        indent = len(raw_line) - len(raw_line.lstrip(" "))
        if indent % 2:
            raise WorkflowConfigError(f"indentation must use two spaces: {stripped}")
        parsed_lines.append((indent, stripped))

    if not parsed_lines:
        raise WorkflowConfigError("workflow config is empty")
    result, consumed = _parse_block(parsed_lines, 0, parsed_lines[0][0])
    if consumed != len(parsed_lines) or not isinstance(result, dict):
        raise WorkflowConfigError("workflow config root must be a mapping")
    return result


def require_string(config: dict[str, Any], dotted_key: str) -> str:
    current: object = config
    for part in dotted_key.split("."):
        if not isinstance(current, dict) or part not in current:
            raise WorkflowConfigError(f"missing required string: {dotted_key}")
        current = current[part]
    if not isinstance(current, str) or not current.strip():
        raise WorkflowConfigError(f"missing required string: {dotted_key}")
    return current
```

- [ ] **Step 5: Add the project workflow configuration**

Create `.monkeycode/workflow.yaml`:

```yaml
schema_version: 1
base_branch: main
language: zh-CN

pull_request:
  link_keyword: Fixes
  require_manual_acceptance_for_ui: true

common:
  diff_check: git diff --check

frontend:
  root: frontend
  package_manager: pnpm
  targeted_test_ts: tsx --test
  targeted_test_mjs: node --test
  lint_changed: pnpm exec eslint
  build_online: pnpm run build:online

preview:
  mode: online
  target: https://monkeycode-ai.com
  api_prefix: /api
  allowed_dependency_roots:
    - frontend/node_modules

backend:
  root: backend
  targeted_test: go test
  related_test: go test ./...
  build: go build ./...
```

- [ ] **Step 6: Run tests and validate the real configuration**

Run:

```bash
python3 .monkeycode/skills/quality-gate/tests/test_workflow_config.py -v
python3 -c 'import sys; from pathlib import Path; sys.path.insert(0, ".monkeycode/skills/quality-gate/scripts"); from workflow_config import load_workflow; config = load_workflow(Path(".monkeycode/workflow.yaml")); assert config["base_branch"] == "main"'
```

Expected: 3 tests PASS and the configuration assertion exits 0.

- [ ] **Step 7: Commit Task 1**

```bash
git add .monkeycode/workflow.yaml .monkeycode/skills/quality-gate/scripts/workflow_config.py .monkeycode/skills/quality-gate/tests/test_workflow_config.py
git commit -m "功能：增加 MonkeyCode 工作流配置解析"
```

### Task 2: Change Scope Detection

**Files:**
- Create: `.monkeycode/skills/quality-gate/scripts/detect_scope.py`
- Test: `.monkeycode/skills/quality-gate/tests/test_detect_scope.py`

**Interfaces:**
- Consumes: repository-relative changed paths.
- Produces: `classify_paths(paths: list[str]) -> dict[str, object]`
- Produces CLI JSON with `scope`, `categories`, and `paths`.

- [ ] **Step 1: Write failing scope tests**

Create `.monkeycode/skills/quality-gate/tests/test_detect_scope.py`:

```python
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

    def test_empty_paths_is_none(self):
        self.assertEqual(classify_paths([])["scope"], "none")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the test and verify failure**

Run:

```bash
python3 .monkeycode/skills/quality-gate/tests/test_detect_scope.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'detect_scope'`.

- [ ] **Step 3: Implement scope detection**

Create `.monkeycode/skills/quality-gate/scripts/detect_scope.py`:

```python
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path


def classify_paths(paths: list[str]) -> dict[str, object]:
    normalized = sorted({path.strip().lstrip("./") for path in paths if path.strip()})
    categories: set[str] = set()
    for path in normalized:
        if path.startswith("frontend/"):
            categories.add("frontend")
        elif path.startswith("backend/"):
            categories.add("backend")
        elif path.startswith(("docs/", ".monkeycode/", ".github/")) or path.endswith(".md"):
            categories.add("docs")
        else:
            categories.add("repository")

    functional = categories & {"frontend", "backend"}
    if len(functional) == 2:
        scope = "mixed"
    elif functional:
        scope = next(iter(functional))
    elif categories:
        scope = "docs"
    else:
        scope = "none"
    return {"scope": scope, "categories": sorted(categories), "paths": normalized}


def _git(repo: Path, *args: str) -> list[str]:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
    )
    return [line for line in result.stdout.splitlines() if line]


def changed_paths(repo: Path, base: str, head: str) -> list[str]:
    committed = _git(repo, "diff", "--name-only", "--diff-filter=ACMRT", f"{base}...{head}")
    working = _git(repo, "diff", "--name-only", "--diff-filter=ACMRT")
    untracked = _git(repo, "ls-files", "--others", "--exclude-standard")
    return sorted(set(committed + working + untracked))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--base", default="origin/main")
    parser.add_argument("--head", default="HEAD")
    parser.add_argument("--path", action="append", dest="paths")
    args = parser.parse_args()
    paths = args.paths if args.paths is not None else changed_paths(args.repo, args.base, args.head)
    print(json.dumps(classify_paths(paths), ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run unit and CLI tests**

Run:

```bash
python3 .monkeycode/skills/quality-gate/tests/test_detect_scope.py -v
python3 .monkeycode/skills/quality-gate/scripts/detect_scope.py --path frontend/src/App.tsx --path docs/change.md
```

Expected: 4 tests PASS; CLI JSON contains `"scope": "frontend"`.

- [ ] **Step 5: Commit Task 2**

```bash
git add .monkeycode/skills/quality-gate/scripts/detect_scope.py .monkeycode/skills/quality-gate/tests/test_detect_scope.py
git commit -m "功能：增加质量门禁变更范围探测"
```

### Task 3: Quality Gate Runner

**Files:**
- Create: `.monkeycode/skills/quality-gate/scripts/run_gate.py`
- Test: `.monkeycode/skills/quality-gate/tests/test_run_gate.py`

**Interfaces:**
- Consumes: `load_workflow`, `classify_paths`, target test paths, backend test selectors.
- Produces: `build_check_plan(config, scope, changed_paths, target_tests, backend_tests) -> list[Check]`.
- Produces CLI JSON report matching `result-schema.md`.

- [ ] **Step 1: Write failing runner tests**

Create `.monkeycode/skills/quality-gate/tests/test_run_gate.py`:

```python
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
    "backend": {"root": "backend", "targeted_test": "go test", "build": "go build ./..."},
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
```

- [ ] **Step 2: Run the test and verify failure**

Run:

```bash
python3 .monkeycode/skills/quality-gate/tests/test_run_gate.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'run_gate'`.

- [ ] **Step 3: Implement the runner**

Create `.monkeycode/skills/quality-gate/scripts/run_gate.py`:

```python
from __future__ import annotations

import argparse
import json
import re
import shlex
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

from detect_scope import changed_paths as git_changed_paths
from detect_scope import classify_paths
from workflow_config import load_workflow, require_string


@dataclass(frozen=True)
class Check:
    name: str
    argv: list[str]
    cwd: Path


def redact(text: str) -> str:
    patterns = (
        r"(?i)(token\s*[=:]\s*)\S+",
        r"(?i)(password\s*[=:]\s*)\S+",
        r"(?i)(secret\s*[=:]\s*)\S+",
        r"(?i)(api[_-]?key\s*[=:]\s*)\S+",
        r"(?i)(authorization\s*:\s*(?:bearer\s+)?)\S+",
    )
    for pattern in patterns:
        text = re.sub(pattern, r"\1[REDACTED]", text)
    return text[-4000:]


def _argv(config: dict[str, object], key: str) -> list[str]:
    return shlex.split(require_string(config, key))


def _relative(path: str, root: str) -> str:
    return str(Path(path).relative_to(root))


def build_check_plan(
    config: dict[str, object],
    scope: str,
    changed_paths: list[str],
    target_tests: list[str],
    backend_tests: list[str],
    repo: Path | None = None,
) -> list[Check]:
    repo = (repo or Path.cwd()).resolve()
    checks: list[Check] = []

    if scope in {"frontend", "mixed"}:
        frontend_root = require_string(config, "frontend.root")
        frontend_cwd = repo / frontend_root
        for target in target_tests:
            relative_target = _relative(target, frontend_root)
            runner_key = "frontend.targeted_test_mjs" if target.endswith(".mjs") else "frontend.targeted_test_ts"
            checks.append(Check(f"frontend-test:{relative_target}", _argv(config, runner_key) + [relative_target], frontend_cwd))

        lint_paths = [
            _relative(path, frontend_root)
            for path in changed_paths
            if path.startswith(f"{frontend_root}/") and Path(path).suffix in {".ts", ".tsx", ".js", ".jsx", ".mjs"}
        ]
        if lint_paths:
            checks.append(Check("frontend-lint", _argv(config, "frontend.lint_changed") + lint_paths, frontend_cwd))
        checks.append(Check("frontend-build-online", _argv(config, "frontend.build_online"), frontend_cwd))

    if scope in {"backend", "mixed"}:
        backend_root = require_string(config, "backend.root")
        backend_cwd = repo / backend_root
        for selector in backend_tests:
            checks.append(Check(f"backend-test:{selector}", _argv(config, "backend.targeted_test") + shlex.split(selector), backend_cwd))
        checks.append(Check("backend-build", _argv(config, "backend.build"), backend_cwd))

    checks.append(Check("git-diff-check", _argv(config, "common.diff_check"), repo))
    return checks


def run_checks(checks: list[Check]) -> dict[str, object]:
    results: list[dict[str, object]] = []
    for check in checks:
        started = time.monotonic()
        try:
            completed = subprocess.run(
                check.argv,
                cwd=check.cwd,
                capture_output=True,
                text=True,
                timeout=600,
            )
            exit_code = completed.returncode
            stdout = redact(completed.stdout)
            stderr = redact(completed.stderr)
        except subprocess.TimeoutExpired as error:
            exit_code = 124
            stdout = redact(error.stdout or "")
            stderr = redact(error.stderr or "timeout after 600 seconds")
        duration_ms = round((time.monotonic() - started) * 1000)
        results.append(
            {
                "name": check.name,
                "command": check.argv,
                "cwd": str(check.cwd),
                "exit_code": exit_code,
                "duration_ms": duration_ms,
                "stdout": stdout,
                "stderr": stderr,
            }
        )
        if exit_code != 0:
            break
    return {"status": "passed" if len(results) == len(checks) and all(item["exit_code"] == 0 for item in results) else "failed", "checks": results}


def _planned(checks: list[Check]) -> dict[str, object]:
    return {
        "status": "planned",
        "checks": [{"name": check.name, "command": check.argv, "cwd": str(check.cwd)} for check in checks],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--config", type=Path, default=Path(".monkeycode/workflow.yaml"))
    parser.add_argument("--base", default="origin/main")
    parser.add_argument("--head", default="HEAD")
    parser.add_argument("--scope", choices=("auto", "frontend", "backend", "mixed", "docs"), default="auto")
    parser.add_argument("--target-test", action="append", default=[])
    parser.add_argument("--backend-test", action="append", default=[])
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    repo = args.repo.resolve()
    config_path = args.config if args.config.is_absolute() else repo / args.config
    config = load_workflow(config_path)
    paths = git_changed_paths(repo, args.base, args.head)
    detected = classify_paths(paths)
    scope = detected["scope"] if args.scope == "auto" else args.scope
    checks = build_check_plan(config, scope, paths, args.target_test, args.backend_test, repo)
    report = _planned(checks) if args.dry_run else run_checks(checks)
    failed_checks = [item["name"] for item in report["checks"] if item.get("exit_code", 0) != 0]
    report.update(
        {
            "scope": scope,
            "paths": paths,
            "blockers": [] if report["status"] != "failed" else ["quality gate failed"],
            "evidence": {"completed_checks": [item["name"] for item in report["checks"]], "failed_checks": failed_checks},
        }
    )
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 1 if report["status"] == "failed" else 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run runner tests**

Run:

```bash
python3 .monkeycode/skills/quality-gate/tests/test_run_gate.py -v
```

Expected: 4 tests PASS.

- [ ] **Step 5: Verify a dry-run against MonkeyCode**

Run:

```bash
python3 .monkeycode/skills/quality-gate/scripts/run_gate.py --repo . --config .monkeycode/workflow.yaml --scope frontend --target-test frontend/test/task-restart-dialog-keyboard.test.mjs --dry-run
```

Expected: JSON status is `planned`; commands include Node test, online build, and diff check; ESLint is included when the detected Git range contains frontend source files; no command is executed.

- [ ] **Step 6: Commit Task 3**

```bash
git add .monkeycode/skills/quality-gate/scripts/run_gate.py .monkeycode/skills/quality-gate/tests/test_run_gate.py
git commit -m "功能：实现统一质量门禁执行器"
```

### Task 4: quality-gate Skill Documentation and Packaging

**Files:**
- Create: `.monkeycode/skills/quality-gate/SKILL.md`
- Create: `.monkeycode/skills/quality-gate/references/cli.md`
- Create: `.monkeycode/skills/quality-gate/references/result-schema.md`

**Interfaces:**
- Consumes: `.monkeycode/workflow.yaml`, changed files, optional targeted tests.
- Produces: structured gate report and exit code.

- [ ] **Step 1: Replace the generated SKILL.md**

Use this frontmatter and core workflow:

```markdown
---
name: quality-gate
description: Detect and run reproducible project quality checks before review, preview, commit, or PR. Use for MonkeyCode frontend, Go backend, documentation, and mixed changes when validating targeted tests, lint, typecheck/build, generated-code checks, or git diff cleanliness; also use in repair mode for authorized formatting and lint fixes.
---

# Quality Gate

1. Read `.monkeycode/workflow.yaml`.
2. Run `scripts/detect_scope.py` for the requested Git range or working tree.
3. Collect explicit targeted test paths or selectors from the implementation plan.
4. Run `scripts/run_gate.py --dry-run` and inspect every command and working directory.
5. Run the approved gate without `--dry-run`.
6. Stop at the first failure and report its evidence.
7. Return the result format from `references/result-schema.md`.

Keep server startup, Git commits, pushes, and PR operations outside this skill. Use `deploy-website` for runtime preview and the delivery workflow for Git authorization.
```

- [ ] **Step 2: Write the result schema reference**

Create `references/result-schema.md` defining `status`, `scope`, `paths`, `checks`, `blockers`, and `evidence`; include one passing JSON example and one failed JSON example. Require every check to contain command, cwd, exit code, duration, redacted stdout, and redacted stderr.

- [ ] **Step 3: Write the CLI reference**

Create `references/cli.md` with the complete `run_gate.py` and `detect_scope.py` argument tables from Tasks 2 and 3, exit-code semantics, one dry-run command, and one normal execution command. State that commands run from configured working directories and stop at the first failure.

- [ ] **Step 4: Run all quality-gate tests and skill validation**

Run:

```bash
python3 -m unittest discover -s .monkeycode/skills/quality-gate/tests -p 'test_*.py' -v
python3 /root/.codingmatrix/project-tpl/.ai-ready/skills/skill-creator/scripts/quick_validate.py .monkeycode/skills/quality-gate
```

Expected: all tests PASS and validator reports a valid skill.

- [ ] **Step 5: Package the skill outside the repository**

Run:

```bash
python3 /root/.codingmatrix/project-tpl/.ai-ready/skills/skill-creator/scripts/package_skill.py .monkeycode/skills/quality-gate /tmp/opencode/skill-packages
```

Expected: `/tmp/opencode/skill-packages/quality-gate.skill` exists and validation passes.

- [ ] **Step 6: Commit Task 4**

Stage only production sources, tests, and references:

```bash
git add .monkeycode/skills/quality-gate/SKILL.md .monkeycode/skills/quality-gate/references .monkeycode/skills/quality-gate/scripts .monkeycode/skills/quality-gate/tests
git commit -m "功能：完善 MonkeyCode 质量门禁 Skill"
```

### Task 5: Delivery State Inspector

**Files:**
- Initialize: `.monkeycode/skills/monkeycode-issue-delivery/`
- Create: `.monkeycode/skills/monkeycode-issue-delivery/scripts/inspect_delivery_state.py`
- Test: `.monkeycode/skills/monkeycode-issue-delivery/tests/test_inspect_delivery_state.py`

**Interfaces:**
- Consumes: local Git repository, issue URL, quality report, acceptance, review, authorization, and PR URL.
- Produces: `inspect_state(args) -> dict[str, object]` with one state from the approved state machine.

- [ ] **Step 1: Initialize and inspect the delivery skill template**

Run:

```bash
ls /tmp/opencode/skill-scaffolds
python3 /root/.codingmatrix/project-tpl/.ai-ready/skills/skill-creator/scripts/init_skill.py monkeycode-issue-delivery --path /tmp/opencode/skill-scaffolds
```

Expected: `/tmp/opencode/skill-scaffolds/monkeycode-issue-delivery/` exists for template inspection. Create only the required project files listed in this plan.

- [ ] **Step 2: Write failing state transition tests**

Create `tests/test_inspect_delivery_state.py`:

```python
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
        subprocess.run(["git", "-C", str(self.repo), *args], check=True, capture_output=True, text=True)

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
        result = inspect_state(self.args(issue_url="https://github.com/chaitin/MonkeyCode/issues/910"))
        self.assertEqual(result["state"], "issue-ready")

    def test_feature_branch_without_changes_is_workspace_ready(self):
        self.issue_branch()
        result = inspect_state(self.args(issue_url="https://github.com/chaitin/MonkeyCode/issues/910"))
        self.assertEqual(result["state"], "workspace-ready")

    def test_changes_with_approved_design_are_implemented(self):
        self.issue_branch()
        (self.repo / "change.txt").write_text("change\n", encoding="utf-8")
        result = inspect_state(self.args(issue_url="https://github.com/chaitin/MonkeyCode/issues/910", design_approved=True))
        self.assertEqual(result["state"], "implemented")

    def test_passing_quality_and_acceptance_waits_for_review(self):
        self.issue_branch()
        self.assertEqual(inspect_state(self.accepted_args())["state"], "preview-accepted")

    def test_ready_review_is_reviewed(self):
        self.issue_branch()
        result = inspect_state(self.accepted_args(review_verdict="ready"))
        self.assertEqual(result["state"], "reviewed")

    def test_authorization_request_waits_for_authorization(self):
        self.issue_branch()
        result = inspect_state(self.accepted_args(review_verdict="ready", authorization_requested=True))
        self.assertEqual(result["state"], "ready-for-authorization")

    def test_authorized_delivery_is_ready_to_integrate(self):
        self.issue_branch()
        result = inspect_state(self.accepted_args(review_verdict="ready", authorization_requested=True, git_authorized=True))
        self.assertEqual(result["state"], "ready-to-integrate")

    def test_pr_url_marks_delivery_opened(self):
        result = inspect_state(self.args(pr_url="https://github.com/chaitin/MonkeyCode/pull/911"))
        self.assertEqual(result["state"], "pr-opened")

    def test_reports_fork_remote(self):
        result = inspect_state(self.args())
        self.assertEqual(result["remotes"]["origin"], "https://github.com/chaitin/MonkeyCode.git")
        self.assertEqual(result["remotes"]["fork"], "https://github.com/example/MonkeyCode.git")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 3: Run the test and verify failure**

Run:

```bash
python3 .monkeycode/skills/monkeycode-issue-delivery/tests/test_inspect_delivery_state.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'inspect_delivery_state'`.

- [ ] **Step 4: Implement state inspection**

Create `scripts/inspect_delivery_state.py`:

```python
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path


STATES = (
    "intake-ready",
    "issue-ready",
    "workspace-ready",
    "design-approved",
    "implemented",
    "verified",
    "preview-accepted",
    "reviewed",
    "ready-for-authorization",
    "ready-to-integrate",
    "pr-opened",
)


def _git(repo: Path, *args: str, check: bool = True) -> str:
    completed = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        check=False,
    )
    if check and completed.returncode != 0:
        raise RuntimeError(completed.stderr.strip() or "git command failed")
    return completed.stdout.strip()


def _quality_status(path: Path | None) -> str:
    if path is None:
        return "pending"
    report = json.loads(path.read_text(encoding="utf-8"))
    status = report.get("status")
    return status if status in {"passed", "failed"} else "invalid"


def _remotes(repo: Path) -> dict[str, str]:
    lines = _git(repo, "remote", "-v", check=False).splitlines()
    remotes: dict[str, str] = {}
    for line in lines:
        fields = line.split()
        if len(fields) >= 3 and fields[2] == "(fetch)":
            remotes[fields[0]] = fields[1]
    return remotes


def inspect_state(args: argparse.Namespace) -> dict[str, object]:
    repo = Path(args.repo).resolve()
    branch = _git(repo, "branch", "--show-current")
    status = _git(repo, "status", "--porcelain")
    ahead_text = _git(repo, "rev-list", "--count", f"{args.base_branch}..HEAD", check=False)
    ahead = int(ahead_text) if ahead_text.isdigit() else 0
    quality_status = _quality_status(args.quality_report)
    accepted = args.manual_acceptance in {"passed", "not-required"}
    review_ready = args.review_verdict == "ready"
    has_implementation = bool(status) or ahead > 0

    if args.pr_url:
        state = "pr-opened"
    elif args.git_authorized and review_ready and accepted and quality_status == "passed":
        state = "ready-to-integrate"
    elif args.authorization_requested and review_ready and accepted and quality_status == "passed":
        state = "ready-for-authorization"
    elif review_ready and accepted and quality_status == "passed":
        state = "reviewed"
    elif accepted and quality_status == "passed":
        state = "preview-accepted"
    elif quality_status == "passed":
        state = "verified"
    elif args.design_approved and has_implementation:
        state = "implemented"
    elif args.design_approved:
        state = "design-approved"
    elif args.issue_url and branch != args.base_branch:
        state = "workspace-ready"
    elif args.issue_url:
        state = "issue-ready"
    else:
        state = "intake-ready"

    return {
        "state": state,
        "branch": branch,
        "base_branch": args.base_branch,
        "clean": not bool(status),
        "ahead": ahead,
        "issue_url": args.issue_url,
        "pr_url": args.pr_url,
        "quality_status": quality_status,
        "manual_acceptance": args.manual_acceptance,
        "review_verdict": args.review_verdict,
        "authorization_requested": args.authorization_requested,
        "git_authorized": args.git_authorized,
        "remotes": _remotes(repo),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--base-branch", default="main")
    parser.add_argument("--issue-url")
    parser.add_argument("--design-approved", action="store_true")
    parser.add_argument("--quality-report", type=Path)
    parser.add_argument("--manual-acceptance", choices=("pending", "passed", "not-required"), default="pending")
    parser.add_argument("--review-verdict", choices=("pending", "ready"), default="pending")
    parser.add_argument("--authorization-requested", action="store_true")
    parser.add_argument("--git-authorized", action="store_true")
    parser.add_argument("--pr-url")
    args = parser.parse_args()
    print(json.dumps(inspect_state(args), ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

The state precedence in this implementation preserves the approved sequence: review completion produces `reviewed`; after the orchestrator presents exact Git actions and requests authorization, `--authorization-requested` produces `ready-for-authorization`; explicit user authorization produces `ready-to-integrate`.

- [ ] **Step 5: Run state inspector tests**

Run:

```bash
python3 .monkeycode/skills/monkeycode-issue-delivery/tests/test_inspect_delivery_state.py -v
```

Expected: 10 tests PASS.

- [ ] **Step 6: Commit Task 5**

```bash
git add .monkeycode/skills/monkeycode-issue-delivery/scripts/inspect_delivery_state.py .monkeycode/skills/monkeycode-issue-delivery/tests/test_inspect_delivery_state.py
git commit -m "功能：实现 Issue 交付状态检查器"
```

### Task 6: Delivery Orchestrator Skill and Templates

**Files:**
- Create: `.monkeycode/skills/monkeycode-issue-delivery/SKILL.md`
- Create: `.monkeycode/skills/monkeycode-issue-delivery/references/state-machine.md`
- Create: `.monkeycode/skills/monkeycode-issue-delivery/references/issue-template.md`
- Create: `.monkeycode/skills/monkeycode-issue-delivery/references/pr-report-template.md`
- Create: `.monkeycode/skills/monkeycode-issue-delivery/references/cli.md`

**Interfaces:**
- Consumes: request or Issue, `.monkeycode/workflow.yaml`, state inspector JSON, quality report, preview and review evidence.
- Produces: authorized next action, Chinese Issue/PR content, and final delivery report.

- [ ] **Step 1: Write SKILL.md**

Use this frontmatter:

```yaml
---
name: monkeycode-issue-delivery
description: Orchestrate MonkeyCode work from a conversation request or existing GitHub Issue through isolated branch setup, design routing, implementation, quality gates, SaaS preview, manual acceptance, code review, authorized push, Chinese PR creation, and final delivery reporting. Use when users ask to create or fix an Issue, continue Issue work, compare historical PRs, provide a test environment, push a PR after acceptance, or report Issue/PR/preview outcomes together.
---
```

The workflow body must contain these stages:

1. Load `.monkeycode/workflow.yaml` and local `.monkeycode/MEMORY.md` when present.
2. Normalize dual entry: existing Issue or proposed new Issue.
3. Search duplicate Issues and historical PRs before remote writes.
4. Request authorization before creating a new Issue.
5. Fetch base branch and create an isolated issue branch/worktree.
6. Select fast-fix or standard-feature route.
7. Add `security-review` for matching risk tags.
8. Run implementation and call `quality-gate`.
9. Call `deploy-website` for Web interaction acceptance.
10. Wait for explicit user acceptance.
11. Call `requesting-code-review` on the complete range.
12. Stop on Critical or Important findings and return to implementation.
13. Present exact local and remote Git actions for authorization.
14. Use an existing writable fork after upstream 403.
15. Create a Chinese PR using the reference template and `Fixes #<issue>`.
16. Re-read PR metadata and preview health before final reporting.

The body must explicitly keep implementation, server lifecycle, review findings, and Git integration delegated to their owning skills.

- [ ] **Step 2: Write state-machine.md**

Document every state from Task 5, its evidence, next action, and authorization requirement. Include fast-fix, standard-feature, security-sensitive, Web interaction, Go backend, mixed, and docs routing tables.

- [ ] **Step 3: Write issue-template.md**

Provide a Chinese template with:

```markdown
## 问题描述
## 复现步骤
## 实际表现
## 期望表现
## 代码定位
## 历史参照
## 验收标准
## 我的 UID
```

Require duplicate search and user approval before calling `gh issue create`.

- [ ] **Step 4: Write pr-report-template.md**

Provide a Chinese PR template containing change summary, resolved problems, historical compatibility, automated verification, manual acceptance, preview URL, and `Fixes #<issue>`. Provide a final report template containing Issue URL, PR URL, mergeability, preview health, resolved problems, review result, test result, acceptance result, and fork path when used.

- [ ] **Step 5: Write the state inspector CLI reference**

Create `references/cli.md` with the complete inspector arguments from Task 5, including `--authorization-requested`, all JSON output fields, and one example each for `reviewed`, `ready-for-authorization`, and `ready-to-integrate`.

- [ ] **Step 6: Validate and package the delivery skill**

Run:

```bash
python3 -m unittest discover -s .monkeycode/skills/monkeycode-issue-delivery/tests -p 'test_*.py' -v
python3 /root/.codingmatrix/project-tpl/.ai-ready/skills/skill-creator/scripts/quick_validate.py .monkeycode/skills/monkeycode-issue-delivery
python3 /root/.codingmatrix/project-tpl/.ai-ready/skills/skill-creator/scripts/package_skill.py .monkeycode/skills/monkeycode-issue-delivery /tmp/opencode/skill-packages
```

Expected: all tests PASS; validation passes; `/tmp/opencode/skill-packages/monkeycode-issue-delivery.skill` exists.

- [ ] **Step 7: Commit Task 6**

```bash
git add .monkeycode/skills/monkeycode-issue-delivery/SKILL.md .monkeycode/skills/monkeycode-issue-delivery/references .monkeycode/skills/monkeycode-issue-delivery/scripts .monkeycode/skills/monkeycode-issue-delivery/tests
git commit -m "功能：增加 MonkeyCode Issue 交付编排 Skill"
```

### Task 7: Integration Replay and Final Verification

**Files:**
- Modify: `.monkeycode/skills/quality-gate/tests/test_run_gate.py`
- Modify: `.monkeycode/skills/monkeycode-issue-delivery/tests/test_inspect_delivery_state.py`
- Modify: `docs/superpowers/plans/2026-07-22-monkeycode-issue-delivery-workflow.md`

**Interfaces:**
- Consumes: both packaged skills and the approved frontend Issue #910 evidence shape.
- Produces: final test evidence and completed checklist.

- [ ] **Step 1: Add a frontend replay fixture**

Add a test that feeds these paths to `quality-gate`:

```text
frontend/src/pages/console/user/task/task-detail.tsx
frontend/test/task-restart-dialog-keyboard.test.mjs
docs/superpowers/specs/example.md
```

Assert scope `frontend`, Node `.mjs` test selection, changed-file ESLint, online build, and final diff check.

- [ ] **Step 2: Add a staged-approval replay fixture**

Create a temporary feature branch with one commit. Feed a passing quality report, `manual_acceptance=passed`, and `review_verdict=ready` to the state inspector. Assert `ready-for-authorization`; set `git_authorized=True` and assert `ready-to-integrate`; add a PR URL and assert `pr-opened`.

- [ ] **Step 3: Run all skill tests**

Run:

```bash
python3 -m unittest discover -s .monkeycode/skills/quality-gate/tests -p 'test_*.py' -v
python3 -m unittest discover -s .monkeycode/skills/monkeycode-issue-delivery/tests -p 'test_*.py' -v
```

Expected: all tests PASS.

- [ ] **Step 4: Validate and package both skills**

Run:

```bash
python3 /root/.codingmatrix/project-tpl/.ai-ready/skills/skill-creator/scripts/quick_validate.py .monkeycode/skills/quality-gate
python3 /root/.codingmatrix/project-tpl/.ai-ready/skills/skill-creator/scripts/quick_validate.py .monkeycode/skills/monkeycode-issue-delivery
python3 /root/.codingmatrix/project-tpl/.ai-ready/skills/skill-creator/scripts/package_skill.py .monkeycode/skills/quality-gate /tmp/opencode/skill-packages
python3 /root/.codingmatrix/project-tpl/.ai-ready/skills/skill-creator/scripts/package_skill.py .monkeycode/skills/monkeycode-issue-delivery /tmp/opencode/skill-packages
```

Expected: both validators pass and both `.skill` packages are generated outside the repository.

- [ ] **Step 5: Run repository checks**

Run:

```bash
git diff --check origin/main...HEAD
git status --short
```

Expected: diff check exits 0; status contains only intentional tracked workflow sources and plan checkbox updates.

- [ ] **Step 6: Perform read-only code review**

Review `origin/main...HEAD` against the approved design. Require:

```text
Critical: 0
Important: 0
Ready to merge: Yes
```

- [ ] **Step 7: Commit final replay evidence**

```bash
git add .monkeycode/skills/quality-gate/tests .monkeycode/skills/monkeycode-issue-delivery/tests docs/superpowers/plans/2026-07-22-monkeycode-issue-delivery-workflow.md
git commit -m "测试：验证 Issue 交付工作流完整链路"
```

## Deferred Follow-up Work

The following items require separate plans after this MVP is accepted:

1. Add unified frontend `test` and `verify` package scripts.
2. Add pull-request CI for frontend and backend gates.
3. Correct Ent generated-code output validation.
4. Establish the primary artifact relationship between `.monkeycode/specs` and `docs/superpowers`.
5. Add requirement coverage and tasklist drift checks.
6. Extend the orchestrator into a full lifecycle state machine.
