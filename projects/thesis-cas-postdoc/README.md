# thesis-cas-postdoc

`thesis-cas-postdoc` 是一个基于 `bensz-thesis` 构建的中国科学院博士后出站研究报告公开示例项目。

说明：

- 封面与题名页优先吸收《博士后研究报告编写规则》的国家通用口径，并按中国科学院博士后出站报告场景做项目化重构
- 项目复用 `bensz-thesis` 的统一构建链路，不新增专门的 `bensz-postdoc` 公共包
- 当前已在 `packages/bensz-thesis/` 中注册独立的 `thesis-cas-postdoc` template/profile/style，不再引用 `thesis-cas-master`
- 当前正文、摘要、科研成果与个人简历均为公开演示内容，作者固定为“冯宝宝”，主题围绕“佐佐木希”相关公开文化研究方向，不包含任何真实出站材料或私有科研数据

## 格式来源映射

本模板参考 `assets/1-2.doc` 中《博士后研究报告编写规则》的结构与版式口径，并将其中可稳定工程化的要求落实为模板默认行为：

| 来源规则 | 模板行为 | 口径 |
| --- | --- | --- |
| A4 纸，天头 30mm、订口 35mm 以上、地脚 25mm、切口 20mm 以上 | `thesis-cas-postdoc` 独立 style 使用 A4，并设置 `left=3.5cm,right=2.0cm,top=3.0cm,bottom=2.5cm` | 严格实现目标 |
| 正文使用四号宋体，中文题名、封面和章节标题使用黑体或等价无衬线字体 | 正文入口统一 `\zihao{4}`，CJK 主字体优先 Songti，标题与封面关键文字使用 CJK sans/黑体族 | 严格实现目标 |
| 封面、题名页、摘要、目录、插图清单、附表清单、正文、参考文献、附录和后置材料顺序完整 | `main.tex` 按该顺序装配公开示例内容，正文从第一章开始重置阿拉伯页码 | 严格实现目标 |
| 正文页码从正文第一页开始，页码位于右下角 | 前置页使用 Roman 页码并居中，正文使用 Arabic 页码并在右下角显示；第一章前执行 `\pagenumbering{arabic}` 与 `\setcounter{page}{1}` | 严格实现目标 |
| 每一篇或部分另页起 | 正文章节通过 `\casdocMainChapter{...}` 入口显式分页，继续保留 `openany`，不强制奇数页起排 | 严格实现目标 |
| 插图题名在图下，附表题名在表上 | style 分别设置 figure/table caption 位置；示例图 caption 置于图后，示例表和 longtable caption 置于表前 | 严格实现目标 |
| 附录中图、表、公式按附录字母编号 | `\casdocAppendix` 将附录图、表、公式编号切换为 `A1`、`B2` 这类字母前缀格式 | 严格实现目标 |
| 参考文献著录遵循国家标准 | 默认使用 `gb7714-2015`；字号使用五号、1.2 倍行距的紧凑排版，作为长文档可读性与篇幅的工程折中 | 模板默认选择 |

正文研究内容、成果条目、个人简历、通信地址和致谢属于内容作者应替换的示例材料；模板只保证这些位置的结构、页码、目录和基础排版稳定。

构建方式：

```bash
python packages/bensz-thesis/scripts/thesis_project_tool.py build --project-dir projects/thesis-cas-postdoc
```

DOCX 初稿导出：

```bash
python packages/bensz-thesis/scripts/thesis_project_tool.py docx --project-dir projects/thesis-cas-postdoc
```

导出的 `main.docx` 是可编辑 Word draft，适合先进入 Word 继续编辑与送审沟通；复杂表格、成果清单、附录材料或特殊排版仍需结合 `.latex-cache/docx/main_docx_quality_report.md` 人工复核。若需对齐单位 Word 模板，可额外传入 `--reference-doc <path-to-reference.docx>`。

只打开项目子目录时，可执行：

```bash
python scripts/thesis_build.py
python scripts/thesis_build.py docx
```
