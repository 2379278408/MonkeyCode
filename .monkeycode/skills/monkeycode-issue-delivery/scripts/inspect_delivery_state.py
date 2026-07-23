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
    status = report.get("status")
    return status if status in {"passed", "failed"} else "invalid"


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
        if len(fields) >= 3 and fields[2] == "(fetch)":
            remotes[fields[0]] = _redact_remote_url(fields[1])
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
    parser.add_argument(
        "--manual-acceptance",
        choices=("pending", "passed", "not-required"),
        default="pending",
    )
    parser.add_argument("--review-verdict", choices=("pending", "ready"), default="pending")
    parser.add_argument("--authorization-requested", action="store_true")
    parser.add_argument("--git-authorized", action="store_true")
    parser.add_argument("--pr-url")
    args = parser.parse_args()
    print(json.dumps(inspect_state(args), ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
