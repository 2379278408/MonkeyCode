# CLI Reference

## Scope Detection

```bash
python3 .monkeycode/skills/quality-gate/scripts/detect_scope.py --repo . --base origin/main --head HEAD
```

| Argument | Meaning |
|---|---|
| `--repo PATH` | Repository root; defaults to the current directory |
| `--base REF` | Git merge-base side; defaults to `origin/main` |
| `--head REF` | Git head side; defaults to `HEAD` |
| `--path PATH` | Classify an explicit path; repeatable and bypasses Git discovery |

The command prints `scope`, `categories`, and normalized repository-relative `paths` as JSON.

## Gate Planning and Execution

```bash
python3 .monkeycode/skills/quality-gate/scripts/run_gate.py --repo . --scope frontend --path frontend/src/App.tsx --target-test frontend/test/example.test.mjs --dry-run
```

```bash
python3 .monkeycode/skills/quality-gate/scripts/run_gate.py --repo . --scope frontend --target-test frontend/test/example.test.mjs
```

| Argument | Meaning |
|---|---|
| `--repo PATH` | Repository root; defaults to the current directory |
| `--config PATH` | Workflow configuration; defaults to `.monkeycode/workflow.yaml` |
| `--base REF` | Git merge-base side; defaults to `origin/main` |
| `--head REF` | Git head side; defaults to `HEAD` |
| `--scope VALUE` | `auto`, `frontend`, `backend`, `mixed`, or `docs` |
| `--target-test PATH` | Repository-relative frontend test; repeatable |
| `--backend-test SELECTOR` | Arguments appended to configured `go test`; repeatable |
| `--path PATH` | Use an explicit changed path for planning; repeatable and bypasses Git discovery |
| `--dry-run` | Print the plan without executing checks |

Checks use configured working directories and argument arrays. Execution stops at the first failure. Exit code `0` means planned or passed; exit code `1` means failed.

Setup failures such as missing targeted tests, invalid roots, paths outside configured roots, bad Git refs, and invalid configuration return structured JSON with exit code `2`.
