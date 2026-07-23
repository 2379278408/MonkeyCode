# Result Schema

Every report contains:

| Field | Type | Meaning |
|---|---|---|
| `status` | string | `planned`, `passed`, or `failed` |
| `scope` | string | Selected change scope |
| `paths` | string array | Detected repository-relative paths |
| `checks` | object array | Planned or completed checks |
| `blockers` | string array | Conditions blocking progression |
| `evidence` | object | Completed and failed check names |

An executed check contains `name`, command argument array, `cwd`, `exit_code`, `duration_ms`, redacted `stdout`, and redacted `stderr`. A planned check contains `name`, command, and `cwd`.

## Passing Example

```json
{
  "status": "passed",
  "scope": "docs",
  "paths": ["docs/change.md"],
  "checks": [
    {
      "name": "git-diff-check",
      "command": ["git", "diff", "--check"],
      "cwd": "/workspace/MonkeyCode",
      "exit_code": 0,
      "duration_ms": 12,
      "stdout": "",
      "stderr": ""
    }
  ],
  "blockers": [],
  "evidence": {
    "completed_checks": ["git-diff-check"],
    "failed_checks": []
  }
}
```

## Failed Example

```json
{
  "status": "failed",
  "scope": "frontend",
  "paths": ["frontend/src/App.tsx"],
  "checks": [
    {
      "name": "frontend-lint",
      "command": ["pnpm", "exec", "eslint", "src/App.tsx"],
      "cwd": "/workspace/MonkeyCode/frontend",
      "exit_code": 1,
      "duration_ms": 420,
      "stdout": "",
      "stderr": "src/App.tsx: lint error"
    }
  ],
  "blockers": ["quality gate failed"],
  "evidence": {
    "completed_checks": ["frontend-lint"],
    "failed_checks": ["frontend-lint"]
  }
}
```
