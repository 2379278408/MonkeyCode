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
    try:
        return str(Path(path).relative_to(root))
    except ValueError as error:
        raise ValueError(f"path must be inside {root}: {path}") from error


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
            if target.endswith(".mjs"):
                runner_key = "frontend.targeted_test_mjs"
            elif target.endswith(".ts"):
                runner_key = "frontend.targeted_test_ts"
            else:
                raise ValueError(f"unsupported frontend test extension: {target}")
            checks.append(
                Check(
                    f"frontend-test:{relative_target}",
                    _argv(config, runner_key) + [relative_target],
                    frontend_cwd,
                )
            )

        lint_paths = [
            _relative(path, frontend_root)
            for path in changed_paths
            if path.startswith(f"{frontend_root}/")
            and Path(path).suffix in {".ts", ".tsx", ".js", ".jsx", ".mjs"}
        ]
        if lint_paths:
            checks.append(
                Check(
                    "frontend-lint",
                    _argv(config, "frontend.lint_changed") + lint_paths,
                    frontend_cwd,
                )
            )
        checks.append(
            Check("frontend-build-online", _argv(config, "frontend.build_online"), frontend_cwd)
        )

    if scope in {"backend", "mixed"}:
        backend_root = require_string(config, "backend.root")
        backend_cwd = repo / backend_root
        for selector in backend_tests:
            checks.append(
                Check(
                    f"backend-test:{selector}",
                    _argv(config, "backend.targeted_test") + shlex.split(selector),
                    backend_cwd,
                )
            )
        checks.append(
            Check("backend-related-tests", _argv(config, "backend.related_test"), backend_cwd)
        )
        checks.append(Check("backend-build", _argv(config, "backend.build"), backend_cwd))

    checks.append(Check("git-diff-check", _argv(config, "common.diff_check"), repo))
    return checks


def _output_text(value: str | bytes | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode(errors="replace")
    return value


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
            stdout = redact(_output_text(error.stdout))
            stderr = redact(_output_text(error.stderr) or "timeout after 600 seconds")
        except OSError as error:
            exit_code = 127
            stdout = ""
            stderr = redact(str(error))
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
    passed = len(results) == len(checks) and all(item["exit_code"] == 0 for item in results)
    return {"status": "passed" if passed else "failed", "checks": results}


def _planned(checks: list[Check]) -> dict[str, object]:
    return {
        "status": "planned",
        "checks": [
            {"name": check.name, "command": check.argv, "cwd": str(check.cwd)}
            for check in checks
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--config", type=Path, default=Path(".monkeycode/workflow.yaml"))
    parser.add_argument("--base", default="origin/main")
    parser.add_argument("--head", default="HEAD")
    parser.add_argument(
        "--scope",
        choices=("auto", "frontend", "backend", "mixed", "docs"),
        default="auto",
    )
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
    failed_checks = [
        item["name"] for item in report["checks"] if item.get("exit_code", 0) != 0
    ]
    report.update(
        {
            "scope": scope,
            "paths": paths,
            "blockers": [] if report["status"] != "failed" else ["quality gate failed"],
            "evidence": {
                "completed_checks": [item["name"] for item in report["checks"]],
                "failed_checks": failed_checks,
            },
        }
    )
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 1 if report["status"] == "failed" else 0


if __name__ == "__main__":
    raise SystemExit(main())
