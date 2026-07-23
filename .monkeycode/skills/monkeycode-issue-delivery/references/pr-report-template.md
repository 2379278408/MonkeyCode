# 中文 PR 与交付汇报模板

## PR 正文

```markdown
## 变更摘要

- <用户可感知变更>

## 解决的问题

- <根因与修复结果>

## 历史兼容性

- <相关历史 PR、兼容行为或迁移影响>

## 自动化验证

- `<命令>`：通过

## 人工验收

- <验收场景与结果；无需验收时说明原因>

## 测试环境

- <SaaS 预览 URL、页面/API/关键资源状态；非 Web 任务填写“不适用”>

Fixes #<issue-number>
```

## 最终交付报告

```markdown
- Issue：<URL>
- PR：<URL>
- PR 状态：<open/mergeable/checks>
- 分支与提交：<base <- head，SHA>
- 解决的问题：<结果>
- 自动化验证：<命令与结果>
- 独立复审：<Critical/Important 数量与结论>
- 测试环境：<URL 和页面/API/资源健康状态>
- 用户验收：<passed/not-required>
- Fork 路径：<使用时填写 remote、branch、head；其余填写“不适用”>
- 剩余风险：<明确风险或“无已知阻断项”>
```

Re-read PR metadata after creation. Report actual base/head, mergeability, checks, and Issue linkage from GitHub rather than inferred values.
