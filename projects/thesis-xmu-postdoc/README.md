# 厦门大学博士后研究工作报告 LaTeX 模板

本模板根据厦门大学《博士后研究工作报告（范本）》制作。示例依次包含封面、双语题名页、著作权使用声明、中英文摘要、目次、正文、参考文献、附录，以及致谢、博士生和博士后期间发表的学术论文与专著、个人简历和联系地址。目录、章节页码、交叉引用和参考文献由 LaTeX 生成。

[厦门大学博士后出站指南](https://postdoctor.xmu.edu.cn/info/1023/1884.htm) · [Issue #57 与 Word 范本](https://github.com/huangwb8/ChineseResearchLaTeX/issues/57) · [示例 PDF](main.pdf)

## 编译

在仓库根目录运行：

```bash
python packages/bensz-thesis/scripts/thesis_project_tool.py build --project-dir projects/thesis-xmu-postdoc
```

单独使用项目目录时，先安装包含 `thesis-xmu-postdoc` profile 的 [bensz-thesis](../../packages/bensz-thesis/)，再在项目目录运行 `python scripts/thesis_build.py`。使用 TeX Live 的 XeLaTeX 和 Biber 编译，需安装 `ctex`、`tocloft` 和 `biblatex-gb7714-2015` 等宏包，输出为 `main.pdf`。使用 Overleaf 版工程时，上传完整 ZIP，将主文件设为 `main.tex`，编译器设为 XeLaTeX。

## 修改内容

| 文件 | 填写内容 |
| --- | --- |
| [extraTex/meta.tex](extraTex/meta.tex) | 中文题名、英文题名、姓名、一级学科流动站、二级学科专业及日期 |
| [extraTex/front/declaration.tex](extraTex/front/declaration.tex) | 著作权使用声明。按实际情况选择保密项，保密报告填写纸本和电子版解密年份，并由作者与合作导师签字 |
| [extraTex/front/](extraTex/front/) | 中英文摘要和关键词 |
| [extraTex/body/](extraTex/body/) | 正文章节。增删章节后同步调整 [main.tex](main.tex) 的输入顺序 |
| [references/refs.bib](references/refs.bib) | 参考文献。使用 `\cite{键名}` 引用，按 GB/T 7714 顺序编码输出 |
| [extraTex/back/](extraTex/back/) | 附录、致谢、科研成果、个人简历和联系地址 |

## 版式

页面统一为 A4。封面和题名页按范本的字段和布局排版，正文用小四宋体、二字缩进和 1.5 倍行距。缺少系统宋体时使用 TeX Live 自带的 Fandol 宋体，西文字体缺少 Times New Roman 时使用 TeX Gyre Termes。

范本的“封面”“题名页”等标识用于指示样页，成稿保留各页实际标题。前置页不显示页码，正文从引言起按阿拉伯数字连续编号，页码在右下角。范本未提供正文样页，正文版心采用博士后研究报告编写规则的页边距，上 30 mm、下 25 mm、左 35 mm、右 20 mm。附录沿用正文页码，图表和公式用附录字母编号，例如 A1。

模板中的示例用于展示写法。正式提交时，签字、装订和交件要求以 [厦门大学博士后出站指南](https://postdoctor.xmu.edu.cn/info/1023/1884.htm) 为准。
