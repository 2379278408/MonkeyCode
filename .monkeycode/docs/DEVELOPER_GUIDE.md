# MonkeyCode 开发、测试与构建指南

## 项目目的

本指南用于把当前环境中已经实战验证的 MonkeyCode 工作流迁移到新环境。流程覆盖环境恢复、Issue 隔离开发、测试和构建、SaaS online 预览、人工验收、代码复审、授权、fork 推送和中文 PR。

## 新环境恢复

### 方案一：直接克隆工作流分支

```bash
git clone https://github.com/2379278408/MonkeyCode.git
cd MonkeyCode
git checkout 260722-design-monkeycode-issue-delivery-workflow
git remote add upstream https://github.com/chaitin/MonkeyCode.git
git fetch upstream main
```

仓库已经存在 `upstream` 时，保留现有 remote 配置。当前分支包含工作流配置、两个 skill、测试、设计、计划和本 Wiki。

### 方案二：已有上游仓库时获取工作流分支

```bash
git remote add workflow-fork https://github.com/2379278408/MonkeyCode.git
git fetch workflow-fork 260722-design-monkeycode-issue-delivery-workflow
git switch -c 260722-design-monkeycode-issue-delivery-workflow \
  --track workflow-fork/260722-design-monkeycode-issue-delivery-workflow
```

### 确认工作流完整性

```bash
git status --short --branch
python3 .monkeycode/skills/quality-gate/scripts/run_gate.py --help
python3 .monkeycode/skills/monkeycode-issue-delivery/scripts/inspect_delivery_state.py --help
```

## 工具链

| 工具 | 要求 | 用途 |
|---|---|---|
| Git | 支持 worktree 和 merge-base | Issue 隔离、范围检测和状态推导 |
| Python | 3.11+ | 工作流脚本与单元测试 |
| Node.js | 20.19+ | Vite 7 前端工具链 |
| pnpm | 9.x | frontend 和 desktop |
| `tsx` | 4.x | 前端 TypeScript 定向测试 |
| Go | 1.25.x | 后端测试与构建 |
| C 编译工具链 | 可用 CGO | SQLite 后端测试 |
| GitHub CLI | 当前稳定版 | Issue、PR 和状态读取 |
| Docker Buildx | 当前稳定版 | 前后端容器镜像 |

本环境使用全局 `tsx`。仓库前端尚未直接声明该依赖，新环境需要确保 `tsx --version` 可执行。

## 依赖恢复

### Web 前端

```bash
cd frontend
pnpm install --frozen-lockfile
```

### Go 后端

```bash
cd backend
go mod download
```

后端 private module 出现 HTTP 40x 时，从 Git credential helper 获取目标 host 的凭据并写入权限为 `600` 的 `/root/.netrc`，随后重试原命令。凭据值只进入本机凭据文件。

### Electron 桌面端

```bash
cd desktop
pnpm install --frozen-lockfile
```

### Expo 移动端

```bash
cd mobile
npm ci
```

## Issue 到 PR 标准工作流

### 1. 读取项目约定

读取以下入口：

- `.monkeycode/workflow.yaml`
- `.monkeycode/MEMORY.md`
- `.monkeycode/skills/monkeycode-issue-delivery/SKILL.md`
- `.monkeycode/skills/quality-gate/SKILL.md`

### 2. 准备 Issue

1. 输入已有 GitHub Issue URL，或把对话需求整理为 Issue 草稿。
2. 查找重复 Issue、历史 PR 和相关代码。
3. 创建 Issue 前展示标题和正文，并取得明确授权。

### 3. 创建隔离工作区

从最新上游 `main` 创建独立分支和 worktree：

```bash
git fetch upstream main
git worktree add -b <branch-name> /tmp/opencode/<worktree-name> upstream/main
```

分支名使用日期、类型和任务摘要。每个 Issue 保持独立分支、worktree、提交和 PR。

### 4. 设计和实施

- 小范围 Bug 使用简短修复方案和定向测试策略。
- 多步骤功能使用 `feature-design`、`implementation-planner` 和 `feature-implementer`。
- 认证、用户输入、密钥、API、支付或敏感数据使用 `security-review`。
- 优先编写可复现失败的回归测试，再实施最小正确改动。

### 5. 运行质量门禁

先执行 dry-run，确认命令参数和工作目录：

```bash
python3 .monkeycode/skills/quality-gate/scripts/run_gate.py \
  --repo . \
  --scope frontend \
  --path frontend/src/example.tsx \
  --target-test frontend/test/example.test.ts \
  --dry-run
```

确认计划后移除 `--dry-run`。保留完整 JSON 输出作为质量证据。

### 6. Web 预览和人工验收

UI 或交互改动使用 `deploy-website` 启动 online 前端。Vite 配置已经包含：

- 监听 `0.0.0.0:11180`
- `/api` 转发到 mode 中的 `TARGET`
- WebSocket 代理
- `.monkeycode-ai.online` allowed host

预览阶段检查：

1. 页面可加载。
2. 关键静态资源返回成功。
3. `/api` 请求和 WebSocket 符合预期。
4. 浏览器控制台中的目标 warning 或 error 已消除。
5. 用户在登录态完成关键交互并明确验收通过。

长时间服务通过后台终端管理，并保存 terminal ID 和预览 URL。环境收尾时按 terminal ID 停止服务。

### 7. 完整范围复审

使用 `requesting-code-review` 审查完整 base-to-head Git range。Critical 和 Important findings 回到实现阶段，修复后重新运行受影响门禁。

### 8. Git 操作授权和 fork 路径

在每项 Git 操作前展示：

- 精确文件列表
- commit message
- remote 和 refspec
- PR base 和 head
- PR 标题和正文

Issue 创建、commit、push、PR 创建和 PR 编辑均支持逐项授权，也可由用户对清晰列出的批次一次授权。上游 push 返回 403 时，使用已有可写 fork 推送同一授权提交，再从 fork 分支向 `chaitin/MonkeyCode:main` 创建 PR。

### 9. 最终交付报告

报告包含：

- Issue URL
- PR URL
- 分支和 commit SHA
- 解决内容
- 测试、Lint 和构建结果
- 预览与人工验收结论
- 代码复审结论
- PR mergeability 和 checks

## 测试与构建矩阵

### 工作流自身

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover \
  -s .monkeycode/skills/quality-gate/tests \
  -p 'test_*.py' \
  -v

PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover \
  -s .monkeycode/skills/monkeycode-issue-delivery/tests \
  -p 'test_*.py' \
  -v
```

### Web 前端

工作目录：`frontend`

```bash
tsx --test test/example.test.ts
node --test test/example.test.mjs
pnpm exec eslint src/example.tsx test/example.test.ts
pnpm run build:online
pnpm run build:offline
```

标准前端门禁为：定向测试、变更文件 ESLint、`build:online`、`git diff --check`。Vite mode、代理或 edition 配置变更同时执行 online 和 offline build。

### Go 后端

工作目录：`backend`

```bash
go test ./pkg/example -run TestExample
go test ./...
go build ./...
```

Ent schema 变更追加：

```bash
make generate
make check-generate
```

Swagger 或 API 契约变更追加：

```bash
make swag
cd ../frontend
SWAGGER=../backend/docs/swagger.json pnpm run api
pnpm run build:online
```

### Electron 桌面端

工作目录：`desktop`

```bash
pnpm run electron:dev
pnpm run electron:pack:with-dist
```

`electron:pack:with-dist` 会先构建 online Web 资源并同步到桌面包。macOS 与 Windows 安装包应在对应平台 runner 验证。

### Expo 移动端

工作目录：`mobile`

```bash
npm test
npm run lint
npx expo prebuild -p android --no-install
npx expo prebuild -p ios --no-install
npx expo export --platform android --platform ios
```

原生模块、SDK、权限和 config plugin 变化需要重新生成原生工程并构建安装包。OTA 适用于 JavaScript 和 assets 更新。

### 改动类型速查

| 改动类型 | 最小验证 |
|---|---|
| Markdown 文档 | `git diff --check` |
| 工作流配置 | 工作流 unittest、相关 dry-run、diff check |
| quality-gate 脚本 | quality-gate 全测、frontend/backend/docs dry-run |
| issue-delivery 脚本 | delivery 全测、状态链 smoke test、脱敏测试 |
| 前端逻辑 | 定向测试、变更文件 ESLint、online build、diff check |
| UI 交互 | 前端门禁、online 预览、API/资源验证、人工验收 |
| 后端逻辑 | 定向测试、`go test ./...`、`go build ./...`、diff check |
| 前后端混合 | 两侧定向测试、前端 lint/build、后端全测/build、集成预览 |
| Desktop | frontend build、sync-web、目标平台 package |
| Mobile | Jest、lint；原生变化追加 prebuild 和 release build |

## 常用开发命令

### 前端开发服务器

```bash
cd frontend
pnpm run dev:online
pnpm run dev:offline
```

默认 `pnpm run dev` 缺少明确 edition 语义，日常开发使用 `dev:online` 或 `dev:offline`。

### 后端服务

```bash
cd backend
go run ./cmd/server/main.go
```

后端从 `backend/config/server` 读取配置，并在监听 HTTP 端口前运行 migration。开发环境至少准备 PostgreSQL、Redis 和有效的 `MCAI_DATABASE_MASTER`。

### 容器构建

前端先生成 `frontend/dist`，再把产物放入 `frontend/docker/dist` 作为 Docker context。后端在 `backend` 中使用：

```bash
make image
make ingress
```

完整 `backend/docker-compose.yml` 依赖 PostgreSQL、Redis、ClickHouse、RustFS、ingress、taskflow、frontend、backend 和 preview 的外部配置。

## 已验证实例

Issue #915 和 PR #916 已验证以下路径：

1. 从最新 `main` 创建独立 worktree。
2. 为任务预览弹窗补充无障碍描述和双语文案。
3. 运行 TypeScript 定向测试、变更文件 ESLint、`pnpm run build:online` 和 `git diff --check`。
4. 启动 online SaaS 预览并由用户人工验收。
5. 完成独立代码复审。
6. 上游 push 返回 403 后推送到 `2379278408/MonkeyCode` fork。
7. 创建中文 PR 并使用 `Fixes #915` 关联 Issue。

该实例还确认：GitHub PR 图片要求可识别的图片 Content-Type。OSS 返回 `application/octet-stream` 时 GitHub 图片代理会失败，持久验收图可提交到仓库并使用固定 commit SHA 的 raw URL。

## 当前限制与恢复策略

1. `desktop/**` 和 `mobile/**` 尚未纳入自动 scope 分类；这两类改动按本指南手动追加测试矩阵。
2. `tsx` 当前依赖环境全局安装；运行前检查命令可用性。
3. Git 范围检测默认依赖 `origin/main`；浅克隆或 fork 环境先 fetch 对应 base ref。
4. 前端 build 只编译 `src`；定向测试仍需独立执行。
5. GitHub Actions 当前覆盖 `main` 的 online 前端构建；PR 质量证据来自本地门禁。
6. Go 全量测试使用 SQLite CGO；环境需要 C 编译工具链。
7. 后端启动会自动 migration；数据库配置错误会阻止服务启动。
8. frontend Docker 只托管静态资源；完整部署的 API 转发由 ingress 处理。

## 环境关闭前检查

```bash
git status --short --branch
git log --oneline -10
git remote -v
```

确认所有计划保留的改动已经 commit 并推送到 fork。记录分支名、最终 commit SHA、测试结果、预览 URL、后台 terminal ID、Issue 和 PR URL。新环境以 fork 分支为恢复源，以最新上游 `main` 为后续 Issue worktree 基线。
