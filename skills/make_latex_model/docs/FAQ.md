# make_latex_model 常见问题（FAQ）

## Q1：如何获取 Word PDF 基准？

优先阅读：`skills/make_latex_model/docs/BASELINE_GUIDE.md`。

核心原则：
- 用 Word/LibreOffice 导出的 PDF 做基准
- 避免 QuickLook（断行/行距算法不同，像素对比会失真）

## Q2：修改后老用户模板还能用吗？

能。该技能的修改边界是：
- 只改 `projects/{project}/extraTex/@config.tex`
- 允许改 `projects/{project}/main.tex` 的标题文本
- 不改 `projects/{project}/extraTex/*.tex` 的正文内容文件

## Q3：如何判断“优化是否过度”？

可接受：
- 参数微调（字号/行距/边距/颜色/缩进）
- 为兼容性增量新增命令（不替换/不破坏旧命令）

需谨慎：
- 删除命令、重构核心宏包结构、改变条件分支逻辑

## Q4：Word 模板章节结构变化了怎么办？

本技能只负责“样式与标题对齐”，不负责替你重写正文结构。

推荐做法：
- 在 `main.tex` 同步标题文字（允许）
- 新增章节内容由用户自行在 `extraTex/*.tex` 中维护（默认不动）

