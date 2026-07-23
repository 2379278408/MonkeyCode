---
name: monkeycode-issue-delivery
description: Use when a MonkeyCode request or GitHub Issue must be delivered through an isolated branch to a reviewed PR, especially when work needs staged authorization, SaaS preview acceptance, fork fallback, or a combined Issue, PR, and preview report.
---

# MonkeyCode Issue Delivery

## Overview

Route a conversation request or existing Issue through one evidence-based state machine. Keep remote writes and Git history changes behind explicit authorization.

## Workflow

1. Read `.monkeycode/workflow.yaml` and local `.monkeycode/MEMORY.md` when present.
2. Normalize the entry as an existing Issue or proposed new Issue.
3. Search duplicate Issues, related code, and historical PRs with read-only operations.
4. For a proposed Issue, draft `references/issue-template.md` and request authorization before `gh issue create`.
5. Fetch the configured base and create an isolated Issue branch and worktree.
6. Choose a route:
   - Fast fix: approve a concise fix and test strategy.
   - Standard feature: use `feature-design`, `implementation-planner`, and `feature-implementer`.
7. Use `security-review` when authentication, user input, secrets, API endpoints, payment, or sensitive data are in scope.
8. Use `quality-gate` for targeted tests, lint, builds, and diff evidence.
9. For Web interaction changes, use `deploy-website`, verify page, API, and critical assets, then wait for explicit acceptance.
10. Use `requesting-code-review` on the complete base-to-head range. Return Critical or Important findings to implementation and revalidation.
11. Run `scripts/inspect_delivery_state.py` and follow `references/state-machine.md`.
12. Present exact files, commit message, remote, refspec, PR base/head, title, and body before each authorized Git action.
13. Request explicit authorization for Issue creation, commit, push, and PR creation or editing. An authorization may cover a clearly enumerated batch.
14. After upstream 403, use an existing writable fork for the same authorized commit and report the fork path.
15. Create a Chinese PR from `references/pr-report-template.md` with `Fixes #<issue>`.
16. Re-read PR metadata, mergeability, checks, and preview health before the final report.

Implementation belongs to the implementation skills. Server lifecycle belongs to `deploy-website`; review findings belong to `requesting-code-review`; branch integration belongs to `finishing-a-development-branch`.

## Resources

- Read `references/state-machine.md` for evidence, routing, and authorization.
- Read `references/issue-template.md` when drafting a new Issue.
- Read `references/pr-report-template.md` before PR creation and final reporting.
- Read `references/cli.md` when deriving or testing delivery state.
