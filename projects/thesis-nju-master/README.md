# thesis-nju-master

`thesis-nju-master` 是 `bensz-thesis` 的南京大学工程管理学院硕士论文示例项目，基于 issue [#37](https://github.com/huangwb8/ChineseResearchLaTeX/issues/37) 中公开提供的官方页面与 Word 附件整理。

说明：

- `main.tex` 是默认可编辑入口，直接承载 NJU 硕士论文脚手架，便于用户按常见习惯打开项目后直接开始写作和渲染
- `editable.tex` 保留为兼容旧命令的别名入口，当前与 `main.tex` 渲染同一份正文
- `main.tex` 默认包含封面、学号/答辩页、英文题名页、原创性声明、学位论文使用授权声明、中英文摘要、目录、正文、参考文献、致谢、附录与出版授权书
- 项目内 `assets/demo/` 复用了 issue 附件中的公开校徽/图表/截图素材，`assets/source/nju_mem_2023_2.pdf` 保留为官方附件导出的公开参考 PDF

默认构建：

```bash
python packages/bensz-thesis/scripts/thesis_project_tool.py build --project-dir projects/thesis-nju-master
```

DOCX 初稿导出：

```bash
python packages/bensz-thesis/scripts/thesis_project_tool.py docx --project-dir projects/thesis-nju-master
```

导出的 `main.docx` 是可编辑 Word draft，不承诺与 PDF 像素级一致；复杂表格、图表、算法和特殊宏会在 `.latex-cache/docx/main_docx_quality_report.md` 中列出人工复核提示。若需贴近学校 Word 附件样式，可额外传入 `--reference-doc <path-to-reference.docx>`。

官方附件参考：

`assets/source/nju_mem_2023_2.pdf` 是 issue #37 所附 Word 模板转换得到的公开参考文件。当前 `main.tex` 是面向真实写作的可编辑脚手架，不逐页复刻附件中的教学标注页和两个封面样张，因此默认不承诺与该参考 PDF 像素级一致。

兼容旧命令：

```bash
python packages/bensz-thesis/scripts/thesis_project_tool.py build \
  --project-dir projects/thesis-nju-master \
  --tex-file editable.tex
```

只打开项目子目录时，可执行：

```bash
python scripts/thesis_build.py
python scripts/thesis_build.py docx
python scripts/thesis_build.py build --tex-file editable.tex
```
