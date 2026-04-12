# paper-sci-01

`paper-sci-01` 是本仓库中首个可直接渲染 PDF 和 DOCX 的 SCI 论文示例项目。

它的核心特点是：

- 依赖公共包 [`packages/bensz-paper`](/Volumes/2T01/Github/ChineseResearchLaTeX/packages/bensz-paper)
- 正文只维护在 `extraTex/**/*.tex`
- DOCX 构建时仅在运行期临时生成 Markdown，不再持久化正文 `.md`
- 示例正文包含一个最小资源表，用于同时演示 PDF / DOCX 表格输出
- 示例正文包含一组代表性数学公式，用于人工审查 PDF / DOCX 对公式的支持程度
- 同一份正文可同时输出 `main.pdf` 与 `main.docx`
- PDF / DOCX 参考文献默认优先保留 DOI，不重复打印 `doi.org` URL
- DOCX 参考文献区默认保持 `References` 一级标题，并避免把编号与正文拆成两段

## 内容来源说明

本项目示例正文基于一篇公开发表的 *Cancer Cell* 文章的公开题名、元数据和摘要信息重写而成，仅用于模板演示：

- Greenhalgh R, Brady SW, Yang W, et al. *The landscape of structural variation in pediatric cancer*. Cancer Cell. 2026. DOI: `10.1016/j.ccell.2026.02.012`

这里的英文正文不是期刊原文复制，也没有使用你提供的未发表论文正文。

## 构建

仓库内开发时，推荐直接执行：

```bash
python packages/bensz-paper/scripts/paper_project_tool.py build --project-dir projects/paper-sci-01
python packages/bensz-paper/scripts/paper_project_tool.py count-words projects/paper-sci-01/extraTex/body/introduction.tex projects/paper-sci-01/extraTex/body/results.tex projects/paper-sci-01/extraTex/body/discussion.tex
```

若只打开了项目子目录，可执行：

```bash
python scripts/paper_build.py
```

构建成功后会产出：

- `main.pdf`
- `main.docx`
- `.latex-cache/`

其中 DOCX 构建链会为 Pandoc 默认生成的 `Normal Table` 补上可见横向边框，通过 HTML5 + MathML 中间态把示例中的数学公式转换为 Word 原生公式对象，避免在 Word 中退化成源码文本，并保持参考文献区为单段编号列表而不是“编号单独一行、正文另起一行”。

若需在投稿前快速核对正文字数，可直接对对应的 `extraTex/**/*.tex` 运行 `count-words`；脚本会忽略 LaTeX 命令名、引用 keys 与数学公式源码，只统计渲染后可见文本。

## 结构

- `main.tex`：LaTeX 主入口
- `extraTex/`：正文 LaTeX 单一真相来源
- `artifacts/reference.docx`：DOCX 样式模板
- `artifacts/manuscript.csl`：参考文献样式
- `references/refs.bib`：BibTeX 数据库
- `scripts/paper_build.py`：项目级构建 wrapper
