# make-latex-model 辅助脚本说明

本目录现在定位为“辅助工具箱”，不是当前 ChineseResearchLaTeX 的权威工作流。

## 先说结论

- 真正的构建与验收，应优先走各产品线官方脚本
- 本目录脚本更适合做 PDF 参数提取、标题比对、像素差异分析
- 一部分脚本是跨产品线通用辅助工具，另一部分是 NSFC 专项参数工具，使用前先判断职责是否匹配当前任务

## 官方构建入口

```bash
python packages/bensz-nsfc/scripts/nsfc_project_tool.py build --project-dir <project>
python packages/bensz-paper/scripts/paper_project_tool.py build --project-dir <project>
python packages/bensz-thesis/scripts/thesis_project_tool.py build --project-dir <project>
python packages/bensz-cv/scripts/cv_project_tool.py build --project-dir <project> --variant all
```

## 推荐保留使用的脚本

### `plan_package_regression.py`

当你判断“这次必须改 `packages/bensz-*`”时，先用它生成受影响模板与官方回归命令。

```bash
python3 skills/make-latex-model/scripts/plan_package_regression.py packages/bensz-thesis
python3 skills/make-latex-model/scripts/plan_package_regression.py packages/bensz-fonts
```

这是当前 skill 里约束“包层改动不能伤到其它现有模板”的确定性入口。建议先跑这个脚本，再真正编辑公共包。

### `check_state.py`

快速看项目是否有 baseline、是否已有 `.make_latex_model/` 工作区，适合作为辅助预检查。

```bash
python3 skills/make-latex-model/scripts/check_state.py projects/thesis-nju-master
```

注意：`check_state.py` 现会按 `config.yaml` 的产品线规则识别 `NSFC / paper / thesis / cv`；其余脚本是否适用，取决于它属于跨产品线辅助工具还是 NSFC 专项参数工具。

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

## NSFC 专项工具

以下能力主要服务 NSFC 参数对齐、批量校验或基于内置 NSFC 结构默认值的专项任务：

- `validate.sh` / `validate.bat`
- `benchmark.sh` / `benchmark.bat`
- `optimize.sh` / `optimize.bat`
- `optimize.py`
- `enhanced_optimize.py`
- `run_ai_optimizer.py`
- `intelligent_adjust.py`
- `sync_config.py`
- `core/template_catalog.py`
- `core/config_loader.py`

如果你的目标是：

- `projects/paper-*`
- `projects/thesis-*`
- `projects/cv-*`
- 或者一个不需要 NSFC 参数调优链路的项目

那么这些 NSFC 专项工具通常不应作为主流程。

## 推荐使用顺序

1. 先用官方构建脚本确认真实入口
2. 如果需要改 `packages/bensz-*`，先跑 `plan_package_regression.py`
3. 再视需要用这里的脚本补充分析
4. 不要让这里的脚本覆盖掉当前仓库的真实分层判断
