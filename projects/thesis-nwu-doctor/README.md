# thesis-nwu-doctor

`thesis-nwu-doctor` 是 `bensz-thesis` 的西北大学博士学位论文公开示例项目，基于 issue [#48](https://github.com/huangwb8/ChineseResearchLaTeX/issues/48) 中提供的《西北大学研究生学位论文规范》（研字〔2019〕7 号）和研究生院公开 Word 模板整理。

## 特点

- 项目在 `packages/bensz-thesis/` 中注册了独立的 `thesis-nwu-doctor` template/profile/style
- 覆盖中文封面、英文题名页、知识产权声明书、独创性声明、中英文摘要、目录、章节正文、结论、参考文献和博士论文后置材料
- 示例正文使用公开、去隐私的佐佐木希跨媒介职业转型主题，不包含真实个人隐私或保密项目材料
- 官方 PDF / Word 模板不直接随项目分发，来源和哈希记录见 [`docs/official/README.md`](docs/official/README.md)

## 构建

在仓库根目录运行：

```bash
python packages/bensz-thesis/scripts/thesis_project_tool.py build --project-dir projects/thesis-nwu-doctor
```

在项目目录内运行：

```bash
python scripts/thesis_build.py
```

## DOCX 初稿

```bash
python packages/bensz-thesis/scripts/thesis_project_tool.py docx --project-dir projects/thesis-nwu-doctor
```

DOCX 输出仅作为可编辑初稿，复杂对象、封面和学校签署页仍需人工复核。
