from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path


def _normalize_path(path: str) -> str:
    normalized = path.strip()
    while normalized.startswith("./"):
        normalized = normalized[2:]
    return normalized


def classify_paths(paths: list[str]) -> dict[str, object]:
    normalized = sorted({_normalize_path(path) for path in paths if path.strip()})
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
    staged = _git(repo, "diff", "--cached", "--name-only", "--diff-filter=ACMRT")
    working = _git(repo, "diff", "--name-only", "--diff-filter=ACMRT")
    untracked = _git(repo, "ls-files", "--others", "--exclude-standard")
    return sorted(set(committed + staged + working + untracked))


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
