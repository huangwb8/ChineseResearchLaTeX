---
name: transfer-old-latex-to-new
version: 2.0.0
description: 当用户明确要求“迁移 LaTeX 模板”“把旧项目接入 ChineseResearchLaTeX”“把旧标书/论文/毕业论文/简历套进当前模板”“把 Word/PDF/Markdown/零散 tex 整理进现有项目”“跨产品线迁移或重构当前模板”，或直接提到 `transfer-old-latex-to-new` 时使用。旧别名 `migrating-latex-templates` 可兼容理解，但当前统一名称是 `transfer-old-latex-to-new`。让 AI 基于仓库当前 packages/ 与 projects/ 真实结构，自主判断目标产品线、接收任意类型输入材料、决定需要修改或生成的文件与交付物；不要要求用户先整理成固定的 old/new 目录或固定输出清单。
author: Bensz Conan
metadata:
  author: Bensz Conan
  short-description: ChineseResearchLaTeX 模板迁移与重构编排
  keywords:
    - latex
    - template migration
    - repository adaptation
    - nsfc
    - paper
    - thesis
    - cv
    - ChineseResearchLaTeX
  triggers:
    - 迁移模板
    - 旧项目接入 ChineseResearchLaTeX
    - 把旧标书套进新模板
    - 把旧论文迁移到当前模板
    - 毕业论文模板迁移
    - 简历模板迁移
    - 跨产品线迁移
dependencies:
  - python: ">=3.8"
  - scripts/run.py
  - scripts/core/
entry_point: python skills/transfer-old-latex-to-new/scripts/run.py
config: skills/transfer-old-latex-to-new/config.yaml
references: skills/transfer-old-latex-to-new/references/
---

# ChineseResearchLaTeX 模板迁移与重构

这个 skill 的目标，已经不再是“把旧版 NSFC 标书机械搬到新版目录里”。

现在它的默认心智是：

- 面向 **当前 ChineseResearchLaTeX 仓库的真实分层** 工作
- 面向 **NSFC / SCI 论文 / 毕业论文 / CV** 四条已落地产品线工作
- 面向 **任意类型输入材料** 工作
- 以“**按要求做出好的模板或项目**”为第一目标，而不是守着固定输入输出协议

## 与当前仓库结构对齐

处理任务时，先判断目标落在哪条产品线，再决定改 `packages/` 还是改 `projects/`：

- NSFC：`packages/bensz-nsfc/` + `projects/NSFC_*`
- SCI 论文：`packages/bensz-paper/` + `projects/paper-sci-01/`
- 毕业论文：`packages/bensz-thesis/` + `projects/thesis-*`
- 简历：`packages/bensz-cv/` + `projects/cv-01/`

如果问题本质上是共享样式、共享脚本、共享资源或公共接口问题，优先改 `packages/`。

如果问题本质上是具体示例项目、正文内容、项目入口、`template.json`、README 或公开演示资产问题，优先改 `projects/`。

不要再默认把 `projects/` 理解成“只有 NSFC 三个壳项目”的旧结构。

## 输入原则

不要要求用户先把材料整理成固定格式。

这个 skill 应该默认接受并消化任意合理输入，例如：

- 一个完整旧项目目录
- 若干 `.tex` / `.bib` / `.cls` / `.sty` 文件
- Word、PDF、Markdown、txt、图片截图
- 一份官方模板、一个公开 baseline、一些零散说明文字
- 一个当前 `projects/*` 目录，加上一些“想变成什么样”的要求
- 多种输入混合出现

如果用户提供的信息不完整，不要立刻停下来追问“标准输入”。
先基于现有材料判断：

- 目标产品线是什么
- 目标层级是 `packages/` 还是 `projects/`
- 缺的到底是关键输入，还是只是可由 AI 自主补位的细节

只有当缺失信息会直接导致高风险误改时，才请求用户补充。

## 输出原则

不要预设固定输出目录、固定报告集合或固定交付物清单。

输出由 AI 根据任务自主决定，可以是：

- 直接把目标项目改到可用状态
- 新增或重写 `extraTex/*.tex`
- 调整 `main.tex`、wrapper、README、`template.json`
- 迁移共享样式到 `packages/`
- 生成必要的对照说明、迁移备忘、风险清单、验收记录
- 在需要时补充中间工作区或测试产物

关键不是“必须产出哪些文件”，而是“最终是否把目标模板或项目做对、做稳、做得可维护”。

## 默认行为

- 默认把用户给的原始材料视为只读，除非用户明确要求原地改写
- 默认尊重仓库当前真实结构，不沿用旧计划文档中的过时约定
- 默认优先选择最短、最稳的迁移路径，而不是保留旧结构包袱
- 默认允许 AI 为了做出更好的模板而重组文件、入口和落层
- 默认只在必要时生成中间文件，并尽量放入任务专属工作区或现有缓存目录

## 推荐工作流

### 1. 识别目标

先回答三个问题：

- 用户到底想得到哪个产品线的结果
- 这次任务是“内容迁移”“模板接入”“结构重构”“样式复刻”还是“公共包沉淀”
- 最终交付应该优先看“能构建”“像目标样式”“结构清晰”“便于后续维护”中的哪几个

### 2. 清点输入

从已有输入里提炼：

- 可直接复用的正文、图表、参考文献、元数据
- 必须保留的版式特征
- 可以丢弃的旧脚手架或历史兼容层
- 仓库当前是否已经存在更合适的目标项目

### 3. 决定落层

遵循以下判断：

- 共享问题进 `packages/`
- 示例项目问题进 `projects/`
- 构建/安装/验证问题进对应 `scripts/`
- 文档与使用口径问题同步 README / CHANGELOG / 项目说明

### 4. 自主迁移或重构

允许以下动作：

- 从旧材料中抽取正文和资源，落到当前标准项目结构
- 把旧模板的局部能力重写成当前公共包风格
- 为 thesis 项目补 `template.json`
- 为项目补 `README`、wrapper、基线入口或验收说明
- 视需要对目标项目做结构收敛，而不是一比一照搬旧目录

### 5. 官方入口验证

迁移或重构完成后，尽量用对应产品线的官方入口验证：

- NSFC：`python packages/bensz-nsfc/scripts/nsfc_project_tool.py build --project-dir <项目路径>`
- SCI：`python packages/bensz-paper/scripts/paper_project_tool.py build --project-dir <项目路径>`
- Thesis：`python packages/bensz-thesis/scripts/thesis_project_tool.py build --project-dir <项目路径>`
- CV：`python packages/bensz-cv/scripts/cv_project_tool.py build --project-dir <项目路径> --variant all`

如果任务本身不是构建类任务，也至少要做结构一致性和路径一致性自检。

## 不要再强加的旧约束

以下做法不再是这个 skill 的默认要求：

- 不再要求必须有“旧项目目录 + 新项目目录”两份输入
- 不再要求输出必须放在 `skills/transfer-old-latex-to-new/runs/<run_id>/`
- 不再要求只能修改 `extraTex/*.tex`
- 不再把 NSFC 当成唯一主场景
- 不再把“分析 → apply → compile → restore”的 CLI 流程当成唯一工作流

如果某次任务刚好适合这些旧流程，可以用；但默认不要被它们绑住。

## Legacy CLI 的定位

`scripts/run.py`、`scripts/migrate.sh` 仍然保留。

它们适合这类场景：

- 已经有清晰的 old/new 两个目录
- 任务仍然是经典的旧版 LaTeX 项目迁移
- 需要可追溯的 `runs/` 输出

但这些脚本现在只是 **可选硬编码后备**，不是这个 skill 的主心智。

如果你只是想完成一次真实迁移任务，优先按用户目标和仓库现状自主做对，不要为了迁就脚本而反过来限制任务。

## 参考材料

优先阅读本文件。

只有在你明确需要旧 CLI 说明时，再查看：

- `scripts/README.md`
- `references/quickstart.md`
- `references/config_guide.md`
- `references/api_reference.md`

这些文档主要服务 legacy CLI，用来补充命令细节，不应覆盖本文件的主原则。
