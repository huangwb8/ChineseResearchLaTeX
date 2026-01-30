# References - 项目辅助文档

本目录存放项目的辅助性 Markdown 文档，包括规范、指南、备忘录等。

## 文档列表

### latex-writing-guide.md
LaTeX 写作指南，包含常用命令、环境、数学公式、表格等。

### nsfc-submission-checklist.md
国自然科学基金提交清单，确保申请材料的完整性。

### bibliography-best-practices.md
参考文献管理最佳实践，包括 BibTeX 使用、引用格式等。

## 参考文献间距调整（NSFC 模板）

三套 NSFC 模板（General/Local/Young）的参考文献间距参数采用“两层架构”管理：

- 基础默认值：在各项目 `extraTex/@config.tex` 中定义
- 项目级定制：在各项目 `references/reference.tex` 中用 `\\setlength{...}{...}` 覆盖（推荐做法，便于后续升级合并）

默认值：

- 标题与上文：`10pt`（`\\NSFCBibTitleAboveSkip`）
- 标题与条目：`0pt`（`\\NSFCBibTitleBelowSkip`）
- 条目间距：`0pt`（`\\NSFCBibItemSep`）
- 条目行宽：`397.16727pt`（`\\NSFCBibTextWidth`）

## 添加新文档

1. 在本目录创建 Markdown 文件
2. 在本 README.md 中添加说明
3. 确保文档使用简体中文（与项目语言一致）
