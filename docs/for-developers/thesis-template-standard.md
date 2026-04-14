# 毕业论文模板标准

本文档描述当前仓库里毕业论文模板的标准形态。它基于以下真实项目和源码整理：

- `projects/thesis-smu-master/`
- `projects/thesis-nju-master/`
- `projects/thesis-smu-postdoc/`
- `projects/thesis-sysu-doctor/`
- `projects/thesis-ucas-doctor/`
- `packages/bensz-thesis/`
- `packages/bensz-fonts/`

## 标准目标

一个标准的毕业论文项目，应当满足：

- 项目层只维护正文、元信息、公开素材和最薄入口
- 学校/学位差异通过 `packages/bensz-thesis/` 中的 profile + style 表达
- 项目根目录必须有可机读元数据 `template.json`
- 构建统一走 `thesis_project_tool.py`

## 真实分层

### 公共包负责什么

`packages/bensz-thesis/` 负责：

- `bensz-thesis.sty`：公共入口
- `bthesis-core.sty`：`template=...` 解析、profile 加载、style 分发
- `profiles/`：模板标识与 style 文件映射
- `styles/`：学校/学位模板的稳定实现
- `scripts/thesis_project_tool.py`：构建、清理、像素级比较

`packages/bensz-fonts/` 负责共享字体接入。

### 项目负责什么

`projects/thesis-*` 负责：

- `main.tex`：论文结构
- 可选的 `baseline.tex`：仅当需要保留只读公开基线直通时使用
- `extraTex/`：前置配置、元信息、章节正文、附录等
- `template.json`：项目元数据
- `references/`、`bibtex-style/`、`assets/`、`figures/`：项目资源
- `scripts/thesis_build.py`：项目级最薄 wrapper
- `*.code-workspace`、`.vscode/settings.json`、`scripts/latex_workshop_build.lua`

## 标准目录形态

```text
projects/thesis-school-degree/
├── main.tex
├── README.md
├── AGENTS.md
├── CLAUDE.md
├── template.json
├── thesis-school-degree.code-workspace
├── .vscode/settings.json
├── scripts/
│   ├── thesis_build.py
│   └── latex_workshop_build.lua
├── extraTex/
│   └── ...
├── references/          # 使用 biblatex/biber 时常见
├── bibtex-style/        # 使用 bibtex 时常见
├── figures/
└── assets/
```

## 入口契约

### `main.tex`

标准 `main.tex` 应满足：

- 仍然是项目根入口
- 在导言区通过 `extraTex/@config.tex` 或 `extraTex/config-pre.tex` 接入 `bensz-thesis`
- 章节、摘要、附录、致谢等按项目需要用 `\input` 组织

当前 thesis / postdoc 项目虽然细节不同，但都遵循同一条核心约定：

```latex
\usepackage{bensz-thesis}
\BenszThesisSetup{template=...}
```

只是入口文件名不同：

- `thesis-smu-master`：`extraTex/@config.tex`
- `thesis-nju-master`：`extraTex/@config.tex`（`main.tex` 为默认可编辑入口，额外提供 `baseline.tex` 公开基线验收入口与 `editable.tex` 兼容别名）
- `thesis-smu-postdoc`：`extraTex/config-pre.tex`
- `thesis-sysu-doctor`：`extraTex/config-pre.tex`
- `thesis-ucas-doctor`：`extraTex/config-pre.tex`

### `template.json`

这是 thesis 项目独有且强制的标准文件。当前至少必须包含：

```json
{
  "project_name": "thesis-smu-master",
  "school": "南方医科大学",
  "degree": "master"
}
```

约束如下：

- `project_name` 必须与目录名一致
- `school` 使用院校名称
- `degree` 目前只允许：`bachelor`、`master`、`doctor`、`postdoc`

如果新增、复制、重命名 thesis 项目，没有同步更新 `template.json`，就不符合当前标准。

### `profiles/` 与 `styles/`

新增一套毕业论文模板，不应该只复制一个项目目录结束。标准做法是：

1. 在 `packages/bensz-thesis/profiles/` 新增一个 profile
2. 在 `packages/bensz-thesis/styles/` 新增或复用一个 style 实现
3. 在 `projects/` 下增加一个与之对应的薄项目

也就是说，学校/学位模板的“真正模板身份”定义在包级，不在项目级。

## 新增 thesis 模板时，应该改哪里

### 只改项目层的场景

如果你只是：

- 改公开演示正文
- 换公开图表和素材
- 补 README / wrapper / workspace
- 调整某个项目自己的章节组织

优先改 `projects/thesis-*`

### 需要改公共包的场景

如果你要：

- 新增一所学校或一种学位模板
- 改共享的 style 装配逻辑
- 改公共字体接入、共享页眉页脚、共享标题策略
- 改统一构建、清理、compare 行为

优先改 `packages/bensz-thesis/`

## 官方构建与验收

标准构建命令：

```bash
python packages/bensz-thesis/scripts/thesis_project_tool.py build --project-dir projects/thesis-smu-master
```

版式回归时，可使用：

```bash
python packages/bensz-thesis/scripts/thesis_project_tool.py compare --project-dir projects/thesis-smu-master --baseline-pdf <baseline.pdf>
```

如果只打开单项目目录，标准 wrapper 是：

```bash
python scripts/thesis_build.py
```

## 不符合标准的常见做法

- 只复制现有 thesis 项目，不补包级 `profile` / `style`
- 新增 thesis 项目却没有 `template.json`
- `template.json` 中 `project_name` 与目录名不一致
- `degree` 使用自由文本，而不是 `bachelor|master|doctor`
- 把共享样式写回单个项目
- 把私有论文正文、私有图表或私有对比图留在公开项目

## 贡献者检查清单

1. 我新增的是“项目示例”，还是“一个新的学校/学位模板能力”
2. 如是新模板能力，是否补齐了包级 `profile` 和 `style`
3. `template.json` 是否存在且字段完整
4. 项目是否仍是薄封装，而不是复制了一套完整样式实现
5. 是否通过 `thesis_project_tool.py build`，必要时通过 `compare`
