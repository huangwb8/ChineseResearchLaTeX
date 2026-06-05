# thesis-jlau-doctor

`thesis-jlau-doctor` 是 `bensz-thesis` 的吉林农业大学博士学位论文公开示例项目，基于 issue [#47](https://github.com/huangwb8/ChineseResearchLaTeX/issues/47) 中提供的学校公开写作规范、博士学位论文装订封面和理工农医类正文范例整理。

说明：

- 项目在 `packages/bensz-thesis/` 中注册了独立的 `thesis-jlau-doctor` template/profile/style
- 默认示例按“学术型博士、非盲审、理工农医类正文结构”组织，可在 `extraTex/meta.tex` 中切换 `\jlauDegreeKind` 与 `\jlauBlindReview`
- JLAU 硕士模板已作为 `thesis-jlau-master` 独立维护；本项目只承载博士学位论文封面字段和示例正文入口
- 公开交付层只保留模板代码、官方封面校徽/校名图素材与可公开示例正文，不在项目目录中混入私有论文或比对截图
- 用于样式分析、原始资料下载和验收记录的文件统一留在 `tests/` 隔离工作区

构建方式：

```bash
python packages/bensz-thesis/scripts/thesis_project_tool.py build --project-dir projects/thesis-jlau-doctor
```

只打开项目子目录时，可执行：

```bash
python scripts/thesis_build.py
```
