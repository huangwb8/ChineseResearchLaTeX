# 学术简历模板标准

本文档描述当前仓库里学术简历模板的标准形态。它基于以下真实项目和源码整理：

- `projects/cv-01/`
- `packages/bensz-cv/`
- `packages/bensz-fonts/`

## 标准目标

一个标准的 CV 项目，应当满足：

- 同一项目内同时维护中文和英文两个入口
- 公共版式、类文件、字体与图标支持放在 `packages/bensz-cv/`
- 项目层只维护公开示例内容、头像、引用数据和最薄构建入口
- 构建统一走 `cv_project_tool.py`

## 真实分层

### 公共包负责什么

`packages/bensz-cv/` 负责：

- `bensz-cv.cls`：公共入口类
- `resume.cls`：底层样式与兼容入口
- `fontawesome.sty`、`zh_CN-*.sty`、`Noto*.sty`：字体和图标支持
- `profiles/`：项目 profile
- `scripts/cv_project_tool.py`：构建、清理、像素级比较

`packages/bensz-fonts/` 负责共享字体接入。

### 项目负责什么

`projects/cv-01/` 负责：

- `main-zh.tex`：中文简历入口
- `main-en.tex`：英文简历入口
- `assets/avatar.jpg`：公开演示头像
- `references/`：演示引用
- `scripts/cv_build.py`：项目级最薄 wrapper
- `*.code-workspace`、`.vscode/settings.json`、`scripts/latex_workshop_build.lua`

## 标准目录形态

```text
projects/cv-foo/
├── main-zh.tex
├── main-en.tex
├── README.md
├── AGENTS.md
├── CLAUDE.md
├── cv-foo.code-workspace
├── .vscode/settings.json
├── scripts/
│   ├── cv_build.py
│   └── latex_workshop_build.lua
├── assets/
│   └── avatar.jpg
└── references/
    └── *.bib
```

## 入口契约

### 双入口文件名是固定约定

当前 `packages/bensz-cv/scripts/cv_project_tool.py` 直接使用固定映射：

- `zh -> main-zh.tex`
- `en -> main-en.tex`

因此，一个标准 CV 项目应保留这两个入口文件名；如果随意改名，就会破坏当前官方构建链路的默认假设。

### `main-zh.tex` / `main-en.tex`

标准入口应满足：

- 使用 `\documentclass{bensz-cv}`
- 在项目层加载必要的图片、表格、图标或中文字体支持宏包
- 直接维护中英文两套公开内容

其中共享版式来自公共包，项目层负责内容本身，不负责复制类文件实现。

## 公共示例内容标准

CV 项目与其他产品线相比，有一个额外硬约束：

- `projects/cv-*` 中只能保留去隐私后的公开演示内容
- 头像、联系方式、教育经历、GitHub、ORCID、引用都应可公开分享或是明确的演示数据

当前 `cv-01` 的标准做法是：

- 用公开演示人物设定
- 用虚构联系方式和 synthetic bibliography
- 把像素级验收放在私有阶段完成，公开仓库只保留去隐私后的最终示例

## 新增 CV 模板时，应该改哪里

### 只改项目层的场景

如果你只是：

- 改双语内容
- 换公开头像
- 补参考文献条目
- 改项目 README / wrapper / workspace

优先改 `projects/cv-*`

### 需要改公共包的场景

如果你要：

- 改共享类文件
- 改共享字体、图标、中文支持方案
- 改统一构建或 compare 能力
- 引入新的公共 profile

优先改 `packages/bensz-cv/`

## 官方构建与验收

标准构建命令：

```bash
python packages/bensz-cv/scripts/cv_project_tool.py build --project-dir projects/cv-01 --variant all
```

版式回归时，可使用：

```bash
python packages/bensz-cv/scripts/cv_project_tool.py compare --project-dir projects/cv-01 --variant zh --baseline-pdf <baseline.pdf>
```

如果只打开单项目目录，标准 wrapper 是：

```bash
python scripts/cv_build.py
```

## 不符合标准的常见做法

- 把类文件、字体文件或共享样式复制回项目目录
- 修改入口文件名，导致官方构建器找不到 `main-zh.tex` / `main-en.tex`
- 在公开项目里残留真实简历内容、真实头像或真实联系方式
- 只维护中文或只维护英文，不再保持双入口

## 贡献者检查清单

1. 是否保留了 `main-zh.tex` 和 `main-en.tex`
2. 是否仍使用 `\documentclass{bensz-cv}`
3. 项目中是否只包含公开可分享的演示内容
4. 新样式是否应该沉淀到 `packages/bensz-cv/`
5. 是否通过 `cv_project_tool.py build --variant all`
