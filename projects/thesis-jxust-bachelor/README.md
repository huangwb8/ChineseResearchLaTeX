# thesis-jxust-bachelor

`thesis-jxust-bachelor` 是 `bensz-thesis` 的江西理工大学本科毕业论文 / 毕业设计公开示例项目，基于 issue [#49](https://github.com/huangwb8/ChineseResearchLaTeX/issues/49) 中公开上传的 2026 届毕业论文（设计）相关表格与附件 5 官方格式文件整理。

说明：

- 项目在 `packages/bensz-thesis/` 中注册了独立的 `thesis-jxust-bachelor` template/profile/style
- `main.tex` 中可通过 `\jxustSetWorkType{thesis}` / `\jxustSetWorkType{design}` 切换“本科毕业论文 / 本科毕业设计”的封面标题和正文页眉
- 公开交付层只保留模板代码与示例正文，不在项目目录中混入私有论文 PDF、验收截图或敏感原稿
- 用于像素级对齐的原始材料、截图、差异图与实验记录统一留在 `tests/` 隔离工作区

构建方式：

```bash
python packages/bensz-thesis/scripts/thesis_project_tool.py build --project-dir projects/thesis-jxust-bachelor
```

只打开项目子目录时，可执行：

```bash
python scripts/thesis_build.py
```
