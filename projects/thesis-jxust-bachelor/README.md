# thesis-jxust-bachelor

`thesis-jxust-bachelor` 是 `bensz-thesis` 的江西理工大学本科毕业论文 / 毕业设计公开示例项目，基于 issue [#49](https://github.com/huangwb8/ChineseResearchLaTeX/issues/49) 中公开上传的 2026 届毕业论文（设计）相关表格与附件 5 官方格式文件整理。

说明：

- 项目在 `packages/bensz-thesis/` 中注册了独立的 `thesis-jxust-bachelor` template/profile/style
- `main.tex` 中可通过 `\jxustSetWorkType{thesis}` / `\jxustSetWorkType{design}` 切换正文页眉中的“本科毕业论文 / 本科毕业设计”；封面按官方附件 6 保留通用标题“本科毕业论文(设计)”
- 封面默认使用附件 6 中拆分出的官方校徽与黑色书法校名图，项目层保存为 `assets/branding/jxust_emblem_official.jpeg` 与 `assets/branding/jxust_wordmark_official.jpeg`；官网横版标志图 `assets/branding/jxust_logo.jpg` 仅作为回退素材保留
- 封面后默认插入附件 6 的“独创性声明”和“关于论文（设计）使用授权的说明”；附件 13 的个人诚信承诺书属于归档材料，不默认纳入论文终稿 PDF，如需单独输出可调用 `\jxustMakeIntegrityCommitment`
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
