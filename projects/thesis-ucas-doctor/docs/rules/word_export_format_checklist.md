# UCAS Word 导出格式对照清单

本清单用于 `projects/thesis-ucas-doctor/` 的 Word 导出格式核对，记录公开模板中可自动检查和需要人工复核的边界。

## 适用范围

- 适用项目：`projects/thesis-ucas-doctor/`
- 核心脚本：`projects/thesis-ucas-doctor/scripts/export_docx.py`
- 参考模板：`projects/thesis-ucas-doctor/docs/official/中国科学院大学资环学科群研究生学位论文word模板.docx`
- 规范原件：`projects/thesis-ucas-doctor/docs/official/中国科学院大学资源与环境学位评定分委员会研究生学位论文撰写具体要.doc`

## 导出口径

前置依赖：

- `pandoc` 是 `portable` 和 `strict` 模式的必需依赖。
- `python-docx` 是 `strict` 模式和 DOCX 后处理的必需依赖。
- Microsoft Word 与 `powershell` / `pwsh` 只在使用 `--word-update-fields` 自动刷新目录域时需要。

推荐先使用 `portable` 模式确认链路可运行，再按本机环境切换到 `strict`：

```bash
python projects/thesis-ucas-doctor/scripts/export_docx.py \
  --project-dir projects/thesis-ucas-doctor \
  --reference-doc projects/thesis-ucas-doctor/docs/official/中国科学院大学资环学科群研究生学位论文word模板.docx \
  --mode portable
```

正式验收可追加：

```bash
python projects/thesis-ucas-doctor/scripts/export_docx.py \
  --project-dir projects/thesis-ucas-doctor \
  --reference-doc projects/thesis-ucas-doctor/docs/official/中国科学院大学资环学科群研究生学位论文word模板.docx \
  --prepare-tex \
  --mode strict
```

`--word-update-fields` 依赖可自动化 Word 的本机环境，属于增强项；公开 CI 不应默认依赖。

## 自动后处理重点

- 标题层级：保持章、节、小节的 Word 标题层级和编号间距。
- 图表题：中文使用 `图X-Y` / `表X-Y`，英文使用 `Figure X-Y` / `Table X-Y`。
- 图片段落：图片所在段落应居中，并清除正文首行缩进。
- 参考文献：按参考模板调整段落样式、悬挂缩进和字体。
- 目录和图表目录：脚本可插入或修复目录域；实际页码更新仍建议在 Word 中最终确认。
- 数学与统计表达：简单统计表达可转为普通文本加斜体统计字母；复杂公式保留数学结构。
- DOCX 包完整性：`strict` 模式会检查关系、content-types、XML 和书签等结构。

## 人工复核项

- 封面、题名页、摘要页、目录页和正文起始页的分页是否符合参考模板。
- 图表目录与正文图表题是否一致。
- 参考文献条目是否按目标样式显示。
- 复杂公式、长表格、横向页面和大型图片是否需要人工微调。
- 使用 `--word-update-fields` 后，目录页码和图表目录页码是否已刷新。

## 公开边界

本清单只记录公开模板和通用导出规则，不保存真实论文正文、真实审阅记录、过程日志、本机路径或个人环境名称。导出产生的 `.docx`、中间 Markdown、质量报告和 `.latex-cache/` 产物不应提交。
