# thesis-writing-workflow

`thesis-writing-workflow` 用于把学位论文的长期写作、审阅、修改和交付过程组织成可追踪流程。它是编排型技能：负责路由、记录、验证和交付门禁，不保存真实论文内容，也不重复实现具体写作或核查能力。

## 适合什么时候用

- 开始一轮章节审阅或交付前检查。
- 需要处理一批人工审阅意见。
- 需要把候选问题转成可执行修改批次。
- 新增、删除或移动图表后，需要检查引用和编号级联。

## 快速开始

1. 复制 `templates/run-log-template.md`，建立本轮运行记录。
2. 在运行记录中填写 `<task-scope>`、`<source-files>` 和 `<acceptance-checks>`。
3. 按 `scan -> adjudicate -> apply -> verify -> deliver` 执行。
4. 将人工意见写入 `human-review-record-template.md` 的副本，并分配 `<review-id>`。
5. 将仍需确认的问题写入 `pending-decisions-template.md` 的副本。
6. 交付时填写 `final-delivery-summary-template.md`。

建议把实际运行记录放在项目内的隐藏工作目录中；公开仓库只提交这些空模板和流程说明。

## 能力路由

| 问题类型 | 处理方式 |
| --- | --- |
| 表达、衔接、章节角色 | 交给写作修订能力提出候选修改，主控裁定后再回填 |
| 引用、参考文献、证据链 | 交给引用核查能力输出结论摘要，不保存真实检索过程 |
| 文献背景、研究进展、指南 | 交给资料整理或规则沉淀能力，避免把真实材料写入公开模板 |
| 图表、编号、标签、交叉引用 | 交给格式与级联检查能力，再执行小批量回填和验证 |
| 构建、导出、版式验收 | 使用项目官方构建和检查入口，只记录命令类别与结果 |

## 示例提示

```text
请使用 thesis-writing-workflow 处理本轮学位论文修改：
- project-dir: <project-dir>
- source-files: <chapter-file>
- review-input: <review-summary>
- run-log: <run-log-file>
- verification-command: <verification-command>
要求：先扫描和裁定，再小批量回填；每批完成后记录验证结果。
```

## 记录原则

- 正式 LaTeX 源文件是唯一正文真相源。
- 运行记录只写本轮轨迹，不复制完整流程。
- 人工审阅记录只写意见摘要、状态和回流结果。
- 待裁定清单只记录问题摘要，不粘贴真实正文。
- 公开模板只使用占位符，不写真实章节、术语、图表、研究对象或个人信息。

## 验收

每轮交付前确认：

- 本轮修改范围与运行记录一致。
- 目标检索、diff 检查和构建检查已有结果。
- 图表变更已检查引用、标签和编号级联。
- 未决项已进入待裁定清单。
- 交付摘要说明了完成项、边界和下一步。
