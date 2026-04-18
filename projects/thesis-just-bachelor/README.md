# thesis-just-bachelor

`thesis-just-bachelor` 是 `bensz-thesis` 的江苏科技大学本科毕业设计（论文）公开示例项目，基于 issue [#40](https://github.com/huangwb8/ChineseResearchLaTeX/issues/40) 中的公开 PDF 与理工类写作规范整理。

说明：

- 项目在 `packages/bensz-thesis/` 中注册了独立的 `thesis-just-bachelor` template/profile/style
- 公开交付层只保留模板代码、校名素材与示例正文，不在项目目录中混入私有论文 PDF 或敏感原稿
- 用于像素级对齐的原始材料、截图、差异图与实验记录统一留在 `tests/` 隔离工作区

构建方式：

```bash
python packages/bensz-thesis/scripts/thesis_project_tool.py build --project-dir projects/thesis-just-bachelor
```

只打开项目子目录时，可执行：

```bash
python scripts/thesis_build.py
```
