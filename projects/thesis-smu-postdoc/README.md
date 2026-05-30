# thesis-smu-postdoc

`thesis-smu-postdoc` 是一个基于 `bensz-thesis` 构建的南方医科大学博士后研究报告公开示例项目。

说明：

- 封面与题名页优先吸收《博士后研究报告编写规则》的国家通用口径，并结合南方医科大学现有公开模板资产做项目化重构
- 项目复用 `bensz-thesis` 的统一构建链路，不新增专门的 `bensz-postdoc` 公共包
- 当前已在 `packages/bensz-thesis/` 中注册独立的 `thesis-smu-postdoc` template/profile/style，不再引用 `thesis-smu-master`
- 当前正文、摘要、科研成果与个人简历均为公开演示内容，不包含任何真实出站材料或私有科研数据

构建方式：

```bash
python packages/bensz-thesis/scripts/thesis_project_tool.py build --project-dir projects/thesis-smu-postdoc
```

DOCX 初稿导出：

```bash
python packages/bensz-thesis/scripts/thesis_project_tool.py docx --project-dir projects/thesis-smu-postdoc
```

导出的 `main.docx` 是可编辑 Word draft，适合先进入 Word 继续编辑与送审沟通；复杂表格、成果清单、附录材料或特殊排版仍需结合 `.latex-cache/docx/main_docx_quality_report.md` 人工复核。若需对齐单位 Word 模板，可额外传入 `--reference-doc <path-to-reference.docx>`。

只打开项目子目录时，可执行：

```bash
python scripts/thesis_build.py
python scripts/thesis_build.py docx
```
