# make_latex_model 工作流（详细版）

本文件承载 `skills/make_latex_model/SKILL.md` 中移出的“可重复执行”的细节流程。`SKILL.md` 只保留：边界、总流程、验收标准与入口链接。

## 0) 预检查（必须先做）

```bash
python3 skills/make_latex_model/scripts/check_state.py projects/{project}
```

根据输出决定下一步：
- `has_baseline=false`：先准备 PDF 基准（推荐：基金委 PDF / Word 导出 PDF）
- `compilation_status=failed`：先修复项目编译错误（不要进入样式优化）

## 1) 准备 PDF 基准（推荐）

推荐直接使用基金委提供的 PDF 模板；如果只有 Word 模板，也建议用 Word/LibreOffice **导出/打印** 得到 PDF，避免 QuickLook 造成断行/行距偏差。

将基准 PDF 放到（推荐路径）：
- `projects/{project}/template/baseline.pdf`

技能会自动将该 PDF 复制到工作空间：
- `projects/{project}/.make_latex_model/baselines/baseline.pdf`

兼容旧流程（不推荐，但仍可用）：
- 指南：`skills/make_latex_model/docs/BASELINE_GUIDE.md`
- 自动生成（如项目模板目录中包含 Word 模板）：`python3 skills/make_latex_model/scripts/generate_baseline.py --project {project}`（产物为 `word.pdf`）

基准默认放在：
- `projects/{project}/.make_latex_model/baselines/baseline.pdf`（推荐）
- `projects/{project}/.make_latex_model/baselines/word.pdf`（legacy）

## 2) 提取 PDF 基准的样式参数（推荐）

```bash
python3 skills/make_latex_model/scripts/analyze_pdf.py \
  projects/{project}/.make_latex_model/baselines/baseline.pdf \
  --project {project}
```

该分析结果用于：
- 对比行距/字号/边距/颜色等“确定性参数”
- 驱动后续“改哪些参数、改到什么值”的决策

## 3) 对齐标题文字（强约束）

只允许修改 `main.tex` 的标题文本（`\section{}`/`\subsection{}`…），禁止触碰 `\input{}` 引入的正文内容文件。

```bash
python3 skills/make_latex_model/scripts/compare_headings.py \
  projects/{project}/template/baseline.pdf \
  projects/{project}/main.tex \
  --report heading_report.html
```

如需检查标题“加粗位置”差异：

```bash
python3 skills/make_latex_model/scripts/compare_headings.py \
  projects/{project}/template/baseline.pdf \
  projects/{project}/main.tex \
  --check-format \
  --report heading_format_report.html
```

如需根据 PDF 的标题跨行情况自动插入 `\linebreak{}`（可选）：

```bash
python3 skills/make_latex_model/scripts/optimize_heading_linebreaks.py \
  projects/{project}/main.tex \
  --pdf-baseline projects/{project}/template/baseline.pdf
```

## 4) 只改样式层：`extraTex/@config.tex`

允许的修改类型（推荐顺序）：
1. 颜色（如 MsBlue）
2. 字号体系（如 `\xiaosi`）
3. 行距/段距（如 `\baselinestretch`、`\parskip`）
4. 边距/版心（`geometry`）
5. 标题缩进/列表缩进（不重构宏包结构）

禁止：
- 删除/重命名已有命令
- 改变宏包加载顺序
- 改写 `\ifwindows` 等条件结构

## 5) 验证（推荐脚本化）

```bash
cd skills/make_latex_model
./scripts/validate.sh --project projects/{project}
```

## 6) 需要精细对齐时：迭代优化闭环

基础闭环：

```bash
python3 skills/make_latex_model/scripts/enhanced_optimize.py \
  --project projects/{project} \
  --max-iterations 30 \
  --report
```

启用 AI 闭环（最小可用版）：

```bash
python3 skills/make_latex_model/scripts/enhanced_optimize.py \
  --project projects/{project} \
  --max-iterations 30 \
  --ai --ai-mode heuristic
```

说明：
- `heuristic`：纯启发式（离线可用）
- `manual_file`：生成 `projects/{project}/.make_latex_model/iterations/iteration_XXX/ai_request.json`，写入 `ai_response.json` 后继续

更多脚本参数与说明见：
- `skills/make_latex_model/scripts/README.md`

像素对比建议使用逐段模式（更稳健）：

```bash
python3 skills/make_latex_model/scripts/compare_pdf_pixels.py \
  projects/{project}/.make_latex_model/baselines/baseline.pdf \
  projects/{project}/main.pdf \
  --mode paragraph \
  --features-out diff_features.json
```
