# paper-sci-01

`paper-sci-01` 是本仓库中首个可直接渲染 PDF 和 DOCX 的 SCI 论文示例项目。

它的核心特点是：

- 依赖公共包 [`packages/bensz-paper`](/Volumes/2T01/Github/ChineseResearchLaTeX/packages/bensz-paper)
- 正文只维护在 `extraTex/**/*.tex`
- DOCX 构建时仅在运行期临时生成 Markdown，不再持久化正文 `.md`
- 同一份正文可同时输出 `main.pdf` 与 `main.docx`

## 内容来源说明

本项目示例正文基于一篇公开发表的 *Cancer Cell* 文章的公开题名、元数据和摘要信息重写而成，仅用于模板演示：

- Greenhalgh R, Brady SW, Yang W, et al. *The landscape of structural variation in pediatric cancer*. Cancer Cell. 2026. DOI: `10.1016/j.ccell.2026.02.012`

这里的英文正文不是期刊原文复制，也没有使用你提供的未发表论文正文。

## 构建

仓库内开发时，推荐直接执行：

```bash
python packages/bensz-paper/scripts/paper_project_tool.py build --project-dir projects/paper-sci-01
```

若只打开了项目子目录，可执行：

```bash
python scripts/paper_build.py
```

构建成功后会产出：

- `main.pdf`
- `main.docx`
- `.latex-cache/`

## 结构

- `main.tex`：LaTeX 主入口
- `extraTex/`：正文 LaTeX 单一真相来源
- `artifacts/reference.docx`：DOCX 样式模板
- `artifacts/manuscript.csl`：参考文献样式
- `references/refs.bib`：BibTeX 数据库
- `scripts/paper_build.py`：项目级构建 wrapper
