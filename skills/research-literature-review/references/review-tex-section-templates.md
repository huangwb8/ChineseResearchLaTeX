# `{主题}_review.tex` Section 模板

> 写作或调整版式时读取。供 `research-literature-review` 生成可编译的综述正文骨架；论证与证据规则见 [专家写作指南](expert-review-writing.md)。

## 默认学术版式入口

新稿先写含摘要和章节的正文片段，再运行：

```bash
python scripts/render_review_template.py --title "文稿题名" --body body.tex --bib 主题_参考文献.bib --output 主题_review.tex
```

Bib 应先放在输出目录或子目录。该入口实际应用 `references/latex-template/review-article.tex`，默认标题、摘要和正文连续排版，自动章节编号，数字上标引用，ctex 自动选择字体。默认不添加封面、目录、档位宣传或任务编号；已有完整 TeX 和用户指定模板不重写。

`compile_latex_with_bibtex.py --template` 只追加资源搜索目录，不会替换导言区或应用 Pandoc 模板。旧 `nature-reviews-template.tex` 是 Pandoc 兼容资产，不能直接用 XeLaTeX 当正文编译。

## 最小结构

以下为默认结构；用户或期刊指定其它结构时遵从其要求，并同步调整结构检查参数。

- `Abstract` / `摘要`
- `Introduction`
- 3-7 个主体 `\section`
- `Questions and concerns` / `讨论`
- `Perspectives` / `展望`
- `Conclusion` / `结论`

## 最小骨架示例

```tex
\begin{abstract}
背景 → 主要趋势/发现 → 挑战 → 展望。
\end{abstract}

\section{Introduction}
问题重要性、旧共识、研究缺口、本文路线。

\section{Topic 1}
局部主张 + 关键证据 + 边界。

\section{Topic 2}
局部主张 + 关键证据 + 边界。

\section{Topic 3}
局部主张 + 关键证据 + 边界。

\section{Questions and concerns}
异质性、方法学陷阱、争议来源。

\section{Perspectives}
可检验研究议程与现实约束。

\section{Conclusion}
回收中心主张与实践意义。
```

## 主体 section 的最低要求

- 开头必须说明该主题在整篇稿件中的角色
- 每节至少有：
  - 一个局部主张
  - 若干关键证据
  - 一句边界或反例

## 表格规则

- 列宽基于 `\textwidth` 按比例分配
- 可用列宽需扣除每列两侧的 `\tabcolsep`；比例和为 1.0 仍可能溢出
- 避免大段固定 `cm` 宽度

示例：

```tex
% 四列合计占满 textwidth，扣除八份 tabcolsep
\begin{longtable}{p{\dimexpr0.14\textwidth-2\tabcolsep\relax}
                  p{\dimexpr0.48\textwidth-2\tabcolsep\relax}
                  p{\dimexpr0.22\textwidth-2\tabcolsep\relax}
                  p{\dimexpr0.16\textwidth-2\tabcolsep\relax}}
```

## 快速自检

- [ ] 默认有 3–7 个主体一级主题，或已按明确要求调整检查参数
- [ ] 有独立讨论段
- [ ] 有独立展望段
- [ ] 标题按概念命名，不是“步骤 1/2/3”
- [ ] 不同时使用自动编号和标题文字中的手写编号
- [ ] 图表用相对路径；实际依赖放在 supporting 内，随完整文稿包发布
- [ ] PDF 最后一次编译没有未解析引用/缺字；Word 从 Heading1 开始，数字引文可见
- [ ] 中文、最长表格、图注及书目经过实际渲染检查，记录页码与限制
