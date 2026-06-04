# thesis-jlau-master

`thesis-jlau-master` 是 `bensz-thesis` 的吉林农业大学硕士论文公开示例项目，基于 issue [#47](https://github.com/huangwb8/ChineseResearchLaTeX/issues/47) 中提供的学校公开写作规范、学术型硕士封面、专业硕士封面和理工农医类正文范例整理。

说明：

- 项目在 `packages/bensz-thesis/` 中注册了独立的 `thesis-jlau-master` template/profile/style
- 默认示例按“学术型硕士、非盲审、理工农医类正文结构”组织，可在 `extraTex/meta.tex` 中切换 `\jlauDegreeKind` 与 `\jlauBlindReview`
- issue 标题中包含“硕博”，但表单学位类型明确为“硕士”；本项目先交付硕士模板，博士模板应后续以独立 `thesis-jlau-doctor` 项目推进
- 公开交付层只保留模板代码、校徽素材与可公开示例正文，不在项目目录中混入私有论文或比对截图
- 用于样式分析、原始资料下载和验收记录的文件统一留在 `tests/` 隔离工作区

构建方式：

```bash
python packages/bensz-thesis/scripts/thesis_project_tool.py build --project-dir projects/thesis-jlau-master
```

只打开项目子目录时，可执行：

```bash
python scripts/thesis_build.py
```
