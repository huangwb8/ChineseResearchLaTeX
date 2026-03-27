# make-latex-model - ChineseResearchLaTeX 模板落地与高保真对齐

本 README 面向使用者：如何触发并正确使用 `make-latex-model`。当前版本：`v3.1.1`。执行边界与硬性规范见 `SKILL.md`，默认参数见 `config.yaml`。兼容旧写法 `make_latex_model`，但后续文档统一使用连字符名称。

## 现在它是干什么的

`make-latex-model` 当前是面向整个 ChineseResearchLaTeX 的模板落地与高保真对齐 skill：

- 支持 `NSFC / paper / thesis / cv` 四条产品线
- 会先判断应该改 `projects/*` 还是 `packages/bensz-*`
- 若必须改 `packages/bensz-*`，会先生成受影响模板回归计划，避免把其它现有模板带偏
- 默认走各产品线官方构建入口验收
- 对 `validate.sh`、`optimize.py`、`templates/nsfc/*.yaml` 这类脚本，统一按“NSFC 专项工具”理解，而不是把整个 skill 视为它们的延伸

## 推荐用法

最推荐直接用自然语言触发：

```text
请使用 make-latex-model skill。
目标项目：projects/thesis-nju-master
参考基线：projects/thesis-nju-master/assets/source/nju_mem_2023_2.pdf
目标：根据当前 ChineseResearchLaTeX 的真实分层，把这套模板调到可交付状态；如果问题属于共享样式，请优先改 packages/bensz-thesis，而不是只改项目层。
输出：直接修改代码并用官方构建入口验证；最后告诉我你改到了哪一层、为什么这样改。
```

## 常见场景

### 1. NSFC 新模板对齐

```text
请使用 make-latex-model skill 对 projects/NSFC_General 做样式对齐。
输入：官方 PDF 或 Word 导出 PDF
输出：按当前 packages/bensz-nsfc + projects/NSFC_General 的真实结构完成修改，并用官方构建命令验收。
```

### 2. 新 thesis 模板打磨

```text
请使用 make-latex-model skill 处理 projects/thesis-nju-master。
输入：学校 Word/PDF 模板、当前 baseline、现有 style 文件
输出：把需要共享的版式沉淀到 packages/bensz-thesis/styles/ 或 profiles/，并验证 thesis_project_tool.py 构建通过。
如果必须改 `packages/bensz-thesis/`，先生成回归计划并逐个验证现有 thesis 项目。
```

### 3. 论文模板 PDF / DOCX 一起对齐

```text
请使用 make-latex-model skill 优化 projects/paper-sci-01。
目标：既保证 PDF 版式更贴近参考模板，也不要破坏 DOCX 导出链路。
输出：按当前仓库标准完成修改，并通过 paper_project_tool.py 验证 PDF + DOCX。
```

### 4. 简历模板双语回归

```text
请使用 make-latex-model skill 优化 projects/cv-01。
目标：同时检查中文和英文入口，并在需要时修改 packages/bensz-cv 的共享样式。
输出：通过 cv_project_tool.py build --variant all 验证。
```

## 它现在默认怎么判断改哪里

| 情况 | 优先修改位置 |
|------|------|
| 只影响单个项目的正文装配、局部参数、项目资源 | `projects/*` |
| 影响多个项目共享的样式、profile、构建逻辑、字体接入 | `packages/bensz-*` |
| 既有项目入口问题，也有共享样式问题 | 项目层 + 包层联动 |

如果判断必须改公共包，额外增加一条硬规则：

```bash
python3 skills/make-latex-model/scripts/plan_package_regression.py packages/bensz-thesis
```

先用这个脚本生成“受影响模板 + 官方回归命令”列表，再真正编辑 `packages/`。没有完成这些回归前，不应把结果表述成“不会影响其它模板”。

## 官方验证命令

```bash
python packages/bensz-nsfc/scripts/nsfc_project_tool.py build --project-dir projects/NSFC_General
python packages/bensz-paper/scripts/paper_project_tool.py build --project-dir projects/paper-sci-01
python packages/bensz-thesis/scripts/thesis_project_tool.py build --project-dir projects/thesis-nju-master
python packages/bensz-cv/scripts/cv_project_tool.py build --project-dir projects/cv-01 --variant all
```

## 备选用法

如果你只是需要 PDF 参数提取、标题比对或像素比对，也可以单独用辅助脚本：

```bash
python3 skills/make-latex-model/scripts/check_state.py projects/thesis-nju-master
python3 skills/make-latex-model/scripts/plan_package_regression.py packages/bensz-thesis
python3 skills/make-latex-model/scripts/analyze_pdf.py <baseline.pdf> --project projects/NSFC_Young
python3 skills/make-latex-model/scripts/compare_headings.py <baseline.pdf> <main.tex>
python3 skills/make-latex-model/scripts/compare_pdf_pixels.py <baseline.pdf> <rendered.pdf>
```

这些脚本现在更适合做“辅助分析”或“NSFC 专项参数任务”。其中 `check_state.py` 已支持按产品线识别入口和官方构建命令；`validate.sh`、`optimize.py`、`templates/nsfc/*.yaml` 等脚本只应在明确属于 NSFC 专项参数对齐时使用，不应替代各产品线官方构建链路。

## 重要边界

- 不要默认把所有模板问题都塞回 `extraTex/@config.tex`
- 不要把共享实现从 `packages/bensz-*` 复制回项目层
- 改公共包前先生成回归计划，并回归该包覆盖的现有模板
- `paper` 场景要记得 PDF 与 DOCX 一起看
- `cv` 场景要记得中文与英文双入口一起看
- 如果没有用户要求，默认不重写正文语义内容

## 更多文档

- 总规范：`skills/make-latex-model/SKILL.md`
- 工作流：`skills/make-latex-model/docs/WORKFLOW.md`
- 常见问题：`skills/make-latex-model/docs/FAQ.md`
- 基线制作：`skills/make-latex-model/docs/BASELINE_GUIDE.md`
- 产品线规则：`skills/make-latex-model/references/PRODUCT_LINE_RULES.md`
- 脚本职责矩阵：`skills/make-latex-model/references/SCRIPT_SCOPE.md`
- 辅助脚本：`skills/make-latex-model/scripts/README.md`
