---
name: transfer-old-latex-to-new
version: 2.1.0
description: 当用户明确要求“迁移 LaTeX 模板”“把旧项目接入 ChineseResearchLaTeX”“把旧标书/论文/毕业论文/简历套进当前模板”“把 Word/PDF/Markdown/零散 tex 整理进现有项目”，或直接提到 `transfer-old-latex-to-new` 时使用。旧别名 `migrating-latex-templates` 可兼容理解。该 skill 只负责把正文内容迁移到当前仓库现有模板的内容层；绝不能修改 `packages/` 内公共包源码、也绝不能修改 `projects/` 内模板样式或入口骨架，只能写入目标项目允许承载正文的内容文件。
author: Bensz Conan
metadata:
  author: Bensz Conan
  short-description: ChineseResearchLaTeX 内容层迁移编排
  keywords:
    - latex
    - content migration
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
dependencies:
  - python: ">=3.8"
  - scripts/run.py
  - scripts/core/
entry_point: python skills/transfer-old-latex-to-new/scripts/run.py
config: skills/transfer-old-latex-to-new/config.yaml
references: skills/transfer-old-latex-to-new/references/
---

# ChineseResearchLaTeX 内容迁移技能

这个 skill 的职责已经收敛为一件事：

- 把旧材料里的正文、参考文献等内容，迁移到 **当前仓库已经存在的模板项目** 的内容层

它**不是**模板开发技能，也**不是**公共包重构技能。

如果用户要改模板源码、改样式、改 `packages/bensz-*`、改 `projects/*` 里的模板骨架、wrapper、`main.tex`、`@config.tex`、`.cls`、`.sty`、profile、style、构建脚本，请改用 `make-latex-model` 或对应产品线的模板开发工作流。

## 硬性边界

处理任务时，必须始终遵守以下约束：

- 绝不能修改 `packages/` 下任何公共包源码、模板实现、profile、style、脚本或共享资源
- 绝不能修改 `projects/` 下任何模板样式、入口骨架、wrapper、`main.tex`、`extraTex/@config.tex`、`.cls`、`.sty`、Lua/Python 构建脚本
- 只能把内容放到目标项目已有的内容层位置
- 如果现有模板没有合适承载位点，不能为了容纳内容去改模板；应明确报告“模板位点不足，需要模板开发 skill 介入”

在当前仓库里，默认可写的内容层只有：

- `extraTex/**/*.tex`（排除 `extraTex/@config.tex`）
- `references/**/*.bib`

除非未来该 skill 的配置白名单明确放开，否则其它路径一律视为只读。

## 与当前仓库结构对齐

这个 skill 仍然需要识别目标产品线，但目的不再是判断“该不该改 `packages/`”。

它真正要做的是：

- NSFC：选择合适的 `projects/NSFC_*`
- SCI 论文：选择 `projects/paper-sci-01/`
- 毕业论文：选择最接近的 `projects/thesis-*`
- 简历：选择 `projects/cv-01/`

然后把旧材料中的正文内容映射到这些**现成项目**的内容文件里。

## 输入原则

不要要求用户先整理成固定输入协议。

本 skill 应该默认接受并消化任意合理输入，例如：

- 一个完整旧项目目录
- 若干 `.tex` / `.bib` / `.docx` / `.md` / `.txt`
- PDF、截图、图片
- 一份已有模板项目路径，加上一些迁移目标说明
- 多种输入混合出现

如果材料不完整，不要先追问“标准输入”。

先判断：

- 目标产品线是什么
- 哪个现有项目最适合作为承载容器
- 哪些内容能直接落入 `extraTex/*.tex` 或 `references/*.bib`
- 哪些诉求超出内容迁移边界，必须交给模板开发流程

只有缺失信息会导致把正文放错位置时，才请求补充。

## 输出原则

不要把输出理解成“任意重构仓库”。

本 skill 的有效输出通常只有这些：

- 把正文迁移到目标项目的 `extraTex/*.tex`
- 把参考文献迁移到目标项目的 `references/*.bib`
- 生成必要的迁移说明、风险提示、未落位清单
- 在构建成功后给出验证结果

不要默认输出：

- 模板源码改动
- 样式修复
- wrapper / `main.tex` / `template.json` / README 的结构重写
- 公共包抽取或包级能力沉淀

这些都超出本 skill 的边界。

## 默认行为

- 默认把用户原始材料视为只读，除非用户明确要求原地改写
- 默认把目标模板视为只读骨架，只允许写内容层
- 默认优先选择最接近的现有项目，而不是新建或重组模板结构
- 默认不为了“更像旧样式”去改当前模板；样式差异要报告，不要偷改
- 默认把资源复制、模板补洞、入口调整视为高风险动作，除非配置白名单和用户要求都明确允许

## 推荐工作流

### 1. 识别目标产品线与承载项目

先回答三个问题：

- 用户最终要落到哪条产品线
- 当前仓库哪个现有项目最适合作为承载容器
- 这次任务是“内容迁移”还是其实已经变成“模板开发”

如果已经变成模板开发，立即切换思路，不要继续把它伪装成内容迁移任务。

### 2. 清点可迁移内容

从输入中提炼：

- 可直接复用的正文段落
- 可直接复用的 BibTeX
- 需要人工确认的缺口
- 会触发模板改动需求的超界诉求

### 3. 做内容层映射

只在内容层做映射：

- 旧正文 → `extraTex/*.tex`
- 旧参考文献 → `references/*.bib`

不要把“映射”理解成：

- 改章节命令
- 改模板标题样式
- 改目录/封面/页眉页脚
- 改公共包接口

### 4. 执行迁移

执行时只允许：

- 覆盖目标内容文件
- 新建目标内容文件（若模板已有对应承载位点）
- 写入或补齐 `.bib`

如果某项需求必须改模板骨架才能完成：

- 不要继续自动修改
- 明确标出受阻位置和原因
- 建议改用 `make-latex-model`

### 5. 官方入口验证

迁移完成后，尽量用对应产品线的官方入口验证：

- NSFC：`python packages/bensz-nsfc/scripts/nsfc_project_tool.py build --project-dir <项目路径>`
- SCI：`python packages/bensz-paper/scripts/paper_project_tool.py build --project-dir <项目路径>`
- Thesis：`python packages/bensz-thesis/scripts/thesis_project_tool.py build --project-dir <项目路径>`
- CV：`python packages/bensz-cv/scripts/cv_project_tool.py build --project-dir <项目路径> --variant all`

如果构建失败且原因来自模板骨架缺口，不要私自修模板；应如实报告。

## Legacy CLI 的定位

`scripts/run.py`、`scripts/migrate.sh` 仍然保留，但只作为经典 old/new 目录迁移的后备入口。

即使使用 legacy CLI，也必须继续遵守本文件的硬性边界：

- 旧项目可以读
- 新项目只能写内容层
- 不得借 CLI 绕过模板保护

## 不适用场景

以下场景不要继续使用本 skill 直接落地：

- 用户要“做一个新模板”
- 用户要“把旧样式 1:1 复刻到当前仓库”
- 用户要改 `packages/bensz-*`
- 用户要改 `projects/*` 里的模板入口或样式文件
- 用户要新增模板承载位点、封面结构、目录结构、profile、class、style

这些都应转交模板开发链路。

## 参考材料

优先阅读本文件。

需要 legacy CLI 细节时，再查看：

- `scripts/README.md`
- `references/quickstart.md`
- `references/config_guide.md`
- `references/api_reference.md`

需要确认迁移边界时，优先遵循：

- “只迁移内容，不改模板骨架”
- “样式差异只报告，不偷改”
