# MonkeyCode Issue 到 PR 交付工作流设计

## 状态

- 日期：2026-07-22
- 状态：设计已批准
- 第一版重点：双入口、分阶段授权的 Issue 到 PR 交付

## 背景

MonkeyCode 当前已经形成完整的开发交付链：Issue 或需求输入、规格和设计、实施计划、测试驱动实现、质量检查、SaaS 预览、用户验收、独立复审、中文 PR 和最终汇报。

这些步骤分散在 `.monkeycode/MEMORY.md`、`.monkeycode/specs/`、`docs/superpowers/`、GitHub 工作流、项目脚本和多个通用 skill 中。高频 Issue 修复仍需要人工重复执行分支准备、历史 PR 对比、质量命令选择、预览配置、验收记录、fork 推送和交付汇报。

本设计通过轻量编排 skill 和统一质量门禁 skill 固化高频路径，并继续复用现有设计、实现、预览、审查和分支收尾能力。

## 当前工作流盘点

### 已形成的端到端阶段

1. 接收对话需求或已有 GitHub Issue。
2. 查找重复 Issue、历史修复和相邻 PR。
3. 从最新 `main` 创建独立分支和 worktree。
4. 根据任务复杂度形成简短方案或正式需求、设计和计划。
5. 编写回归测试并实施最小改动。
6. 运行专项测试、Lint、类型检查、构建和差异检查。
7. 启动 online 预览并连接 SaaS 后端。
8. 用户在登录态完成交互验收。
9. 对完整 Git range 进行独立代码复审。
10. 经用户授权后 commit、push 和创建中文 PR。
11. 汇报 Issue、PR、测试环境、解决内容和验证结论。

### 已有项目约定

- 每个 Issue 使用独立分支、独立提交和独立 PR。
- 新分支基于最新 `main`。
- 前端使用 pnpm，最低质量门禁包含专项测试、Lint 和 `build:online`。
- Web 交互改动先提供预览，用户验收通过后再进入 Git 提交和远程操作。
- 提交信息、PR 标题和 PR 描述使用中文。
- Issue 正文包含用户要求的 UID；UID 属于个人本地偏好。
- 前端 online 预览通过 `TARGET=https://monkeycode-ai.com` 连接 SaaS。
- 安全敏感改动需要防御性安全复核。

### 当前主要损耗

1. `.monkeycode/specs/` 与 `docs/superpowers/` 构成两套规格和计划体系，阶段边界存在重叠。
2. 前端测试、Lint 和构建缺少统一质量入口，执行方式依赖文件扩展名和 Node 版本。
3. GitHub Actions 仅在 `main` push 后构建 online 前端，PR 阶段缺少统一自动门禁。
4. 预览依赖路径授权、API 代理和 SaaS 状态，环境问题容易表现为产品回归。
5. 上游写权限、fork remote 和跨仓 PR 路径每次需要重新判断。
6. PR 描述和最终汇报每次重复整理相同字段。
7. 计划 checkbox 与实际实施状态容易漂移。
8. Go 生成代码检查存在输出目录配置风险，需要独立治理。

## 目标

1. 提供一个双入口 Issue 交付编排器，支持对话需求和已有 Issue。
2. 使用分阶段授权控制创建 Issue、commit、push 和创建 PR 等副作用。
3. 统一前端、Go 后端、文档和混合改动的质量验证结果。
4. 复用现有 skill，保持每个 skill 的单一职责。
5. 为每次交付稳定生成结构一致的中文 PR 和最终汇报。
6. 支持失败恢复、历史 PR 兼容性检查和 fork PR 路径。
7. 为后续配置驱动的完整生命周期状态机保留扩展接口。

## 首版范围边界

首版聚焦 Issue 到 PR 的高频交付链。CI 改造、规格目录统一、Ent 生成门禁修复、多平台发布和完整项目 Wiki 同步进入后续阶段。

## 方案比较

### 方案 A：单体交付 skill

一个 skill 内包含需求、设计、实现、测试、预览、审查和 Git 收尾。该方案落地快，职责重叠和上下文体积会随功能增加而增长。

### 方案 B：轻量编排器加统一质量门禁

创建 `monkeycode-issue-delivery` 和 `quality-gate` 两个 skill。编排器负责状态、路由、授权和交付报告；现有 skill 继续处理设计、实现、预览、审查和分支收尾。

该方案提供清晰边界、较小首版范围和良好扩展性，作为本设计的推荐方案。

### 方案 C：配置驱动的完整状态机

建立完整 feature manifest、运行状态持久化、统一输入输出信封和生命周期路由器。该方案适合作为长期方向，需要同步改造现有规则、文档体系、skill 契约和 CI。

## 总体架构

```text
用户需求或 Issue
  -> monkeycode-issue-delivery
  -> Issue 就绪
  -> 独立 worktree 和分支
  -> 复杂度与风险分流
  -> 设计、计划和实现能力
  -> quality-gate
  -> deploy-website 和人工验收
  -> requesting-code-review
  -> Git 操作授权
  -> finishing-a-development-branch
  -> 中文 PR 和交付汇报
```

### 新建 skill

#### monkeycode-issue-delivery

职责：

- 识别对话需求或已有 Issue。
- 查重并准备 Issue 内容。
- 检查最新主分支、独立分支和 worktree。
- 推导当前交付状态。
- 根据复杂度、技术栈和风险标签选择下游 skill。
- 管理分阶段授权。
- 组合质量、预览、人工验收和复审证据。
- 生成中文 PR 元数据和最终交付报告。

边界：

- 设计内容由设计 skill 负责。
- 产品代码由实现 skill 负责。
- 质量命令由 `quality-gate` 负责。
- 运行环境由 `deploy-website` 负责。
- 审查结论由 `requesting-code-review` 负责。
- Git 集成由 `finishing-a-development-branch` 负责。

#### quality-gate

职责：

- 根据变更文件识别 frontend、backend、docs 或 mixed 范围。
- 从项目配置读取确定性命令。
- 执行专项测试、Lint、类型检查、构建和差异检查。
- 在 repair 模式下修复授权范围内的格式和 Lint 问题。
- 输出结构化检查结果、失败证据和恢复建议。

边界：

- 质量门禁保持有限时长命令。
- Web 服务启动由预览 skill 管理。
- Git commit 和远程操作由交付编排器协调授权。

### 复用现有 skill

| Skill | 在交付流程中的职责 |
|---|---|
| `feature-design` | 标准功能的正式需求和技术设计 |
| `implementation-planner` | 复杂功能的可执行 tasklist |
| `feature-implementer` | 按批准计划实施代码和测试 |
| `security-review` | 安全风险标签命中时执行防御性复核 |
| `deploy-website` | 启动服务、返回 terminal ID 和预览 URL |
| `requesting-code-review` | 对工作树或 Git range 进行只读复审 |
| `finishing-a-development-branch` | 经授权后完成 push 和 PR |
| `skill-creator` | 创建、验证和打包两个新 skill |

## 状态模型

首版从 GitHub Issue、Git 分支、工作树、计划文档、验证证据和 PR 动态推导状态，减少重复持久化。

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

### 状态进入条件

| 状态 | 进入条件 |
|---|---|
| `issue-ready` | Issue 已存在，或新 Issue 内容经用户批准并创建 |
| `workspace-ready` | 最新 main 已同步，独立分支和 worktree 已创建 |
| `design-approved` | 简短修复方案或正式设计已获批准 |
| `implemented` | 需求范围内代码和回归测试完成 |
| `verified` | `quality-gate` 必须项全部通过 |
| `preview-accepted` | 需要运行验收的任务已由用户确认通过 |
| `reviewed` | 独立复审无 Critical 和 Important 问题 |
| `ready-for-authorization` | 实现、质量门禁、验收和复审已完成，等待用户授权 Git 操作 |
| `ready-to-integrate` | 用户明确授权 Git 提交和远程操作 |
| `pr-opened` | PR 已创建且 Issue 关联、base/head 和状态已核对 |

## 任务分流

### 快速修复路径

适用条件：Issue 已包含复现、期望、代码范围和验收标准，改动集中在少量文件。

流程：

1. 对比历史 Issue、PR 和当前代码。
2. 提出简短修复方案和测试策略。
3. 用户批准后实施。
4. 进入统一质量、预览、复审和 PR 流程。

### 标准功能路径

适用条件：新增能力、多模块改动、数据模型变化或架构决策。

流程：

1. `feature-design` 生成 requirements 和 design。
2. `implementation-planner` 生成 tasklist。
3. `feature-implementer` 执行批准任务。
4. 进入统一质量、预览、复审和 PR 流程。

### 条件叠加

- 安全敏感任务叠加 `security-review`。
- Web 交互任务叠加 online 预览和人工验收。
- Go schema 或生成代码任务叠加生成一致性检查。
- 前后端混合任务执行两侧质量门禁和 API 联调。
- 文档任务执行语法、引用和差异检查。

## 授权模型

| 授权级别 | 操作 |
|---|---|
| 只读 | Issue/PR 查询、代码搜索、Git 状态、历史对比 |
| 工作区写入 | 用户要求开发后修改代码、测试和文档，启动当前项目预览 |
| 本地 Git | 创建分支、stage 和 commit；遵循用户的提交时机约定 |
| 远程写入 | 创建 Issue、push、创建或编辑 PR |
| 高风险 Git | 丢弃提交、删除分支、清理 worktree，需要单独确认 |

第一版采用 `staged-approval`：自动推进只读检查、实现、质量门禁和预览准备；创建 Issue、本地提交和远程写入在对应阶段获取明确授权。

## 项目配置

新增版本化 `.monkeycode/workflow.yaml`，保存团队可共享的确定性配置。个人 UID 和个人偏好继续保存在本地 MEMORY。

```yaml
schema_version: 1
base_branch: main
language: zh-CN

pull_request:
  link_keyword: Fixes
  require_manual_acceptance_for_ui: true

frontend:
  root: frontend
  package_manager: pnpm
  targeted_test_ts: tsx --test
  targeted_test_mjs: node --test
  lint: pnpm lint
  build_online: pnpm run build:online

preview:
  mode: online
  target: https://monkeycode-ai.com
  api_prefix: /api
  allowed_dependency_roots:
    - frontend/node_modules

backend:
  root: backend
  targeted_test: go test
  build: go build ./...
```

配置加载失败时，`quality-gate` 报告缺失字段和建议值。编排器在信息足够时继续执行只读状态检查，并在进入质量门禁前要求补齐配置。

## Quality Gate 设计

### 门禁矩阵

| 变更类型 | 必须项 |
|---|---|
| 前端逻辑 | 专项测试、变更文件 ESLint、online build、`git diff --check` |
| 前端交互 | 前端逻辑门禁、online 预览、对应交互验收 |
| Go 后端 | 定向测试、相关包测试、`go build ./...`、适用的生成一致性检查 |
| 前后端混合 | 前端和后端门禁、API 联调预览 |
| 文档和配置 | 格式或语法检查、引用检查、`git diff --check` |
| 安全敏感 | 基础门禁、防御性安全复核 |

### 输出契约

```yaml
status: passed
scope: frontend
checks:
  targeted_test: passed
  lint_changed_files: passed
  typecheck_build: passed
  diff_check: passed
evidence:
  preview_page: 200
  preview_api: 200
blockers: []
```

每个检查项记录名称、命令、工作目录、退出码、耗时和简短结果。输出隐藏凭据和敏感环境值。

## Issue Delivery 输入输出契约

### 输入

```yaml
request_or_issue: 用户需求或 GitHub Issue URL/编号
automation_policy: staged-approval
delivery_language: zh-CN
workspace: 当前 MonkeyCode 仓库
```

### 输出

```yaml
issue_url: https://github.com/chaitin/MonkeyCode/issues/000
branch: YYMMDD-fix-topic
worktree: /tmp/opencode/MonkeyCode-topic
change_type: frontend-interaction
quality_gate: passed
preview_url: https://port-domain.monkeycode-ai.online
manual_acceptance: passed
review_verdict: ready
pr_url: https://github.com/chaitin/MonkeyCode/pull/000
resolved_problems:
  - 问题描述
```

## Skill 目录设计

```text
monkeycode-issue-delivery/
├── SKILL.md
├── references/
│   ├── state-machine.md
│   ├── issue-template.md
│   └── pr-report-template.md
└── scripts/
    └── inspect_delivery_state.sh

quality-gate/
├── SKILL.md
├── references/
│   └── result-schema.md
└── scripts/
    ├── detect_scope.sh
    └── run_gate.sh
```

`SKILL.md` 保持核心流程和资源路由，详细状态、模板和结果 schema 放入一级 references。确定性探测和门禁执行由脚本完成。

## 失败恢复

### 测试或构建失败

状态停留在 `implemented`。`quality-gate` 返回失败命令、退出码、关键错误和建议恢复入口。修复后重新执行失败项及其后续依赖项。

### 预览环境失败

分别验证页面、API、字体和静态资源。环境配置修复保持在预览层，产品代码分支只接收真实产品修复。

### 主分支前进

重新 fetch 后计算 merge-base，执行冲突检查和历史 PR 兼容性复核。兼容时同步分支并重跑受影响门禁。

### 上游推送权限不足

检查已有 fork remote。存在可写 fork 时推送到 fork，并创建以用户 fork 为 head、上游 main 为 base 的跨仓 PR。

### 用户验收发现问题

状态回到 `implemented`，保留预览 terminal 和验收上下文。修复后重新运行质量门禁和受影响验收项。

### 代码复审发现问题

Critical 和 Important 问题进入修复闭环。修复完成后重跑相应质量门禁，并对更新后的完整 Git range 复审。

## PR 和交付报告模板

### 中文 PR 必备内容

- 变更说明。
- 解决的问题。
- 历史兼容性。
- 自动验证命令与结果。
- 人工验收结果。
- 测试环境。
- `Fixes #<issue>` 关联。

### 最终交付报告必备内容

- Issue 地址。
- PR 地址、base/head 和 mergeability。
- 测试环境及页面、API、关键资源状态。
- 解决的问题。
- 历史 PR 兼容性结论。
- 测试、Lint、构建和复审结论。
- 用户人工验收结论。
- fork 推送等权限路径说明。

## 验收用例

1. 已有前端交互 Issue：完成独立 worktree、修复、门禁、预览、验收、复审和中文 PR。
2. 对话新需求：查重后经授权创建 Issue，再进入标准交付流程。
3. 上游只读权限：使用已有 fork 创建跨仓 PR。
4. 字体或 API 预览失败：识别环境层问题，恢复后验证页面、API 和字体资源。
5. 历史 PR 存在相邻实现：提取模式并验证交互和关闭语义兼容。
6. Go 后端 Issue：运行定向测试、相关包测试、构建和生成一致性检查。
7. 远程操作等待授权：状态停在 `ready-for-authorization` 并列出待授权动作。
8. 任一质量门禁失败：阻止进入 PR 阶段并保留恢复证据。

## Skill 验证策略

1. 使用 `skill-creator` 初始化两个 skill。
2. 验证 YAML frontmatter、命名、目录和引用。
3. 为脚本准备临时 Git 仓库 fixture，覆盖 frontend、backend、docs 和 mixed 范围。
4. 验证所有脚本只输出脱敏状态信息。
5. 使用一个已完成的前端修复案例回放完整状态推导。
6. 使用一个只读仓库案例验证零写入状态检查。
7. 打包 skill 并运行结构校验。

## 分阶段落地

### 第一阶段

- 创建 `.monkeycode/workflow.yaml`。
- 创建 `quality-gate` skill 和探测脚本。
- 创建 `monkeycode-issue-delivery` skill 和模板。
- 使用前端 Issue 修复案例完成试运行。

### 第二阶段

- 增加统一前端 `test` 和 `verify` 脚本。
- 将质量门禁接入 PR CI。
- 修复 Go 生成代码检查目录。
- 增加 Go 后端案例。

### 第三阶段

- 明确 `.monkeycode/specs` 与 `docs/superpowers` 的主次关系。
- 统一 tasklist 完成状态和 requirement coverage。
- 将编排器扩展为配置驱动的完整生命周期路由器。

## 完成标准

- 两个新 skill 的职责边界清晰，无重复实现现有设计、预览、审查和 Git 收尾能力。
- 同类 Issue 的重复人工操作得到显著减少。
- 每次交付生成一致的中文 PR 和最终汇报。
- Issue、commit、push 和 PR 操作遵循分阶段授权。
- 质量门禁输出可供编排器、人工和后续 CI 共同消费。
- 两个 skill 通过结构验证和代表性案例试运行。
