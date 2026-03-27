# make-latex-model 辅助脚本说明

本目录现在定位为“辅助工具箱”，不是当前 ChineseResearchLaTeX 的权威工作流。

## 先说结论

- 真正的构建与验收，应优先走各产品线官方脚本
- 本目录脚本更适合做 PDF 参数提取、标题比对、像素差异分析
- 其中不少入口带有明显的旧版 NSFC 假设，使用前要先判断是否匹配当前项目结构

## 官方构建入口

```bash
python packages/bensz-nsfc/scripts/nsfc_project_tool.py build --project-dir <project>
python packages/bensz-paper/scripts/paper_project_tool.py build --project-dir <project>
python packages/bensz-thesis/scripts/thesis_project_tool.py build --project-dir <project>
python packages/bensz-cv/scripts/cv_project_tool.py build --project-dir <project> --variant all
```

## 推荐保留使用的脚本

### `check_state.py`

快速看项目是否有 baseline、是否已有 `.make_latex_model/` 工作区，适合作为辅助预检查。

```bash
python3 skills/make-latex-model/scripts/check_state.py projects/NSFC_Young
```

注意：它更偏向旧版 NSFC 目录假设，对 `paper / thesis / cv` 的判断仅供参考。

### `analyze_pdf.py`

从 PDF baseline 提取页面尺寸、字体、颜色、边距等参数，适合作为通用辅助分析。

```bash
python3 skills/make-latex-model/scripts/analyze_pdf.py <baseline.pdf> --project projects/NSFC_Young
```

### `compare_headings.py`

对比 PDF / Word 基线与 LaTeX 标题文字、格式差异。

```bash
python3 skills/make-latex-model/scripts/compare_headings.py <baseline.pdf> <main.tex> --report heading_report.html
```

### `compare_pdf_pixels.py`

做像素级 PDF 比对。

```bash
python3 skills/make-latex-model/scripts/compare_pdf_pixels.py <baseline.pdf> <rendered.pdf>
```

### `optimize_heading_linebreaks.py`

根据 PDF 基线的标题断行位置，辅助优化标题换行。

```bash
python3 skills/make-latex-model/scripts/optimize_heading_linebreaks.py <main.tex> --pdf-baseline <baseline.pdf>
```

## 带明显 legacy 假设的入口

以下能力仍然保留，但主要服务旧版 NSFC 流程：

- `validate.sh` / `validate.bat`
- `benchmark.sh` / `benchmark.bat`
- `templates/nsfc/*.yaml`
- `core/config_loader.py`
- 一些围绕 `main.tex + extraTex/@config.tex + Word 模板目录` 展开的自动化逻辑

如果你的目标是：

- `projects/paper-*`
- `projects/thesis-*`
- `projects/cv-*`
- 或者一个已经明显脱离旧版 NSFC 目录模型的项目

那么这些 legacy 入口通常不应作为主流程。

## 推荐使用顺序

1. 先用官方构建脚本确认真实入口
2. 再视需要用这里的脚本补充分析
3. 不要让这里的脚本覆盖掉当前仓库的真实分层判断
