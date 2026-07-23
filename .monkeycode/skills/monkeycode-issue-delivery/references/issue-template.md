# 中文 Issue 模板

Search open and closed Issues plus historical PRs before drafting. Show the complete draft and request explicit authorization before `gh issue create`.

```markdown
## 问题描述

<描述用户场景和问题背景>

## 复现步骤

1. <步骤>

## 实际表现

<当前行为>

## 期望表现

<目标行为>

## 代码定位

- `<相关路径或模块>`

## 历史参照

- <相关 Issue、PR 或提交；没有时填写“未发现直接参照”>

## 验收标准

- [ ] <可验证标准>

## 我的 UID

<从本地 `.monkeycode/MEMORY.md` 获取；缺失时向用户询问>
```

Keep private local values in the rendered Issue only when the user has approved that content. Never copy credentials or environment secrets into the draft.
