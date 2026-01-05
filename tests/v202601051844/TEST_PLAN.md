# 测试计划：make_latex_model（v202601051844）

## 目标

在**不干预正式项目**（`projects/NSFC_Young`）的前提下，在隔离副本中对 `extraTex/@config.tex` 进行第一轮样式参数迭代，并建立可重复的“Word 基准 → LaTeX 输出 → 像素对比 → 记录”测试链路。

## 范围与约束

- 测试对象：`tests/v202601051844/NSFC_Young/extraTex/@config.tex`
- 不修改：`projects/NSFC_Young/*`
- 不改动示例正文：不编辑 `tests/v202601051844/NSFC_Young/main.tex`
- 允许新增：测试驱动文件（用于对齐验证）`tests/v202601051844/NSFC_Young/compare_2026.tex`

## 基准来源（Word 2026）

- Word 模板：`tests/v202601051844/NSFC_Young/template/2026年最新word模板-青年科学基金项目（C类）-正文.doc`
- 基准生成方式（本机无 Office/LibreOffice）：
  - QuickLook 预览 HTML：`qlmanage -p -o tests/v202601051844/artifacts/word_preview <doc>`
  - QuickLook 缩略图（PNG）：`qlmanage -t -s 2000 -o tests/v202601051844/artifacts/word_thumb <doc>`

## LaTeX 输出

### 1) 回归编译（保持示例不变）

在测试副本中按标准序列编译 `main.tex`，确保副本可正常构建：

- `xelatex -> bibtex -> xelatex -> xelatex`
- 产物：`tests/v202601051844/NSFC_Young/main.pdf`
- 日志：`tests/v202601051844/xelatex*.log`、`tests/v202601051844/bibtex.log`

### 2) 对齐验证编译（对照 Word 模板结构）

编译 `compare_2026.tex`（内容参照 QuickLook 预览的 2026 模板），用于更聚焦地观察“样式差异”而非“正文差异”：

- 产物：`tests/v202601051844/NSFC_Young/compare_2026.pdf`
- 日志：`tests/v202601051844/compare2026_*.log`

## 像素对比方法（第一轮）

由于缺少 Word“打印 PDF”基准，第一轮使用 QuickLook 缩略图作为近似基准。

- Word 基准图：`tests/v202601051844/artifacts/baseline/word.png`
- LaTeX 缩略图：`tests/v202601051844/artifacts/**/latex.png`
- 对比脚本：`tests/v202601051844/scripts/compare_images.py:1`
- 指标：
  - `mean_abs_diff`：灰度平均绝对差
  - `changed_ratio`：像素差超过阈值（默认 16/255）的比例
  - 可选：`--crop left,top,right,bottom` 聚焦页面上半部（标题与提纲区域）

## 迭代策略（第一轮）

- 仅允许修改：`tests/v202601051844/NSFC_Young/extraTex/@config.tex`
- 优先顺序：
  1. 页面边距/版心（`geometry`）
  2. 标题层级格式（`titlesec`：字号/加粗/缩进/段前段后）
  3. 行距/字号系统（`\fontsize{size}{baselineskip}`）
  4. 列表/编号缩进（`enumitem`）

## 通过标准（当前轮次）

- 编译成功（无 error）
- 生成并留存：Word 基准（HTML+PNG）、LaTeX PDF、PNG、diff PNG、diff JSON
- 输出测试报告，明确：
  - 本轮对齐的限制（无 Word 打印 PDF）
  - 指标变化与下一步需要的输入（推荐由用户提供 Word 打印 PDF）

