# thesis-scu-master

四川大学硕士学位论文可编辑示例，对应 [issue #56](https://github.com/huangwb8/ChineseResearchLaTeX/issues/56)。正文以“佐佐木希跨媒介公众形象的内容表达”为简短演示主题，包含双语摘要、目录、四级标题、流程图、模拟计数表、连续脚注、参考文献、附录、致谢、科研成果与两份声明。正文同时保留高分子链统计的多行公式、矢量求和、函数曲线与模型比较表，方便直接查看各类排版效果。

本版依据 issue 提供的**法学院**附件建立，尚不能视为高分子学院现行规范的官方认证。附件间的冲突、字体替代及适用边界见 [规范来源与取舍](docs/specification.md)。社区模板用于结构参考，本项目未引入其文档类，也无需初始化 Git 子模块。

## 开始写作

修改 `extraTex/meta.tex` 中的题目、作者、导师、培养单位、专业、日期等字段；正文位于 `extraTex/body/`，摘要位于 `extraTex/front/`，参考文献与其他后置材料位于 `extraTex/back/`。培养单位待填写，新闻与传播专业及身份信息均为演示占位。正文未开展系统材料采集或受众调查，计数为模拟值；高分子模型曲线由指定公式计算，用于格式展示。双语摘要为简短示例，正式稿需按实际研究和学院篇幅要求重写。

在仓库根目录构建：

```bash
python packages/bensz-thesis/scripts/thesis_project_tool.py build --project-dir projects/thesis-scu-master
```

仅打开项目目录时，先安装 `bensz-thesis` 及其 `bensz-fonts` 依赖，再执行：

```bash
python scripts/thesis_build.py
```

输出 `main.pdf`，中间文件集中在 `.latex-cache/`。使用 XeLaTeX 和 TeX Live 自带的 Fandol、TeX Gyre Termes 字体，无需额外中文字体、Biber 或 Shell escape。VS Code 可打开 `thesis-scu-master.code-workspace`，通过 LaTeX Workshop 调用同一构建入口。独立 Overleaf 包使用 XeLaTeX 编译 `main.tex`。

## 引注与参考文献

按附件6使用 `句子。\footnote{参见 作者. 文献题名……}`，生成标点后的连续阿拉伯数字上标脚注，跨章不重置。直接引语、间接引用与转引分别写明来源，特定观点附核实后的页码；重复引注的“同上注”或“见前注”由作者维护，可用 `\label` / `\ref` 引用原注号，不自动推断引用关系。

书目在 `extraTex/back/references.tex` 中显式按类别排列，同类内按作者字母顺序排列，中文按拼音；`\scuReferenceGroup{类别}` 不占编号，`\bibitem{key}` 连续编号。普通 `\cite{key}` 仍可使用，但它本身不生成附件6要求的完整脚注。高分子学院若另有数值引文或 GB/T 7714 要求，应先核对学院规则，再更换引用方案；法学院引注要求不代表所有学院统一要求。

## Word 初稿

附件要求使用 Word 排版。本项目提供 LaTeX 工作稿与 PDF；通用导出入口可生成供继续编辑的 Word 初稿：

```bash
python packages/bensz-thesis/scripts/thesis_project_tool.py docx --project-dir projects/thesis-scu-master
```

如已下载官方 Word 模板，可加 `--reference-doc /path/to/5.docx`。当前通用转换会遗漏自定义摘要标题与关键词值，脚注可能转为正文，并存在排版命令残留；公式与图表也需重建。该输出仅用于辅助提取和继续编辑正文，不保证16开版式、封面、脚注与 PDF 一致。检查 `.latex-cache/docx/` 的质量报告，并在 Word 中人工补齐和排版；不能将初稿导出等同于已经满足 Word 提交规范。
