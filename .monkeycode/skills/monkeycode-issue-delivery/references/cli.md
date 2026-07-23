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
| `--git-authorized` | User authorized the enumerated Git actions |
| `--pr-url URL` | Created and verified PR URL |

Output fields are `state`, `branch`, `base_branch`, `clean`, `ahead`, `issue_url`, `pr_url`, `quality_status`, `manual_acceptance`, `review_verdict`, `authorization_requested`, `git_authorized`, and credential-redacted `remotes`.

## Reviewed

```bash
python3 .monkeycode/skills/monkeycode-issue-delivery/scripts/inspect_delivery_state.py --repo . --issue-url "$ISSUE_URL" --design-approved --quality-report /tmp/quality.json --manual-acceptance passed --review-verdict ready
```

## Waiting for Authorization

Add `--authorization-requested` after presenting exact Git actions. Expected state: `ready-for-authorization`.

## Authorized

Add `--authorization-requested --git-authorized` after explicit approval. Expected state: `ready-to-integrate`.
