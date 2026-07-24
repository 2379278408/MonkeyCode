from __future__ import annotations

import argparse
import json
import re
import shlex
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

from detect_scope import changed_paths as git_changed_paths
from detect_scope import classify_paths
from workflow_config import WorkflowConfigError, load_workflow, require_string


@dataclass(frozen=True)
class Check:
    name: str
    argv: list[str]
    cwd: Path


class GatePlanError(ValueError):
    pass


def redact(text: str) -> str:
    patterns = (
        r"(?i)(token\s*[=:]\s*)\S+",
        r"(?i)(password\s*[=:]\s*)\S+",
        r"(?i)(secret\s*[=:]\s*)\S+",
        r"(?i)(api[_-]?key\s*[=:]\s*)\S+",
        r"(?i)(authorization\s*[=:]\s*(?:bearer\s+)?)\S+",
    )
    for pattern in patterns:
        text = re.sub(pattern, r"\1[REDACTED]", text)
    return text[-4000:]


def _redact_url(value: str) -> str:
    parsed = urlsplit(value)
    if not parsed.scheme or parsed.hostname is None or parsed.username is None:
        return value
    host = parsed.hostname
    if parsed.port is not None:
        host = f"{host}:{parsed.port}"
    return urlunsplit((parsed.scheme, host, parsed.path, parsed.query, parsed.fragment))


def redact_command(argv: list[str]) -> list[str]:
    sensitive_flags = {"--token", "--password", "--secret", "--api-key", "--api_key", "--authorization"}
    result: list[str] = []
    redact_next = False
    for argument in argv:
        if redact_next:
            result.append("[REDACTED]")
            redact_next = False
            continue
        result.append(redact(_redact_url(argument)))
        if argument.lower() in sensitive_flags:
            redact_next = True
    return result


def _argv(config: dict[str, object], key: str) -> list[str]:
    return shlex.split(require_string(config, key))


def _configured_root(repo: Path, root: str) -> Path:
    candidate = (repo / root).resolve()
    if not candidate.is_relative_to(repo):
        raise GatePlanError(f"configured root must be inside repository: {root}")
    return candidate


def _relative(path: str, repo: Path, root: Path) -> str:
    candidate = (repo / path).resolve()
    if not candidate.is_relative_to(root):
        raise GatePlanError(f"path must be inside {root.relative_to(repo)}: {path}")
    return str(candidate.relative_to(root))


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
        frontend_cwd = _configured_root(repo, frontend_root)
        if not target_tests:
            raise GatePlanError("frontend scope requires at least one targeted test")
        for target in target_tests:
            relative_target = _relative(target, repo, frontend_cwd)
            if target.endswith(".mjs"):
                runner_key = "frontend.targeted_test_mjs"
            elif target.endswith(".ts"):
                runner_key = "frontend.targeted_test_ts"
            else:
                raise GatePlanError(f"unsupported frontend test extension: {target}")
            checks.append(
                Check(
                    f"frontend-test:{relative_target}",
                    _argv(config, runner_key) + [relative_target],
                    frontend_cwd,
                )
            )

        lint_paths = [
            _relative(path, repo, frontend_cwd)
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
        backend_cwd = _configured_root(repo, backend_root)
        if not backend_tests:
            raise GatePlanError("backend scope requires at least one targeted test selector")
        for index, selector in enumerate(backend_tests, start=1):
            checks.append(
                Check(
                    f"backend-test:{index}",
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
                "command": redact_command(check.argv),
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
            {"name": check.name, "command": redact_command(check.argv), "cwd": str(check.cwd)}
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
    parser.add_argument("--path", action="append", dest="paths")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    repo = args.repo.resolve()
    scope = args.scope
    paths: list[str] = []
    try:
        config_path = args.config if args.config.is_absolute() else repo / args.config
        config = load_workflow(config_path)
        paths = args.paths if args.paths is not None else git_changed_paths(repo, args.base, args.head)
        detected = classify_paths(paths)
        scope = detected["scope"] if args.scope == "auto" else args.scope
        checks = build_check_plan(config, scope, paths, args.target_test, args.backend_test, repo)
        report = _planned(checks) if args.dry_run else run_checks(checks)
    except (WorkflowConfigError, ValueError, subprocess.CalledProcessError, OSError) as error:
        report = {
            "status": "failed",
            "scope": scope,
            "paths": paths,
            "checks": [],
            "blockers": ["quality gate setup failed"],
            "evidence": {"completed_checks": [], "failed_checks": []},
            "error": {
                "category": type(error).__name__,
                "message": redact(str(error)),
                "recovery": "fix the reported configuration, path, or Git input and rerun dry-run",
            },
        }
        print(json.dumps(report, ensure_ascii=False, sort_keys=True))
        return 2
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
