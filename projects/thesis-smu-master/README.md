# thesis-smu-master

`thesis-smu-master` 是 `bensz-thesis` 的南方医科大学硕士论文公开示例项目。

说明：

- 版式源自已验证的 SMU 临床医学硕士论文样式
- 当前正文、图表和摘要均为公开重写的演示内容
- 作者统一使用“冯宝宝”
- 项目用于展示模板能力，不包含任何真实病历或私有论文正文

构建方式：

```bash
python packages/bensz-thesis/scripts/thesis_project_tool.py build --project-dir projects/thesis-smu-master
```

DOCX 初稿导出：

```bash
python packages/bensz-thesis/scripts/thesis_project_tool.py docx --project-dir projects/thesis-smu-master
```

导出的 `main.docx` 是可编辑 Word draft，复杂图表、算法或特殊 LaTeX 构造需按 `.latex-cache/docx/main_docx_quality_report.md` 提示人工复核；如需对齐学校 Word 样式，可额外传入 `--reference-doc <path-to-reference.docx>`。

只打开项目子目录时，可执行：

```bash
python scripts/thesis_build.py
python scripts/thesis_build.py docx
```
