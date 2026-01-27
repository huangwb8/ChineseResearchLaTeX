# make_latex_model - LaTeX 模板高保真优化器

基于 PDF（推荐：基金委 PDF / Word 导出 PDF）作为“基准”，对 LaTeX 模板进行样式参数对齐与标题文字对齐，并提供验证器、HTML 报告与像素级对比辅助验收。

## 适用场景

- NSFC 等官方 Word 模板更新，需要将 `projects/*` 的 LaTeX 模板对齐到最新样式
- 需要快速定位：字号/行距/边距/颜色/标题格式/标题文字等差异来源
- 希望形成“分析 → 修改 → 验证 → 迭代”的可重复流程

## 推荐用法（优先：Prompt 调用 Skill）

在 Claude Code / OpenAI Codex CLI 里，通常**优先用自然语言 Prompt**触发 Skill（而不是手动跑脚本）。下面这条 Prompt 已验证可靠：

```
基于make_latex_model这个skill对 projects/NSFC_General 进行改造，使得它的latex系统与 `projects/NSFC_General/template/2026年最新word模板-1.面上项目-正文.pdf` 这个最新模板对齐。
```

## 备选用法（脚本/硬编码流程）

1) 状态检查（看缺什么）

```bash
python3 skills/make_latex_model/scripts/check_state.py projects/NSFC_Young
```

2) 分析 PDF 基准（提取样式参数）

```bash
python3 skills/make_latex_model/scripts/analyze_pdf.py projects/NSFC_Young/.make_latex_model/baselines/baseline.pdf
```

3) 运行验证（检查编译与关键一致性）

```bash
cd skills/make_latex_model
./scripts/validate.sh --project NSFC_Young
```

> 基准 PDF 质量与来源非常关键：优先使用基金委 PDF，或用 Word “导出/打印”得到的 PDF，避免 QuickLook 等渲染链路带来的偏差。详见 `skills/make_latex_model/docs/BASELINE_GUIDE.md`。

## 一键迭代优化（需要精细对齐时）

```bash
python3 skills/make_latex_model/scripts/enhanced_optimize.py --project NSFC_Young --max-iterations 30 --report
```

## 修改边界（底线）

- 只允许精确修改 `projects/{project}/extraTex/@config.tex`
- 允许修改 `main.tex` 中的标题文本（`\section{}` / `\subsection{}` 等），不触碰正文内容（`extraTex/*.tex`）

## 文档入口

- 总规范：`skills/make_latex_model/SKILL.md`
- 脚本说明与更多用法：`skills/make_latex_model/scripts/README.md`
- 基准制作与注意事项：`skills/make_latex_model/docs/BASELINE_GUIDE.md`

## 依赖（最低要求）

- Python `>=3.8`，建议安装：`PyMuPDF`、`python-docx`、`Pillow`、`PyYAML`
- LaTeX：`xelatex` / `pdflatex` / `bibtex`

> 变更历史记录在 `CHANGELOG.md`。
