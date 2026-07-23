---
name: quality-gate
description: Use when validating MonkeyCode frontend, Go backend, documentation, configuration, or mixed changes before review, preview, commit, or PR, and when a failed gate needs scoped repair and revalidation.
---

# Quality Gate

## Overview

Build and execute reproducible checks from `.monkeycode/workflow.yaml`. Treat the dry-run command plan and structured report as the evidence contract.

## Workflow

1. Read `.monkeycode/workflow.yaml`.
2. Run `scripts/detect_scope.py` for the requested Git range or explicit paths.
3. Collect targeted frontend test paths and Go test selectors from the implementation plan.
4. Run `scripts/run_gate.py --dry-run` and inspect every argument array and working directory.
5. Run the same command without `--dry-run`.
6. Stop at the first failure and report its command, exit code, redacted output, and recovery entry point.
7. Return the contract in `references/result-schema.md`.

Use `references/cli.md` for arguments and examples.

## Scope Rules

| Scope | Required checks |
|---|---|
| frontend | Targeted tests, changed-file ESLint, online build, diff check |
| backend | Targeted tests, related package tests, build, diff check |
| mixed | Frontend and backend checks, one final diff check |
| docs | Diff check |

Explicit targeted tests remain the caller's responsibility. An empty targeted-test list means the plan contains no targeted test command.

## Failure Handling

- Preserve the failed report as evidence.
- Repair only the failed scope when mutation is authorized.
- Re-run the failed check and every later check in the plan.
- Generate a fresh report for review and delivery state inspection.

Keep server startup, Git commits, pushes, and PR operations outside this skill. Use `deploy-website` for runtime preview and `monkeycode-issue-delivery` for authorization and Git routing.
