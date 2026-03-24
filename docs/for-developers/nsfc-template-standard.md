# NSFC 模板标准

本文档描述当前仓库里 NSFC 模板的标准形态。它基于以下真实项目和源码整理：

- `projects/NSFC_General/`
- `projects/NSFC_Local/`
- `projects/NSFC_Young/`
- `packages/bensz-nsfc/`
- `packages/bensz-fonts/`

## 标准目标

一个标准的 NSFC 项目，应当同时满足这几件事：

- 项目层是薄封装，只维护正文内容、项目级参数和最薄构建入口
- 共享版式、共享宏、共享 BibTeX 样式和共享字体接入都放在 `packages/bensz-nsfc/` 与 `packages/bensz-fonts/`
- 本地开发、单项目使用和 VS Code 自动构建都走同一条官方链路
- 最终根目录只保留 `main.pdf`，中间文件进入 `.latex-cache/`

## 真实分层

### 公共包负责什么

`packages/bensz-nsfc/` 负责：

- `bensz-nsfc-common.sty`：公共入口
- `bensz-nsfc-core.sty`：`type=general|local|young` 解析、profile 加载、实现分发
- `profiles/`：不同项目类型的默认参数
- `impl/`：已稳定的模板实现
- `scripts/`：安装、构建、校验、TDS 打包

`packages/bensz-fonts/` 负责：

- 共享字体文件
- 统一字体路径 API
- 为 NSFC 公共包提供字体解析能力

### 项目负责什么

`projects/NSFC_*` 负责：

- `main.tex`：正文结构与 `\input` 顺序
- `extraTex/@config.tex`：项目级参数面板和公共包入口
- `extraTex/*.tex`：章节内容
- `references/`：项目参考文献入口和 `.bib`
- `figures/`：项目图片
- `scripts/nsfc_build.py`：项目级最薄 wrapper
- `*.code-workspace`、`.vscode/settings.json`、`scripts/latex_workshop_build.lua`

## 标准目录形态

一个标准的 NSFC 项目，至少应包含：

```text
projects/NSFC_Foo/
├── main.tex
├── README.md
├── AGENTS.md
├── CLAUDE.md
├── NSFC_Foo.code-workspace
├── .vscode/settings.json
├── scripts/
│   ├── nsfc_build.py
│   └── latex_workshop_build.lua
├── extraTex/
│   ├── @config.tex
│   └── *.tex
├── references/
│   ├── reference.tex
│   └── *.bib
├── figures/
└── template/             # 推荐：可公开分发的 Word/PDF 基线资料
```

其中真正决定“是不是标准模板”的关键文件是：

- `main.tex`
- `extraTex/@config.tex`
- `references/reference.tex`
- `scripts/nsfc_build.py`
- `.vscode/settings.json`

## 入口契约

### `main.tex`

`main.tex` 应承担这些职责：

- 使用 `ctexart`
- 在导言区通过 `\input{extraTex/@config.tex}` 接入公共包
- 按官方提纲组织章节和 `\input` 顺序
- 不把大段公共样式直接写回项目

当前标准项目都遵循：

```latex
\documentclass[...]{ctexart}
\input{extraTex/@config.tex}
\begin{document}
...
\input{extraTex/...}
...
\end{document}
```

### `extraTex/@config.tex`

这是 NSFC 项目的核心入口文件。标准要求：

- 必须通过 `\usepackage[type=...]{bensz-nsfc-common}` 接入公共包
- 必须把项目允许调整的参数集中在这里
- 不应把整份公共样式实现重新复制到项目层

当前三套 NSFC 项目虽然参数细节不同，但都遵循同一个模型：

1. profile 默认值来自 `packages/bensz-nsfc/profiles/`
2. 项目级参数在 `extraTex/@config.tex` 覆盖
3. 最终稳定实现仍来自 `packages/bensz-nsfc/impl/`

### `references/reference.tex`

标准用法是把参考文献渲染入口单独放在 `references/reference.tex`，让正文结构和参考文献格式控制解耦。这里通常负责：

- 标题展示
- 参考文献间距微调
- `\bibliographystyle` 与 `\bibliography`

## 新增 NSFC 模板时，应该改哪里

### 只改项目层的场景

如果你只是：

- 改示例正文
- 换示例图片
- 调整当前项目特有的参数默认值
- 补项目 README / wrapper / VS Code 文件

优先改 `projects/NSFC_*`

### 需要改公共包的场景

如果你要：

- 新增一个新的 NSFC 类型
- 改共享标题样式、共享页面版心、共享参考文献逻辑
- 改共享字体解析、共享 `bst` 资源、共享宏
- 改构建与安装逻辑

优先改 `packages/bensz-nsfc/`

新增一种新 NSFC 类型，通常至少要补齐：

- `packages/bensz-nsfc/profiles/bensz-nsfc-profile-<type>.def`
- `packages/bensz-nsfc/impl/bensz-nsfc-<type>.tex` 或复用/扩展现有实现
- 一个新的 `projects/NSFC_<Type>/` 项目薄封装

## 官方构建与校验

项目验证优先用：

```bash
python packages/bensz-nsfc/scripts/nsfc_project_tool.py build --project-dir projects/NSFC_General
```

公共包变更后，优先再跑：

```bash
python packages/bensz-nsfc/scripts/validate_package.py
```

如果新增或调整了 VS Code 项目文件，补跑：

```bash
python scripts/sync_vscode_configs.py
```

## 不符合标准的常见做法

- 把共享样式直接复制回 `projects/NSFC_*`
- 不用 `bensz-nsfc-common`，改成项目里各自维护一套样式
- 绕过 `scripts/nsfc_build.py` 和 `nsfc_project_tool.py`，只依赖手写命令
- 把中间文件散落回根目录
- 在项目里重新复制共享字体和共享 `bst`
- 修改官方提纲标题文字，导致与 Word 模板承诺不一致

## 贡献者检查清单

1. `main.tex` 是否仍是“结构入口”，而不是重新塞满样式代码
2. `extraTex/@config.tex` 是否仍是唯一项目级参数面板
3. 新改动是否应该提升到 `packages/bensz-nsfc/`
4. 是否保留了 `scripts/nsfc_build.py`、`.vscode/settings.json`、`*.code-workspace`
5. 是否通过 `nsfc_project_tool.py` 成功构建
