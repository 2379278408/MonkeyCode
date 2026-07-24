# State Inspector CLI

```bash
python3 .monkeycode/skills/monkeycode-issue-delivery/scripts/inspect_delivery_state.py --repo . --issue-url https://github.com/chaitin/MonkeyCode/issues/910
```

| Argument | Meaning |
|---|---|
| `--repo PATH` | Local repository root |
| `--base-branch NAME` | Base branch; defaults to `main` |
| `--issue-url URL` | Existing or newly created Issue URL |
| `--design-approved` | Concise strategy or formal design approved |
| `--quality-report PATH` | JSON report from `quality-gate` |
| `--manual-acceptance VALUE` | `pending`, `passed`, or `not-required` |
| `--review-verdict VALUE` | `pending` or `ready` |
| `--authorization-requested` | Exact Git actions have been presented |
| `--required-action ACTION` | Enumerated pending write: `issue-create`, `commit`, `push`, `pr-create`, or `pr-edit`; repeatable |
| `--authorized-action ACTION` | One explicitly authorized write; repeatable |
| `--pr-url URL` | Created and verified PR URL |

Output fields are `state`, `branch`, `base_branch`, `clean`, `ahead`, `issue_url`, `pr_url`, `quality_status`, `manual_acceptance`, `review_verdict`, `authorization_requested`, `required_actions`, `authorized_actions`, `pending_actions`, and credential-redacted push `remotes`.

## Reviewed

```bash
python3 .monkeycode/skills/monkeycode-issue-delivery/scripts/inspect_delivery_state.py --repo . --issue-url "$ISSUE_URL" --design-approved --quality-report /tmp/quality.json --manual-acceptance passed --review-verdict ready
```

## Waiting for Authorization

Add `--authorization-requested --required-action commit --required-action push --required-action pr-create` after presenting exact Git actions. Expected state: `ready-for-authorization`.

## Authorized

Add matching `--authorized-action commit --authorized-action push --authorized-action pr-create` after explicit approval. Expected state: `ready-to-integrate`.
