---
name: paper-write-sci
description: 根据 LaTeX 论文项目撰写、修订和润色 SCI 期刊论文，默认 AI 自主模式，也支持人机协作仅输出审查计划；提供作者风格化写作、数字事实核验、逻辑树多轮审查与 PDF/Word 渲染闭环。⚠️ 不适用：仅改格式/样式参数、纯参考文献管理、图片处理、非论文写作任务。
metadata:
  author: Bensz Conan
  short-description: SCI 论文写作与修订 skill（支持风格化、数字审查、逻辑审查）
  keywords:
    - paper-write-sci
    - write-paper-sci
    - SCI论文写作
    - 期刊论文
    - LaTeX论文
    - 论文润色
    - 风格化写作
    - 数字审查
    - 逻辑审查
---

# Paper Write SCI

## 与 bensz-collect-bugs 的协作约定

- 因本 skill 设计缺陷导致的 bug，先用 `bensz-collect-bugs` 规范记录到 `~/.bensz-skills/bugs/`，不要直接修改用户本地已安装的 skill 源码；若有 workaround，先记 bug，再继续完成任务
- 只有用户明确要求“report bensz skills bugs”等公开上报时，才用本地 `gh` 上传新增 bug 到 `huangwb8/bensz-bugs`；不要 pull 或 clone 整个仓库

用于根据 LaTeX 论文项目、Figure/Table 注释和用户补充要求，撰写或优化 SCI 期刊论文正文。

执行时优先把确定性步骤交给脚本，把启发式判断留给 AI：

- 初始化工作区、模式归一化、风格选择、计划文件命名：使用 `config.yaml:scripts.prepare_workspace`
- 长规则块按需从 `references/` 读取；不要把所有参考文档一次性塞进上下文

## 目标

- 写出更像作者本人、而不是通用 AI 模板的论文
- 在写作与修订过程中严格保护数字、逻辑和术语一致性
- 默认直接推进修改；当用户需要人机协作时，只输出计划，不直接改论文
- 除明确约定的对外交付物外，把所有中间文件收敛到 `<paper_dir>/.paper-write-sci/run_{timestamp}/`

## 输入

| 输入项 | 是否必须 | 说明 |
|---|---|---|
| 论文源代码目录 | 必须 | LaTeX 论文项目根目录 |
| Figure/Table 注释 | 必须 | 解释每张图表支撑什么论点、有哪些关键数字 |
| 用户要求 | 可选 | 例如“只改 Results”“偏保守润色”“补强 Discussion” |
| 参考论文/参考作者材料 | 可选 | 用于提炼额外风格信号，只学风格，不抄句子 |
| 运行模式 | 可选 | 默认值与别名以 `config.yaml:mode` 为准 |
| 风格 | 可选 | 默认值与可用列表以 `config.yaml:style` 为准 |

## 输出

### `autonomous`

- 直接修改目标正文文件
- 将分析、审查、渲染日志写入当前运行目录 `<paper_dir>/.paper-write-sci/run_{timestamp}/`
- 若检测到可用构建链，尝试重新渲染 PDF 和 Word

### `collaborative`

- 只输出计划文件，文件名模式以 `config.yaml:runtime_outputs.collaborative_plan_pattern` 为准，默认带上本轮 `run_id`
- 计划中总结论文缺陷、证据、建议修复方案、影响文件和风险
- 不直接修改论文内容
- 计划以外的中间文件仍写入当前运行目录 `<paper_dir>/.paper-write-sci/run_{timestamp}/`

## 模式规则

### `autonomous`（默认）

- 发现问题就直接修复
- 采用最小必要改动原则
- 在写入任何新数字前，必须先过数字审查
- 在结束前，必须通过章节职责终审、全文一致性终审和逻辑树终审

### `collaborative`

- 先完整读论文，再归纳缺陷和修改路径
- 计划仅作为人类审查材料，不对正文落笔
- 计划文件名、主题 slug、`run_id` 和输出目录都以 `config.yaml:runtime_outputs` 为准
- 计划内容至少包含：问题、证据、建议动作、影响章节、关联图表、风格锚点、章节分工风险、风险说明

## 中间文件约束

除下列“明确约定的对外交付物”外，其余中间文件都必须放在 `<paper_dir>/.paper-write-sci/run_{timestamp}/`：

- `plans/{collaborative_plan_pattern}`
- 论文最终构建产物，例如项目已有的 PDF 和 Word 输出

禁止再使用旧目录 `.write-paper-sci/` 与更早的 `.write-paper/`。

## 风格系统

- 风格目录：`references/styles/`
- 风格模板：`references/styles/style-template.md`
- 默认风格以 `config.yaml:style.default` 为准

当前风格：

| 风格 | 领域 | 作用 |
|---|---|---|
| `bensz-01` | 生物医学 | 以作者风格为中心，强调问题导向、方法命名、强数字对比、详尽且对非领域读者友好的 figure legend，以及诚实局限 |
| `general-01` | 通用 SCI | 综合官方 SCI 写作建议，提供未指定领域时的稳健默认风格 |

风格使用原则：

1. 优先使用用户显式指定的风格
2. 若用户提供了参考论文或作者材料，可在所选风格基础上提炼额外信号，保存到当前运行目录的 `analysis/reference-style.md`
3. 若用户未指定，则使用 `config.yaml:style.default`
4. 风格服务于“更像人”，不是为了堆砌花哨句子
5. 风格只能改变表达方式，不能改变事实、数字和逻辑
6. 当任务是“全面润色”“重写 Discussion”或任何明显涉及 `Discussion` 去结果化的请求时，先用 `general-01` 守住章节分工底线，再叠加 `bensz-01` 的作者感；不要让作者风格压过章节职责

## 按需读取的参考文件

优先只读取当前任务所需的参考文件：

- 风格与章节写法：`references/writing-style-guide.md`、`references/styles/bensz-01.md`、`references/styles/general-01.md`
- 执行护栏与通过标准：`references/execution-guards.md`
- 协作计划模板：`references/collaborative-plan-template.md`
- 数字审查模板：`references/templates/number-check-template.md`
- 章节职责审查模板：`references/templates/section-role-check-template.md`
- `Discussion audit` 模板：`references/templates/discussion-role-check-template.md`
- 逻辑树模板：`references/templates/logic-tree-template.md`
- 逻辑审查模板：`references/templates/logic-check-template.md`

读取建议：

- 涉及章节串位、`Discussion` 重写或全文终审时，读取 `references/execution-guards.md`
- 只做风格化润色或图注润色时，优先读取 `writing-style-guide.md` 和目标风格文件
- 新增风格时，再读取 `references/styles/style-template.md`

## 工作流程

### 阶段 0：初始化

1. 确认论文目录、Figure/Table 注释存在且可读
2. 定位主入口 tex，优先检查 `main.tex`
3. 扫描 `\input{}` 和 `\include{}`，建立章节路径映射
4. 识别构建方式与受保护格式文件
5. 运行 `python3 scripts/prepare_workspace.py --paper-dir <paper_dir> [--mode ...] [--style ...] [--topic ...] [--reference-material ...]`
6. 根据脚本输出确认本轮 `run_{timestamp}` 目录、协作计划路径和隐藏工作区根目录
7. 若有参考论文或参考作者材料，提炼补充风格信号
8. 若任务涉及章节职责、数字、缩写或逻辑高风险问题，读取 `references/execution-guards.md`

### 阶段 1：理解当前论文

1. 读取全文正文与关键 front/back matter
2. 对照 Figure/Table 注释，提取每张图表支撑的论点
3. 识别已有优质段落、薄弱段落、事实风险、风格不一致位置
4. 标记章节职责风险，特别是 `Introduction` 泄露结果、`Results` 过度解释、`Discussion` 复述结果的段落
5. 初步构建逻辑树并写入当前运行目录的 `analysis/logic-tree.md`
6. 若任务涉及全文缩写治理，按 `references/execution-guards.md` 建立 `analysis/abbreviation-inventory.md`

### 阶段 2：决定执行路径

#### `collaborative`

- 按 `config.yaml:runtime_outputs.collaborative_plan_pattern` 生成计划文件
- 计划应聚焦“缺陷与修复建议”，而不是直接给改后全文
- 计划必须显式写出 `section-role risk`
- 到此停止，不修改正文

#### `autonomous`

- 制定内部修订顺序
- 优先修正事实错误、数字风险和逻辑断裂
- 再做结构优化、语言润色和风格统一

### 阶段 3：逐节写作或修订

默认顺序：

```text
Introduction -> Methods -> Results -> Discussion -> Conclusion ->
Additional Information -> Figure Legends -> Supplementary Materials -> Abstract
```

每节处理时：

1. 先读现有文本和对应图表证据
2. 先判断该节的章节职责，再用所选风格判断“应该怎么写更像作者”
3. 若涉及长规则判断，回到 `references/execution-guards.md`
4. 若涉及新数字，先过数字审查
5. 若命中 `Discussion audit` 触发条件，先完成专项审查，再动笔
6. 若涉及新增、删除或改写缩写，先回查 `analysis/abbreviation-inventory.md`
7. 在 `autonomous` 模式下对目标 tex 做最小必要修改，并遵守 `config.yaml:tex_readability`
8. 更新逻辑树与必要的全文一致性记录，确保局部改动没有破坏全局

处理 Figure Legends 或 Supplementary Materials 时：

- 对每个 panel 解释读图所需的最小视觉语法
- 对首次出现且不够直观的术语或缩写，补全称并给一句短定义
- 只保留帮助读图的必要方法细节，避免把整段 Methods 重复进 legend

### 阶段 4：终审

1. 发起 `section-role-check`
2. 完成全文一致性复核，包括数字、缩写、Figure/Table 引用与图注一致性
3. 对最新文本重建逻辑树并发起逻辑审查
4. 若有阻塞性问题，修复后再复审

### 阶段 5：渲染与交付

按以下优先级检测构建链：

1. 项目内置一键构建或导出脚本
2. `scripts/manuscript_tool.py`
3. `Makefile`
4. `latexmk`
5. 直接 `xelatex`

若存在 Word 导出链，也应尝试执行。构建日志放入当前运行目录的 `render/`。

## 约束

- 不修改 `artifacts/`、`*.sty`、`*.cls`、`*.bst`、`*.bbx`、`*.cbx`、`latexmkrc`
- 不改 `main.tex` 的结构，除非用户明确要求
- 不编造数字
- 不把缩写检查降级成“当前文件自洽”
- 不允许同一概念在不同 tex 中使用冲突缩写、冲突全称或忽有忽无的定义
- 不要为了局部简洁随意新造缩写；若新缩写不会在全文稳定复用，优先不用
- 不为“排版整齐”而重排无关段落或整节 `.tex`
- 用户要求“只改某节”时，严格限制改动范围
- 用户要求协作模式时，严格禁止直接修改论文

## 参考文件

- 运行准备脚本：`scripts/prepare_workspace.py`
- 执行护栏：`references/execution-guards.md`
- 风格模板：`references/styles/style-template.md`
- `bensz-01`：`references/styles/bensz-01.md`
- `general-01`：`references/styles/general-01.md`
- 协作计划模板：`references/collaborative-plan-template.md`
- 章节写作指南：`references/writing-style-guide.md`
- 数字审查模板：`references/templates/number-check-template.md`
- 章节职责审查模板：`references/templates/section-role-check-template.md`
- `Discussion audit` 模板：`references/templates/discussion-role-check-template.md`
- 逻辑树模板：`references/templates/logic-tree-template.md`
- 逻辑审查模板：`references/templates/logic-check-template.md`
