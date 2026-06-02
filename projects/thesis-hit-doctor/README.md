# thesis-hit-doctor

`thesis-hit-doctor` 是 `bensz-thesis` 的哈尔滨工业大学博士学位论文公开示例项目，基于 issue [#45](https://github.com/huangwb8/ChineseResearchLaTeX/issues/45) 中提供的 HIT 研究生院官方书写范例整理。

## 特点

- 项目在 `packages/bensz-thesis/` 中注册了独立的 `thesis-hit-doctor` template/profile/style
- 覆盖中文封面、中文题名页、英文题名页、中英文摘要、目录、英文目录、章节正文、结论、参考文献和后置材料
- 示例正文使用公开、去隐私的能源系统主题，不包含真实个人或保密项目材料
- 官方 Word 范例不直接随项目分发，来源和哈希记录见 [`docs/official/README.md`](docs/official/README.md)

## 构建

在仓库根目录运行：

```bash
python packages/bensz-thesis/scripts/thesis_project_tool.py build --project-dir projects/thesis-hit-doctor
```

在项目目录内运行：

```bash
python scripts/thesis_build.py
```

## DOCX 初稿

```bash
python packages/bensz-thesis/scripts/thesis_project_tool.py docx --project-dir projects/thesis-hit-doctor
```

DOCX 输出仅作为可编辑初稿，复杂对象、封面和学校签署页仍需人工复核。
