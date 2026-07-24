from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit


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
    try:
        report = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return "invalid"
    if not isinstance(report, dict):
        return "invalid"
    required = {
        "status": str,
        "scope": str,
        "paths": list,
        "checks": list,
        "blockers": list,
        "evidence": dict,
    }
    if any(not isinstance(report.get(key), expected) for key, expected in required.items()):
        return "invalid"
    status = report["status"]
    if status not in {"passed", "failed"}:
        return "invalid"
    if status == "passed":
        if report["blockers"]:
            return "invalid"
        if any(not isinstance(check, dict) or check.get("exit_code") != 0 for check in report["checks"]):
            return "invalid"
    return status


def _redact_remote_url(url: str) -> str:
    parsed = urlsplit(url)
    if not parsed.scheme or parsed.hostname is None:
        return url
    host = parsed.hostname
    if parsed.port is not None:
        host = f"{host}:{parsed.port}"
    return urlunsplit((parsed.scheme, host, parsed.path, parsed.query, parsed.fragment))


def _remotes(repo: Path) -> dict[str, str]:
    lines = _git(repo, "remote", "-v", check=False).splitlines()
    remotes: dict[str, str] = {}
    for line in lines:
        fields = line.split()
        if len(fields) >= 3 and fields[2] == "(push)":
            remotes[fields[0]] = _redact_remote_url(fields[1])
    return remotes


def _valid_pr_url(url: str | None) -> bool:
    if not url:
        return False
    parsed = urlsplit(url)
    parts = [part for part in parsed.path.split("/") if part]
    return parsed.scheme == "https" and parsed.hostname == "github.com" and len(parts) == 4 and parts[2] == "pull" and parts[3].isdigit()


def _has_implementation(repo: Path, status: str, ahead: int, quality_report: Path | None) -> bool:
    ignored = quality_report.resolve() if quality_report is not None else None
    for line in status.splitlines():
        changed = line[3:].split(" -> ")[-1]
        if ignored is None or (repo / changed).resolve() != ignored:
            return True
    return ahead > 0


def inspect_state(args: argparse.Namespace) -> dict[str, object]:
    repo = Path(args.repo).resolve()
    branch = _git(repo, "branch", "--show-current")
    status = _git(repo, "status", "--porcelain")
    ahead_text = _git(repo, "rev-list", "--count", f"{args.base_branch}..HEAD", check=False)
    ahead = int(ahead_text) if ahead_text.isdigit() else 0
    quality_status = _quality_status(args.quality_report)
    accepted = args.manual_acceptance in {"passed", "not-required"}
    review_ready = args.review_verdict == "ready"
    has_implementation = _has_implementation(repo, status, ahead, args.quality_report)
    required_actions = set(args.required_actions)
    authorized_actions = set(args.authorized_actions)
    actions_authorized = bool(required_actions) and required_actions <= authorized_actions
    issue_ready = bool(args.issue_url)
    workspace_ready = issue_ready and branch != args.base_branch
    design_ready = workspace_ready and args.design_approved
    implementation_ready = design_ready and has_implementation
    verified_ready = implementation_ready and quality_status == "passed"
    accepted_ready = verified_ready and accepted
    reviewed_ready = accepted_ready and review_ready
    authorization_ready = reviewed_ready and args.authorization_requested and bool(required_actions)
    integration_ready = authorization_ready and actions_authorized
    pr_ready = integration_ready and "pr-create" in authorized_actions and _valid_pr_url(args.pr_url)
    blockers: list[str] = []
    if args.pr_url and not pr_ready:
        blockers.append("pr-url requires the complete authorized delivery chain")
    if quality_status == "passed" and not implementation_ready:
        blockers.append("quality report requires issue, workspace, design, and implementation evidence")

    if pr_ready:
        state = "pr-opened"
    elif integration_ready:
        state = "ready-to-integrate"
    elif authorization_ready:
        state = "ready-for-authorization"
    elif reviewed_ready:
        state = "reviewed"
    elif accepted_ready:
        state = "preview-accepted"
    elif verified_ready:
        state = "verified"
    elif implementation_ready:
        state = "implemented"
    elif design_ready:
        state = "design-approved"
    elif workspace_ready:
        state = "workspace-ready"
    elif issue_ready:
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
        "required_actions": sorted(required_actions),
        "authorized_actions": sorted(authorized_actions),
        "pending_actions": sorted(required_actions - authorized_actions),
        "blockers": blockers,
        "remotes": _remotes(repo),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--base-branch", default="main")
    parser.add_argument("--issue-url")
    parser.add_argument("--design-approved", action="store_true")
    parser.add_argument("--quality-report", type=Path)
    parser.add_argument(
        "--manual-acceptance",
        choices=("pending", "passed", "not-required"),
        default="pending",
    )
    parser.add_argument("--review-verdict", choices=("pending", "ready"), default="pending")
    parser.add_argument("--authorization-requested", action="store_true")
    actions = ("issue-create", "commit", "push", "pr-create", "pr-edit")
    parser.add_argument("--required-action", dest="required_actions", choices=actions, action="append", default=[])
    parser.add_argument("--authorized-action", dest="authorized_actions", choices=actions, action="append", default=[])
    parser.add_argument("--pr-url")
    args = parser.parse_args()
    print(json.dumps(inspect_state(args), ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
