# Delivery State Machine

## States

| State | Required evidence | Next action | Authorization |
|---|---|---|---|
| `intake-ready` | Request received, Issue absent | Draft or identify Issue | Issue creation requires approval |
| `issue-ready` | Issue URL | Create isolated branch/worktree | None |
| `workspace-ready` | Issue URL and non-base branch | Approve fix strategy or design | Design approval |
| `design-approved` | Approved concise strategy or formal design | Implement and test | None |
| `implemented` | Commits or working changes | Run `quality-gate` | None |
| `verified` | Passing quality report | Preview or mark acceptance unnecessary | None |
| `preview-accepted` | Passing quality and accepted/not-required preview | Independent review | User acceptance for Web interaction |
| `reviewed` | Review ready with no Critical or Important findings | Present Git actions | None |
| `ready-for-authorization` | Exact Git actions presented | Await authorization | Commit, push, and PR actions as listed |
| `ready-to-integrate` | Explicit Git authorization | Execute authorized actions | Granted for enumerated actions |
| `pr-opened` | Verified PR URL and metadata | Final report | PR edits require fresh approval |

`--authorization-requested` distinguishes `reviewed` from `ready-for-authorization`. `--git-authorized` advances reviewed and accepted work to `ready-to-integrate`.

## Delivery Routes

| Route | Selection | Required capabilities |
|---|---|---|
| Fast fix | Reproduction, expected behavior, code scope, and acceptance criteria are already clear | Concise strategy, implementation, quality gate, applicable preview, review |
| Standard feature | Requirements or architecture need refinement | `feature-design`, `implementation-planner`, `feature-implementer` |
| Security-sensitive | Auth, input, secrets, API, payment, or sensitive data | Selected route plus `security-review` |

## Change Routes

| Scope | Required evidence |
|---|---|
| Web interaction | Frontend gate, SaaS preview, page/API/assets health, explicit acceptance |
| Go backend | Targeted tests, related package tests, build, review |
| Mixed | Both quality routes plus API integration preview |
| Docs/config | Syntax or format evidence and diff check |

## Fork Recovery

After an upstream 403, preserve the local SHA and use the configured writable fork. Push the same authorized commit with an explicit remote and refspec. Create the PR with upstream as base and `<fork-owner>:<branch>` as head. Report the upstream failure category, fork remote name, branch, SHA, and PR URL with credentials removed.
