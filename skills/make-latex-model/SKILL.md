---
name: make-latex-model
version: 3.1.2
author: Bensz Conan
metadata:
  author: Bensz Conan
maintainer: project-maintainers
status: stable
category: normal
description: 当用户明确要求“LaTeX 模板优化”“样式参数对齐”“像素级比对”“make-latex-model”或旧写法“make_latex_model”，或要把 ChineseResearchLaTeX 里的某个项目做成高质量模板时使用。适配 NSFC / paper / thesis / cv 四条产品线；先依据 packages/ 与 projects/ 的真实分层判断改项目层还是公共包，再用各产品线官方构建入口验收。若必须修改 packages 下公共包，需先生成受影响模板回归计划并完成相关回归；NSFC 专项工具仅在明确属于 NSFC 参数对齐场景时按需使用。
tags:
  - latex
  - template
  - optimization
  - nsfc
  - paper
  - thesis
  - cv
  - pdf-analysis
  - visual-regression
dependencies:
  python: ">=3.8"
  packages:
    - name: PyMuPDF
      version: ">=1.23.0"
      purpose: PDF 样式参数提取
    - name: python-docx
      version: ">=0.8.11"
      purpose: Word 标题提取（可选）
    - name: Pillow
      version: ">=9.0.0"
      purpose: 图像处理和像素对比
    - name: PyYAML
      version: ">=6.0"
      purpose: 配置文件解析
requires:
  - xelatex
  - bibtex
compatibility:
  platforms:
    - macos
    - windows
    - linux
  latex_templates:
    - nsfc
    - paper
    - thesis
    - cv
    - generic
changelog: CHANGELOG.md
---

# ChineseResearchLaTeX 模板落地与高保真对齐器

## 与 bensz-collect-bugs 的协作约定

- 当用户环境中出现因本 skill 设计缺陷导致的 bug 时，优先使用 `bensz-collect-bugs` 按规范记录到 `~/.bensz-skills/bugs/`，严禁直接修改用户本地 Claude Code / Codex 中已安装的 skill 源码。
- 若 AI 仍可通过 workaround 继续完成用户任务，应先记录 bug，再继续完成当前任务。
- 当用户明确要求“report bensz skills bugs”等公开上报动作时，调用本地 `gh` 与 `bensz-collect-bugs`，仅上传新增 bug 到 `huangwb8/bensz-bugs`；不要 pull / clone 整个 bug 仓库。

## 先读什么

- 当前仓库分层与产品线标准：
  - `docs/for-developers/nsfc-template-standard.md`
  - `docs/for-developers/paper-template-standard.md`
  - `docs/for-developers/thesis-template-standard.md`
  - `docs/for-developers/cv-template-standard.md`
- 本 skill 的执行口径：`skills/make-latex-model/docs/WORKFLOW.md`
- 产品线判定与初始化规则：`skills/make-latex-model/references/PRODUCT_LINE_RULES.md`
- 脚本职责矩阵：`skills/make-latex-model/references/SCRIPT_SCOPE.md`
- 本 skill 的辅助脚本说明：`skills/make-latex-model/scripts/README.md`
- 如需从 Word 导出 PDF 基准：`skills/make-latex-model/docs/BASELINE_GUIDE.md`

## 核心定位

这个 skill 的目标是：

- 让 ChineseResearchLaTeX 里的目标项目按当前真实架构做成高质量模板
- 在 `projects/` 与 `packages/` 之间选对修改层级
- 若必须改 `packages/`，先识别所有直接受影响的现有模板并完成回归
- 在需要时做 PDF / Word / baseline 对齐
- 始终通过各产品线的官方构建入口验收

默认假设：

- `projects/` 现在更多是“薄封装示例项目”，不是旧时代那种把所有样式都堆在项目里的模板目录
- 共享能力优先沉淀到 `packages/bensz-*`
- 视觉基线可以来自官方 PDF、Word 导出 PDF、既有 baseline PDF、学校样例 PDF，或用户提供的验收 PDF

## 适用任务

- 把某个 `projects/*` 项目对齐到新的官方模板、Word 稿件或 baseline PDF
- 发现当前问题其实属于共享样式、profile、构建脚本，改到 `packages/bensz-*`
- 新增或重构 thesis / paper / cv / nsfc 模板时，帮助确定“项目层 vs 公共包层”边界
- 在需要时做像素级 PDF 比对、标题对齐、参数抽取、回归验收
- 把“按要求做出好模板”作为第一目标，而不是被某一种单一路径绑住

## 产品线判定

- 具体的产品线识别、初始化标记与官方命令矩阵见 `references/PRODUCT_LINE_RULES.md`
- 如果一个问题会影响多个项目共享的版式、字体接入、profile、统一构建逻辑或对齐策略，优先改 `packages/bensz-*`，不要把同一份逻辑复制回各个 `projects/*`

## 工作流

### 1. 先判断验收口径

优先问自己：

- 用户要的是“像某份 PDF/Word 一样”
- 还是“把现有项目做成符合当前仓库标准的好模板”
- 还是“新增一套学校 / 期刊 / 简历模板能力”

能拿来当基线的输入包括：

- 官方 PDF
- Word 导出 PDF
- 现有 baseline PDF
- 公开学校模板 PDF
- 已通过验收的旧版 PDF

### 2. 再判断修改层级

优先使用当前仓库的真实分层规则：

- `projects/*`：示例内容、薄封装入口、项目资源、局部项目差异
- `packages/bensz-*`：共享样式、共享字体、profile、统一构建逻辑

不要再默认认为“模板优化 = 只改 `main.tex` 标题 + `@config.tex` 参数”。

### 3. 最小范围实现

只改与当前任务直接相关的文件：

- NSFC：可改项目级参数、共享 impl/profile、必要的标题结构
- Paper：可改 `packages/bensz-paper/` 共享样式，也可改 `projects/paper-*/extraTex/**/*.tex` 的装配与版式相关内容；不要重新引入持久化 Markdown 正文副本
- Thesis：可改 `packages/bensz-thesis/styles/`、`profiles/`、项目级 `main.tex` / `baseline.tex` / `editable.tex` / `template.json` / `extraTex/`
- CV：可改 `packages/bensz-cv/` 共享样式，或项目级 `main-zh.tex` / `main-en.tex` / 公开演示资源

除非用户明确要求改正文语义内容，否则默认聚焦模板、版式、结构入口、构建链路和验收资产。

### 3.5 包层安全门禁

当你判断“这次必须改 `packages/`”时，额外执行以下动作：

1. 默认先证明项目层方案为什么不够；只有共享问题才升级到包层
2. 先运行 `python3 skills/make-latex-model/scripts/plan_package_regression.py <packages/bensz-*>`
3. 优先把改动收敛到最窄的模板专属 `profile / style / template` 文件
4. 只有在前述路径都不够时，才修改共享核心宏、公共入口或字体 API
5. 改完先验证当前目标项目，再回归该公共包直接覆盖的全部现有项目
6. 若某个受影响项目已有 baseline，优先补跑官方 compare；没有 compare 入口时至少完成官方 build

不要做这些事：

- 没有回归计划就直接改共享包
- 为了省事把共享逻辑复制回单个项目
- 在未验证其它现有模板前宣称“不会影响别的模板”

### 4. 官方入口验证

验证时，始终以当前官方构建链路为准：

- NSFC：`nsfc_project_tool.py`
- Paper：`paper_project_tool.py`
- Thesis：`thesis_project_tool.py`
- CV：`cv_project_tool.py`

如涉及共享包改动，再补跑对应公共包校验或 compare 流程。

### 5. 需要对比时再用辅助脚本

本 skill 自带的脚本现在是“辅助工具箱”，不是唯一工作流：

- `analyze_pdf.py`：提取 PDF 基线参数
- `compare_headings.py`：对比标题文本或格式
- `compare_pdf_pixels.py`：像素级 PDF 比对
- `optimize_heading_linebreaks.py`：按 PDF 基线优化标题换行
- `plan_package_regression.py`：为包层修改生成“受影响模板 + 官方回归命令”计划

这些工具对“单入口 + PDF 基线”场景尤其有用；其中部分脚本属于 NSFC 专项参数对齐工具，不应被拿来替代 `paper / thesis / cv` 的官方工作流。

## 修改边界

### 允许做的事

- 调整项目层版式参数、标题体系、入口装配
- 提升共享样式到 `packages/bensz-*`
- 增补或修正 profile / style / 构建 wrapper
- 在需要时修改 `main.tex`、`baseline.tex`、`editable.tex`、`main-zh.tex`、`main-en.tex`
- 使用 baseline PDF / Word 导出 PDF 做验收

### 不该做的事

- 把共享实现重新复制回单个项目
- 把 thesis / paper / cv 强行解释成“只有 `@config.tex` 才能改”
- 绕过官方构建入口，只做裸 `xelatex`
- 为了追求像素对齐而牺牲当前仓库的真实分层与长期可维护性
- 默认改写用户正文语义内容

## 脚本职责约定

- 具体哪些脚本是跨产品线辅助工具，哪些属于 NSFC 专项工具，请直接看 `references/SCRIPT_SCOPE.md`
- 如果目标是 `paper` / `thesis` / `cv`，默认不要切到 NSFC 专项工具链；只有它们能补充 PDF 参数分析或标题比对时才按需单独调用通用脚本
- 当前仓库的权威来源永远是：真实目录结构、真实源码、真实官方构建脚本

## 验收标准

至少满足以下几点：

1. 改动落在正确层级，没有把共享逻辑散落回项目层
2. 通过对应产品线的官方构建入口
3. 若有 warning，需要说明是已有 warning 还是新增 warning
4. 若发生包层改动，必须说明回归了哪些现有模板；若没法全量回归，要明确剩余风险
5. 若用户提供 baseline，则完成必要的 compare / 像素比对 / 结构比对
6. `paper` 场景默认同时关注 PDF 与 DOCX；`cv` 默认关注中英文双入口；`thesis` 默认关注 profile/style 与项目入口的一致性

## 输出要求

- 明确说明本次改动属于哪条产品线
- 明确说明为什么改项目层或包层
- 明确说明使用了哪条官方验证命令
- 如未执行某个比对或导出步骤，要说明原因

## 文档入口

- 工作流：`skills/make-latex-model/docs/WORKFLOW.md`
- FAQ：`skills/make-latex-model/docs/FAQ.md`
- 基线制作：`skills/make-latex-model/docs/BASELINE_GUIDE.md`
- 辅助脚本：`skills/make-latex-model/scripts/README.md`
