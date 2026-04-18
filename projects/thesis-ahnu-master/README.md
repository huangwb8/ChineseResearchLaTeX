# thesis-ahnu-master

`thesis-ahnu-master` 是 `bensz-thesis` 的安徽师范大学硕士论文公开示例项目，基于 issue [#41](https://github.com/huangwb8/ChineseResearchLaTeX/issues/41) 中的公开样例 PDF，并结合学校公开研究生手册中的硕士论文格式条款整理。

说明：

- 项目在 `packages/bensz-thesis/` 中注册了独立的 `thesis-ahnu-master` template/profile/style
- 公开交付层只保留模板代码、校名字样素材与可公开示例正文，不在项目目录中混入私有论文 PDF 或比对截图
- 用于样式分析、原始资料下载、差异图和验收记录的文件统一留在 `tests/` 隔离工作区

构建方式：

```bash
python packages/bensz-thesis/scripts/thesis_project_tool.py build --project-dir projects/thesis-ahnu-master
```

只打开项目子目录时，可执行：

```bash
python scripts/thesis_build.py
```
