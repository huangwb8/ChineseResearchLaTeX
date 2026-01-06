# NSFC_General 与 2026 Word 模板对齐说明

本项目已使用 `skills/make_latex_model` 对齐到 `projects/NSFC_General/template/2026年最新word模板-1.面上项目-正文.pdf`。

## 基准文件（baseline）

- 基准 PDF：`projects/NSFC_General/artifacts/baseline/word.pdf`
- 基准分析：`projects/NSFC_General/artifacts/baseline/word_analysis.json`

当 Word 模板更新时：
1. 用新模板导出 PDF 覆盖 `artifacts/baseline/word.pdf`
2. 运行 `python3 skills/make_latex_model/scripts/analyze_pdf.py projects/NSFC_General/artifacts/baseline/word.pdf`
3. 重新编译 `projects/NSFC_General/main.tex` 并做像素对比

## 占位空白（重要）

Word 模板在提纲标题之间包含空白段落。为了让“无正文内容”时也能对齐行距与段落高度，模板定义了：

- `\\NSFCBlankPara`：生成一个“空白段落高度”（1 行行距减去段后）。

各 `extraTex/*.tex` 默认包含一行 `\\NSFCBlankPara` 作为占位；开始写正文后可以删除该行，避免多余空白。

## 验证命令

- 编译（建议两遍）：`xelatex -interaction=nonstopmode -halt-on-error main.tex && xelatex -interaction=nonstopmode -halt-on-error main.tex`
- 像素对比：`python3 skills/make_latex_model/scripts/compare_pdf_pixels.py projects/NSFC_General/artifacts/baseline/word.pdf projects/NSFC_General/main.pdf --dpi 150 --tolerance 2 --report projects/NSFC_General/artifacts/compare/diff.html`

