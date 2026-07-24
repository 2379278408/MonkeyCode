# MonkeyCode 开发工作流文档

本文档集用于在新环境中恢复 MonkeyCode 仓库，并按统一流程完成开发、测试、构建、预览、验收和 Pull Request 交付。

## 快速入口

| 文档 | 用途 |
|---|---|
| [开发者指南](./DEVELOPER_GUIDE.md) | 环境恢复、开发命令、测试矩阵、构建、预览和交付流程 |
| [工作流架构](./ARCHITECTURE.md) | Issue 交付编排器、质量门禁及下游 skill 的职责边界 |
| [工作流接口](./INTERFACES.md) | 配置文件、Python CLI、状态与质量报告契约 |

## 推荐阅读顺序

1. 按[开发者指南](./DEVELOPER_GUIDE.md#新环境恢复)恢复分支和工具链。
2. 阅读[工作流架构](./ARCHITECTURE.md#端到端交付链)理解交付阶段。
3. 使用[工作流接口](./INTERFACES.md)调用质量门禁和状态检查器。
4. 在 Agent 中加载 `monkeycode-issue-delivery`，按 Issue 独立推进开发。

## 当前可恢复版本

- 仓库：`2379278408/MonkeyCode`
- 分支：`260722-design-monkeycode-issue-delivery-workflow`
- 工作流配置：`.monkeycode/workflow.yaml`
- 交付编排 skill：`.monkeycode/skills/monkeycode-issue-delivery/`
- 质量门禁 skill：`.monkeycode/skills/quality-gate/`
