# SCI 论文模板标准

本文档描述当前仓库里 SCI 论文模板的标准形态。它基于以下真实项目和源码整理：

- `projects/paper-sci-01/`
- `packages/bensz-paper/`
- `packages/bensz-fonts/`

## 标准目标

一个标准的 SCI 论文项目，应当满足：

- 项目层只维护 `main.tex` 与 `extraTex/**/*.tex` 正文片段
- PDF 和 DOCX 都来自同一份 LaTeX 正文来源
- 公共版式、profile、DOCX 构建逻辑都留在 `packages/bensz-paper/`
- 不持久化重复的 Markdown 正文副本

## 真实分层

### 公共包负责什么

`packages/bensz-paper/` 负责：

- `bensz-paper.sty`：公共入口
- `bml-core.sty`：`template=...` 解析、profile 加载、模块装配
- `bml-*.sty`：版心、标题、字体、浮动体、参考文献、review mode
- `profiles/`：模板默认参数
- `scripts/manuscript_tool.py`：PDF + DOCX 统一构建
- `scripts/paper_project_tool.py`：仓库内项目 wrapper

`packages/bensz-fonts/` 负责共享字体接入。

### 项目负责什么

`projects/paper-sci-01/` 负责：

- `main.tex`：正文组装顺序
- `extraTex/front|body|back/**/*.tex`：正文单一真相来源
- `references/refs.bib`：BibTeX 数据库
- `artifacts/reference.docx`：DOCX 样式模板
- `artifacts/manuscript.csl`：参考文献样式
- `scripts/paper_build.py`：项目级最薄 wrapper
- `*.code-workspace`、`.vscode/settings.json`、`scripts/latex_workshop_build.lua`

## 标准目录形态

```text
projects/paper-foo/
├── main.tex
├── README.md
├── AGENTS.md
├── CLAUDE.md
├── paper-foo.code-workspace
├── .vscode/settings.json
├── scripts/
│   ├── paper_build.py
│   └── latex_workshop_build.lua
├── extraTex/
│   ├── front/
│   ├── body/
│   └── back/
├── references/
│   └── refs.bib
└── artifacts/
    ├── reference.docx
    └── manuscript.csl
```

## 入口契约

### `main.tex`

标准 `main.tex` 应满足：

- 使用常规文档类，例如 `article`
- 通过 `\usepackage{bensz-paper}` 接入公共包
- 通过 `\BenszPaperSetup{template = ...}` 选择模板 profile
- 用 `\input{extraTex/...}` 明确正文顺序
- 通过 `\addbibresource{references/refs.bib}` 接入 BibLaTeX 数据源

当前标准项目遵循：

```latex
\documentclass[12pt,a4paper]{article}
\usepackage{bensz-paper}
\BenszPaperSetup{template = paper-sci-01}
\addbibresource{references/refs.bib}
\begin{document}
\input{extraTex/...}
...
\end{document}
```

### `extraTex/**/*.tex`

这是 SCI 模板最重要的标准：

- `extraTex/**/*.tex` 是 PDF 和 DOCX 的唯一正文真相来源
- `main.tex` 中的 `\input` 顺序，就是 DOCX 导出时的正文顺序
- 不要再维护一份持久化 Markdown 正文副本

`packages/bensz-paper/scripts/manuscript_tool.py` 会直接读取 `main.tex` 中出现的 `\input{extraTex/...}` 顺序，然后把同一批 `.tex` 片段在运行期转换为 DOCX。

### `artifacts/`

一个标准的 SCI 项目，通常需要：

- `artifacts/reference.docx`：Word 输出的样式基线
- `artifacts/manuscript.csl`：引用样式控制

它们属于项目级交付契约，不应该被省略。

## 新增 SCI 模板时，应该改哪里

### 只改项目层的场景

如果你只是：

- 改示例正文
- 改章节组织
- 换参考文献数据
- 换 `reference.docx` 或 `.csl`

优先改 `projects/paper-*`

### 需要改公共包的场景

如果你要：

- 新增一个新的论文 profile
- 改共享版心、字体、标题体系、review mode
- 改 DOCX 导出逻辑
- 改包安装或统一构建逻辑

优先改 `packages/bensz-paper/`

新增一个新模板，通常至少要补齐：

- `packages/bensz-paper/profiles/bml-profile-<template>.def`
- 必要时扩展 `bml-*.sty`
- 一个新的 `projects/paper-*/` 示例项目

## 官方构建与校验

标准构建命令：

```bash
python packages/bensz-paper/scripts/paper_project_tool.py build --project-dir projects/paper-sci-01
```

这条命令默认产出：

- `main.pdf`
- `main.docx`
- `.latex-cache/`

如果只打开单项目目录，标准 wrapper 是：

```bash
python scripts/paper_build.py
```

## 不符合标准的常见做法

- 重新引入持久化正文 Markdown 副本
- 让 DOCX 来自另一份独立内容源，而不是 `extraTex/**/*.tex`
- 把共享样式写回单个项目
- 在项目里私自复制公共包文件
- 绕过 `paper_project_tool.py`，只验证 PDF 不验证 DOCX

## 贡献者检查清单

1. `main.tex` 是否只承担“装配顺序”职责
2. `extraTex/**/*.tex` 是否仍是唯一正文真相来源
3. `artifacts/reference.docx` 与 `artifacts/manuscript.csl` 是否齐全
4. 新样式是否应该沉淀到 `packages/bensz-paper/`
5. 是否通过官方入口同时产出了 `main.pdf` 与 `main.docx`
