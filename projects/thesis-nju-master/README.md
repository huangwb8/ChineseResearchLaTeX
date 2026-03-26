# thesis-nju-master

`thesis-nju-master` 是 `bensz-thesis` 的南京大学工程管理学院硕士论文示例项目，基于 issue [#37](https://github.com/huangwb8/ChineseResearchLaTeX/issues/37) 中公开提供的官方页面与 Word 附件整理。

说明：

- `main.tex` 是默认可编辑入口，直接承载 NJU 硕士论文脚手架，便于用户按常见习惯打开项目后直接开始写作和渲染
- `editable.tex` 保留为兼容旧命令的别名入口，当前与 `main.tex` 渲染同一份正文
- `baseline.tex` 是“公开附件的像素级验收入口”，直接复现由附件 `2023.2.docx` 转出的公开 PDF，用于稳定比对与 Release 验收
- 项目内 `assets/demo/` 复用了 issue 附件中的公开校徽/图表/截图素材，`assets/source/nju_mem_2023_2.pdf` 保留为公开基线

默认构建：

```bash
python packages/bensz-thesis/scripts/thesis_project_tool.py build --project-dir projects/thesis-nju-master
```

公开基线构建：

```bash
python packages/bensz-thesis/scripts/thesis_project_tool.py build \
  --project-dir projects/thesis-nju-master \
  --tex-file baseline.tex
```

像素级比对：

```bash
python packages/bensz-thesis/scripts/thesis_project_tool.py compare \
  --project-dir projects/thesis-nju-master \
  --baseline-pdf projects/thesis-nju-master/assets/source/nju_mem_2023_2.pdf \
  --tex-file baseline.tex \
  --build-first
```

兼容旧命令：

```bash
python packages/bensz-thesis/scripts/thesis_project_tool.py build \
  --project-dir projects/thesis-nju-master \
  --tex-file editable.tex
```

只打开项目子目录时，可执行：

```bash
python scripts/thesis_build.py
python scripts/thesis_build.py build --tex-file baseline.tex
python scripts/thesis_build.py build --tex-file editable.tex
```
