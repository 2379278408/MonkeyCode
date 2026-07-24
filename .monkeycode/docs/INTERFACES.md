# MonkeyCode 工作流接口

## 配置接口

配置文件：`.monkeycode/workflow.yaml`

| 配置 | 当前值 | 用途 |
|---|---|---|
| `base_branch` | `main` | Issue 分支基线 |
| `language` | `zh-CN` | commit、PR 和报告语言 |
| `pull_request.link_keyword` | `Fixes` | PR 与 Issue 自动关联 |
| `pull_request.require_manual_acceptance_for_ui` | `true` | UI 改动人工验收门禁 |
| `frontend.targeted_test_ts` | `tsx --test` | TypeScript 定向测试 |
| `frontend.targeted_test_mjs` | `node --test` | ESM 定向测试 |
| `frontend.lint_changed` | `pnpm exec eslint` | 变更文件 Lint |
| `frontend.build_online` | `pnpm run build:online` | online 构建 |
| `preview.target` | `https://monkeycode-ai.com` | online 预览 API 目标 |
| `backend.targeted_test` | `go test` | Go 定向测试 |
| `backend.related_test` | `go test ./...` | Go 全量测试 |
| `backend.build` | `go build ./...` | Go 全量构建 |

## 变更范围检测器

入口：`.monkeycode/skills/quality-gate/scripts/detect_scope.py`

```bash
python3 .monkeycode/skills/quality-gate/scripts/detect_scope.py \
  --repo . \
  --base origin/main \
  --head HEAD
```

输出 scope：

- `frontend`
- `backend`
- `mixed`
- `docs`
- `none`

## 质量门禁执行器

入口：`.monkeycode/skills/quality-gate/scripts/run_gate.py`

### 前端计划

```bash
python3 .monkeycode/skills/quality-gate/scripts/run_gate.py \
  --repo . \
  --scope frontend \
  --path frontend/src/example.tsx \
  --target-test frontend/test/example.test.ts \
  --dry-run
```

移除 `--dry-run` 后执行同一计划。每个 `.ts`、`.tsx` 定向测试由 `tsx --test` 执行，每个 `.mjs` 定向测试由 `node --test` 执行。

### 后端计划

```bash
python3 .monkeycode/skills/quality-gate/scripts/run_gate.py \
  --repo . \
  --scope backend \
  --path backend/pkg/example/example.go \
  --backend-test './pkg/example -run TestExample' \
  --dry-run
```

### 文档计划

```bash
python3 .monkeycode/skills/quality-gate/scripts/run_gate.py \
  --repo . \
  --scope docs \
  --path .monkeycode/docs/DEVELOPER_GUIDE.md
```

### 退出码

| 退出码 | 含义 |
|---|---|
| `0` | 计划成功或全部检查通过 |
| `1` | 质量检查失败 |
| `2` | 配置、参数、路径、Git ref 或必需定向测试存在 setup failure |

### JSON 证据

报告包含：

- `scope`
- `paths`
- `status`
- `checks`
- `blockers`
- `evidence.completed_checks`
- `evidence.failed_checks`

命令、日志和 URL 中的凭据会在输出前脱敏。调用方应保存完整 JSON 作为代码复审和交付状态的质量证据。

## Issue 交付状态检查器

入口：`.monkeycode/skills/monkeycode-issue-delivery/scripts/inspect_delivery_state.py`

```bash
python3 .monkeycode/skills/monkeycode-issue-delivery/scripts/inspect_delivery_state.py \
  --repo . \
  --issue-url https://github.com/chaitin/MonkeyCode/issues/915 \
  --design-approved \
  --quality-report /tmp/quality.json \
  --manual-acceptance passed \
  --review-verdict ready \
  --authorization-requested \
  --required-action commit \
  --required-action push \
  --required-action pr-create
```

授权完成时，为每个必需动作追加对应的 `--authorized-action`。可用动作以 CLI `--help` 和 `references/cli.md` 为准。

## Skill 调用入口

新环境加载仓库后，在 Agent 中使用：

```text
使用 monkeycode-issue-delivery 处理 GitHub Issue <ISSUE_URL>
```

编排器会读取 `.monkeycode/workflow.yaml`，并在质量阶段调用 `quality-gate`。涉及 UI 时，流程会进入 `deploy-website` 和人工验收阶段。
