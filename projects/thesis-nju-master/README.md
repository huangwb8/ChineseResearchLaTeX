# thesis-nju-master

`thesis-nju-master` 是 `bensz-thesis` 的南京大学工程管理学院硕士论文示例项目，基于 issue [#37](https://github.com/huangwb8/ChineseResearchLaTeX/issues/37) 中公开提供的官方页面与 Word 附件整理。

说明：

- `main.tex` 是“公开附件的像素级验收入口”，直接复现由附件 `2023.2.docx` 转出的公开 PDF，用于稳定比对与 Release 验收
- `editable.tex` 是“干净可编辑的 NJU 硕士论文脚手架”，把 issue 材料中的教学标签与实际正文结构分离开，便于后续继续模板化
- 项目内 `assets/demo/` 复用了 issue 附件中的公开校徽/图表/截图素材，`assets/source/nju_mem_2023_2.pdf` 保留为公开基线

基线构建：

```bash
python packages/bensz-thesis/scripts/thesis_project_tool.py build --project-dir projects/thesis-nju-master
```

像素级比对：

```bash
python packages/bensz-thesis/scripts/thesis_project_tool.py compare \
  --project-dir projects/thesis-nju-master \
  --baseline-pdf projects/thesis-nju-master/assets/source/nju_mem_2023_2.pdf \
  --build-first
```

可编辑脚手架：

```bash
python packages/bensz-thesis/scripts/thesis_project_tool.py build \
  --project-dir projects/thesis-nju-master \
  --tex-file editable.tex
```

只打开项目子目录时，可执行：

```bash
python scripts/thesis_build.py
python scripts/thesis_build.py build --tex-file editable.tex
```
