# `{主题}_review.tex` Section 模板

> 供 `systematic-literature-review` 生成稳定、可编译、像综述而不是像笔记的正文骨架。

## 最小结构

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
- 所有比例之和不得超过 1.0
- 避免大段固定 `cm` 宽度

示例：

```tex
\begin{longtable}{p{0.14\textwidth} p{0.48\textwidth} p{0.22\textwidth} p{0.16\textwidth}}
```

## 快速自检

- [ ] 主体一级主题不超过 7 个
- [ ] 有独立讨论段
- [ ] 有独立展望段
- [ ] 标题按概念命名，不是“步骤 1/2/3”
