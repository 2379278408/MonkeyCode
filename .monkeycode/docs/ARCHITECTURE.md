# MonkeyCode 开发交付工作流架构

## 概述

MonkeyCode 使用仓库内版本化的 skill 和配置文件组织 Issue 到 Pull Request 的完整开发链。`monkeycode-issue-delivery` 负责状态、路由、授权和交付报告，`quality-gate` 负责生成并执行可复现的测试、Lint、构建和差异检查计划。

产品设计、代码实现、Web 预览、代码复审和分支收尾继续由专用 skill 处理。编排层只组合证据和控制阶段边界，从而让每个 Issue 保持独立分支、独立 worktree、独立提交和独立 PR。

## 技术栈

| 区域 | 技术与工具 |
|---|---|
| 工作流 | Python 3.11+ 标准库、YAML 配置、Git、GitHub CLI |
| Web 前端 | Node.js 20.19+、pnpm 9、React、Vite、TypeScript、ESLint |
| 后端 | Go 1.25、PostgreSQL、Redis、Ent、Swagger |
| 桌面端 | Electron、electron-builder、pnpm |
| 移动端 | Expo、React Native、npm、Jest |
| 构建 | Vite、Go toolchain、Docker Buildx、GitHub Actions |

## 工作流目录

```text
.monkeycode/
├── workflow.yaml
├── docs/
│   ├── INDEX.md
│   ├── ARCHITECTURE.md
│   ├── INTERFACES.md
│   └── DEVELOPER_GUIDE.md
└── skills/
    ├── monkeycode-issue-delivery/
    │   ├── SKILL.md
    │   ├── references/
    │   ├── scripts/
    │   └── tests/
    └── quality-gate/
        ├── SKILL.md
        ├── references/
        ├── scripts/
        └── tests/
```

## 端到端交付链

```mermaid
flowchart LR
    A["对话需求或 GitHub Issue"] --> B["monkeycode-issue-delivery"]
    B --> C["独立分支与 worktree"]
    C --> D["设计与实施"]
    D --> E["quality-gate"]
    E --> F["SaaS online 预览"]
    F --> G["用户人工验收"]
    G --> H["完整范围代码复审"]
    H --> I["逐项 Git 授权"]
    I --> J["中文 commit、push 和 PR"]
```

## 子系统职责

### `monkeycode-issue-delivery`

- 接收对话需求或已有 Issue。
- 查找重复 Issue、历史修复和相邻 PR。
- 准备最新 `main`、独立分支和 worktree。
- 在快速修复与标准功能路径之间分流。
- 汇总质量、预览、验收和复审证据。
- 对 Issue 创建、commit、push、PR 创建和 PR 编辑执行逐项授权。
- 上游返回 403 时使用已有可写 fork 延续同一授权操作。

### `quality-gate`

- 根据 Git 范围或显式路径识别 `frontend`、`backend`、`mixed` 和 `docs` scope。
- 前端执行定向测试、变更文件 ESLint、online build 和 diff check。
- 后端执行定向测试、全量测试、全量 build 和 diff check。
- 以 JSON 输出计划、成功证据、失败命令和恢复入口。
- 对命令参数、日志和 remote URL 中的敏感信息进行脱敏。
- 校验工作目录和目标文件均位于仓库允许范围内。

### 下游能力

| Skill | 职责 |
|---|---|
| `feature-design` | 正式需求和技术设计 |
| `implementation-planner` | 多步骤实施计划 |
| `feature-implementer` | 按批准计划实现代码和测试 |
| `security-review` | 认证、输入、密钥、API 和敏感数据复核 |
| `deploy-website` | 启动服务、管理后台终端和提供预览 URL |
| `requesting-code-review` | 审查完整 base-to-head 范围 |
| `finishing-a-development-branch` | 经授权完成分支集成和 PR 收尾 |

## 状态模型

```text
intake-ready
  -> issue-ready
  -> workspace-ready
  -> design-approved
  -> implemented
  -> verified
  -> preview-accepted
  -> reviewed
  -> ready-for-authorization
  -> ready-to-integrate
  -> pr-opened
```

状态由 Issue、Git 工作树、质量报告、人工验收、复审结论、授权动作和 PR 元数据动态推导。远程写入发生在相应授权动作完成之后。

## 关键设计边界

- `.monkeycode/workflow.yaml` 保存项目级确定性命令和策略。
- skill 保存需要判断的流程规则与恢复路径。
- Python 脚本只执行有限时长的检查与状态推导。
- Web 服务生命周期由后台终端管理。
- UI 交互改动要求 online 预览和明确人工验收。
- GitHub Actions 当前主要覆盖 `main` 上的 online 前端构建，PR 质量证据由本地 `quality-gate` 生成。
