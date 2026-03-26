# UCAS 资环规范对照矩阵（Word 基线）

本文用于固定 `thesis-ucas-doctor` 的资环一致性验收口径，避免后续口径漂移。

说明：

- “具体要”原文件是 `.doc`，当前仓库环境无法直接完整结构化解析；本矩阵采用“双证据”固化基线：
-  1) 用户按 [`docs/official/README.md`](official/README.md) 自行下载并校验的“撰写具体要” `.doc`，用于人工核对条款关键词；
  2) 用户按同一说明下载并校验的资环 Word 模板 `.docx`，用于结构与样式结果比对。
- 验收优先看“结构与版式规则是否满足”；内容型规则（如摘要字数）单独按正文最终稿核查。
- 当前 DOCX 导出能力仅作为 `thesis-ucas-doctor` 项目级对齐参考，不构成 `bensz-thesis` 通用 DOCX 支持；图表/算法/代码环境/交叉引用等复杂对象仍需人工复核，后续持续优化。

## 对照矩阵

| 条款主题 | Word 模板基线（证据） | UCAS LaTeX 落点 | 检查方式 |
|---|---|---|---|
| 纸张 A4（210x297mm） | 质量检查 `page=11906x16838 twip` | `ucasDissertation.cls` 的 `geometry a4paper` | `export_docx.py` 质量报告 |
| 页边距与页眉页脚 | 质量检查 `top/bottom=1440`, `left/right=1797`, `header/footer=851` | `ucasDissertation.cls` 中 `top/bottom=2.54cm`, `left/right=3.17cm`, `headheight/headsep/footskip` | `export_docx.py` 质量报告 |
| 正文字体（宋体 + Times New Roman） | 质量检查 Normal 样式字体通过 | `ctexbook + fontspec + \\setmainfont{Times New Roman}` | `export_docx.py` 质量报告 |
| 正文行距/首行缩进（1.25 倍/两字符） | 质量检查 `line=300, firstLine=200` | `linespread=1.25` + `autoindent=true` | `export_docx.py` 质量报告 |
| 标题不超过三级（0083） | Word 模板 `Heading4=0` | `secnumdepth=subsection` + 对 `\\subsubsection` 及更深层级告警并降级为不入目录/不编号 | LaTeX 编译日志 + 质量报告 |
| 目录不超过三级（0036） | Word 模板目录域层级不超三级 | `\\setcounter{tocdepth}{2}` | `export_docx.py` 质量报告（目录域未更新可提示） |
| 结构必备：摘要/Abstract | Word 模板存在 | `extraTex/abstract.tex` + `\\makeAbstract` | `export_docx.py` 质量报告 |
| 结构必备：目录/图表目录 | Word 模板存在目录、图目录、表目录 | `main.tex` 的 `\\tableofcontents` + `\\listofmaterials`；DOCX 导出补齐结构标题 | `export_docx.py` 质量报告 |
| 结构必备：参考文献 | Word 模板存在 | `main.tex` 的 `\\printbibliography[heading=bibintoc]`；DOCX 导出补齐“参考文献”标题 | `export_docx.py` 质量报告 |
| 结构必备：致谢 | Word 模板存在 | `extraTex/acknowledgements.tex` | `export_docx.py` 质量报告 |
| 书脊页 | Word 模板提供“书脊”页 | `ucasDissertation.cls` 的 `\\makeSpine` + `spine.tex` 独立构建入口 | `thesis_project_tool.py build --tex-file spine.tex` |
| 参考文献规范（GB/T 7714-2015） | `.doc` 可提取到 `GB/T 7714 2015` | `biblatex` 使用 `gb7714-2015` | 构建日志 + PDF 复核 |

## 验收命令（项目级）

```bash
python packages/bensz-thesis/scripts/thesis_project_tool.py build --project-dir projects/thesis-ucas-doctor
python packages/bensz-thesis/scripts/thesis_project_tool.py build --project-dir projects/thesis-ucas-doctor --tex-file spine.tex
python3 projects/thesis-ucas-doctor/scripts/export_docx.py --project-dir projects/thesis-ucas-doctor
```

通过标准（本轮）：

- 质量报告中以下项应为 `PASS`：纸张、页边距、字体行距、正文不超三级、章节存在（摘要/Abstract/目录/图表目录/参考文献/致谢）。
- “目录域未更新”允许保留提示，不作为失败项。
