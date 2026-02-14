---
name: nsfc-bib-manager
description: 当用户明确要求"加引用""补参考文献""核对论文信息""写bibtex""更新.bib"时使用。新增/核验论文信息（题目/作者/年份/期刊/DOI）并写入 `references/ccs.bib` 或 `references/mypaper.bib`，保证不出现幻觉引用。
metadata:
  short-description: NSFC 标书引用与 Bib 管理
  keywords:
    - nsfc
    - bibtex
    - 参考文献
    - 引用管理
    - 文献核验
    - bib 文件
  triggers:
    - 加引用
    - 补参考文献
    - 核对论文信息
    - 写 bibtex
    - 更新 bib
config: skills/nsfc-bib-manager/config.yaml
---

# 引用与 Bib 管理器

目标：只引“可核验”文献，且通过 `\\cite{...}` 使用，不手写参考文献列表。

## 0) 规则（硬约束）

- 不凭记忆编造 DOI/卷期页码/作者列表；核验不到就先不加，并标注“待核验”。
- 新增条目优先写入 `references/ccs.bib`（通用文献）；申请人已发论文写入 `references/mypaper.bib`。
- 参考文献样式不动：不要改 `references/reference.tex` 的 `\\bibliographystyle{bibtex-style/gbt7714-nsfc.bst}`。

## 1) 工作流（每次新增引用都走）

1) 明确要支持的“主张”是什么（避免为了凑数加文献）。
2) 联网检索并核验元数据：优先用 MCP 的论文检索/出版方元数据（题目、年份、期刊、DOI）。
3) 生成 BibTeX 条目并落库（只做最小增量改动）。
4) 在对应 `.tex` 中使用 `\\cite{key}` 引用（不手写条目）。

