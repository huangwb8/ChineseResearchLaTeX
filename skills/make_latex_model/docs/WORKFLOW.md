# make_latex_model 工作流（详细版）

本文件承载 `skills/make_latex_model/SKILL.md` 中移出的“可重复执行”的细节流程。`SKILL.md` 只保留：边界、总流程、验收标准与入口链接。

## 0) 预检查（必须先做）

```bash
python3 skills/make_latex_model/scripts/check_state.py projects/{project}
```

根据输出决定下一步：
- `has_baseline=false`：先准备/生成 Word PDF 基准（见 `skills/make_latex_model/docs/BASELINE_GUIDE.md`）
- `compilation_status=failed`：先修复项目编译错误（不要进入样式优化）

## 1) 准备 Word PDF 基准

优先使用 Word/LibreOffice **导出/打印** 的 PDF，避免 QuickLook 造成断行/行距偏差。

- 指南：`skills/make_latex_model/docs/BASELINE_GUIDE.md`
- 自动生成（如项目模板目录中包含 Word 模板）：`python3 skills/make_latex_model/scripts/generate_baseline.py --project {project}`

基准默认放在：
- `skills/make_latex_model/workspace/{project}/baseline/word.pdf`

## 2) 提取 Word PDF 的样式参数（推荐）

```bash
python3 skills/make_latex_model/scripts/analyze_pdf.py \
  skills/make_latex_model/workspace/{project}/baseline/word.pdf \
  --project {project}
```

该分析结果用于：
- 对比行距/字号/边距/颜色等“确定性参数”
- 驱动后续“改哪些参数、改到什么值”的决策

## 3) 对齐标题文字（强约束）

只允许修改 `main.tex` 的标题文本（`\section{}`/`\subsection{}`…），禁止触碰 `\input{}` 引入的正文内容文件。

```bash
python3 skills/make_latex_model/scripts/compare_headings.py \
  projects/{project}/template/{word_docx} \
  projects/{project}/main.tex \
  --report heading_report.html
```

如需检查标题“加粗位置”差异：

```bash
python3 skills/make_latex_model/scripts/compare_headings.py \
  projects/{project}/template/{word_docx} \
  projects/{project}/main.tex \
  --check-format \
  --report heading_format_report.html
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
  --max-iterations 10 \
  --report
```

启用 AI 闭环（最小可用版）：

```bash
python3 skills/make_latex_model/scripts/enhanced_optimize.py \
  --project projects/{project} \
  --max-iterations 10 \
  --ai --ai-mode heuristic
```

说明：
- `heuristic`：纯启发式（离线可用）
- `manual_file`：生成 `workspace/{project}/iterations/iteration_XXX/ai_request.json`，写入 `ai_response.json` 后继续

更多脚本参数与说明见：
- `skills/make_latex_model/scripts/README.md`

