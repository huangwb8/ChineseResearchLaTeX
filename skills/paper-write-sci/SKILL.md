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

- 因本 skill 设计缺陷导致的 bug，先用 `bensz-collect-bugs` 规范记录到 `~/.bensz-skills/bugs/`，不要直接修改用户本地已安装的 skill 源码；若有 workaround，先记 bug，再继续完成任务。
- 只有用户明确要求“report bensz skills bugs”等公开上报时，才用本地 `gh` 上传新增 bug 到 `huangwb8/bensz-bugs`；不要 pull / clone 整个仓库。

用于根据 LaTeX 论文项目、Figure/Table 注释和用户补充要求，撰写或优化 SCI 期刊论文正文。

执行时优先把确定性步骤交给脚本，把启发式判断留给 AI：

- 初始化工作区、模式归一化、风格选择、计划文件命名：使用 `config.yaml:scripts.prepare_workspace`
- 风格、章节写法与计划模板等长文档细节：从 `references/` 按需读取

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

### `autonomous` 模式

- 直接修改目标正文文件
- 将分析、审查、渲染日志写入当前运行目录 `<paper_dir>/.paper-write-sci/run_{timestamp}/`
- 若检测到可用构建链，尝试重新渲染 PDF/Word

### `collaborative` 模式

- 只输出计划文件，文件名模式以 `config.yaml:runtime_outputs.collaborative_plan_pattern` 为准，默认带上本轮 `run_id`
- 计划中总结论文缺陷、证据、建议修复方案、影响文件和风险
- 不直接修改论文内容
- 计划以外的中间文件仍写入当前运行目录 `<paper_dir>/.paper-write-sci/run_{timestamp}/`

## 模式规则

### `autonomous`（默认）

- 发现问题就直接修复
- 采用最小必要改动原则
- 在写入任何新数字前，必须先过数字审查
- 在结束前，必须通过逻辑树多轮审查

### `collaborative`

- 先完整读论文，再归纳缺陷和修改路径
- 计划仅作为人类审查材料，不对正文落笔
- 计划文件名、主题 slug、`run_id` 和输出目录都以 `config.yaml:runtime_outputs` 为准
- 计划内容至少包含：问题、证据、建议动作、影响章节、关联图表、风格锚点、章节分工风险、风险说明

## 中间文件约束

除下列“明确约定的对外交付物”外，其余中间文件都必须放在 `<paper_dir>/.paper-write-sci/run_{timestamp}/`：

- `plans/{collaborative_plan_pattern}`
- 论文最终构建产物（例如项目已有的 PDF/Word 输出）

禁止再使用旧目录 `.write-paper-sci/` 与更早的 `.write-paper/`。

推荐工作区结构：

```text
<paper_dir>/
├── main.tex
├── plans/
│   └── WritePaperSCI_{topic}_{run_id}.md
└── .paper-write-sci/
    ├── run_20260326185644/
    │   ├── analysis/
    │   │   ├── paper-structure.md
    │   │   ├── figures-tables.md
    │   │   ├── logic-tree.md
    │   │   ├── reference-style.md
    │   │   ├── render-plan.md
    │   │   ├── consistency-check.md
    │   │   └── runtime-context.json
    │   ├── number-check/
    │   ├── section-role-check/
    │   ├── logic-check/
    │   └── render/
    └── run_20260326190105/
        └── ...
```

每次针对同一篇论文启动新一轮工作时，都必须创建新的 `run_{timestamp}` 子目录；禁止把新的分析、审查和渲染日志继续写进上一轮 run 目录。

## 风格系统

### 风格文件位置

- 风格目录：`references/styles/`
- 风格模板：`references/styles/style-template.md`
- 默认风格以 `config.yaml:style.default` 为准

### 当前风格

| 风格 | 领域 | 作用 |
|---|---|---|
| `bensz-01` | 生物医学 | 以作者风格为中心，强调问题导向、方法命名、强数字对比、详尽且对非领域读者友好的 figure legend，以及诚实局限 |
| `general-01` | 通用 SCI | 综合官方 SCI 写作建议，提供未指定领域时的稳健默认风格 |

### 风格使用原则

1. 优先使用用户显式指定的风格
2. 若用户提供了参考论文/作者材料，可在所选风格基础上提炼额外信号，保存到当前运行目录的 `analysis/reference-style.md`
3. 若用户未指定，则使用 `config.yaml:style.default`
4. 风格服务于“更像人”，不是为了堆砌花哨句子
5. 风格只能改变表达方式，不能改变事实、数字和逻辑
6. 当任务是“全面润色”“重写 Discussion”或任何明显涉及 `Discussion` 去结果化的请求时，先用 `general-01` 守住章节分工底线，再叠加 `bensz-01` 的作者感；不要让作者风格压过章节职责

## 章节职责守卫

任何章节优化都先判断“这一节应该做什么”，再判断“应该写成什么风格”。

- `Introduction`：提出问题、界定空白、给出研究目标；不要提前泄露结果性结论
- `Methods`：说明如何回答问题；不要把结果或解释偷写进方法
- `Results`：报告事实、比较和证据锚点；不要提前做 `Discussion` 式意义阐释
- `Discussion`：解释意义、边界、文献关系、机制或临床转化价值；不要把上一节压缩重写一遍
- `Conclusion`：收束贡献与边界；不要引入新证据

对 `Discussion` 额外执行以下硬约束：

1. 若出现连续的 figure-level 结果复述，优先判定为结构性缺陷，而不是“更具体”
2. 默认每段最多保留 `1` 个核心定量锚点，且该锚点必须直接服务于后续解释
3. 不要追求覆盖所有主图结果；只保留不可替代、能支撑讨论动作的少量结果锚点
4. 每段优先完成以下任务之一：解释主要发现、对位既有文献、说明临床/机制意义、交代局限与适用边界、提出未来验证路径

## 章节职责审查

除数字审查与逻辑审查外，还必须单独检查“这一节是否在做它该做的事”。

### 必答问题

每轮 `section-role-check` 至少回答：

1. 当前章节是否承担了错误职能
2. 是否存在“把上一节压缩重写一遍”的倾向
3. 是否出现“数字都对，但章节功能错位”的问题
4. 对 `Discussion` 而言，解释/文献/局限/未来方向的比重是否高于结果复述

### 审查机制

- 使用 `parallel-vibe` 做独立并行审查
- 并发参数与 SDK 以 `config.yaml:section_role_check.parallel_vibe` 为准
- 审查记录写入当前运行目录的 `section-role-check/`
- 通用模板使用 `references/templates/section-role-check-template.md`
- 若任务聚焦 `Discussion`，或用户明确表达“讨论像结果”“减少重复”“更像人写的 discussion”等意图，必须额外触发 `Discussion audit`
- `Discussion audit` 使用 `references/templates/discussion-role-check-template.md`
- 若任一 runner 指出阻塞性章节串位问题，必须先修复，再进入逻辑终审

### `Discussion audit` 触发条件

出现以下任一意图时，强制触发 `Discussion audit`：

- “优化讨论”
- “讨论像结果”
- “discussion 太像 results”
- “减少重复”
- “更像人写的 discussion”

专项审查输出至少包含：

1. 复述型句子列表
2. 空心评论句列表
3. 缺失的解释任务列表
4. 建议保留的少量定量锚点

## `.tex` 可读性：分段分点

编辑对象是 `.tex` 正文文件，因此必须同时优化“渲染后阅读体验”和“源文件回看体验”。

### 分段

- 需要另起一段时，必须在文本块之间保留 `1` 个或以上空行；在 `.tex` 中，空行意味着新段落
- 典型触发场景：背景切到空白、目的切到方法、结果切到解释、一个局限簇切到另一个局限簇、总述切到图注导读
- 不要为了视觉整齐随意插空行；一旦插空行，就等于明确告诉读者“这里已经是新段落”

### 分点

- 多个点仍属于同一段时，不要插空行；改为让每个“并列信息单元”各占一个物理行，保持“同段但分点”的 `.tex` 源文结构
- 这里的“点”优先指：并列证据单元、并列 panel、并列比较项、并列局限项，而不是任意一个普通句子
- 典型触发场景：同一段内串联多个 Figure/Table 证据、多个组别/亚型对比、panel-by-panel legend、同一段内连续展开的观点或局限
- 同一物理行优先只承载一个便于人类定位的点，这样用户从 PDF/Word 点击回源文时，更容易直接落到目标位置

### 使用边界

- 不要机械地把每一句都拆成单独一行
- 不要把“分点换行”误用成真正列表；只有论文体裁本身适合列表时，才考虑显式 list 环境
- 只对纯正文自然语言段落使用；不要主动重排行敏感结构，例如 `%` 注释拼接、宏参数、大括号内文本、命令密集行、环境头尾或其他可能影响编译/空白语义的 LaTeX 结构
- 不要为了套用新规则而重排整节或整文件；仍应遵循最小必要修改原则

## 数字审查

任何新增、改写或重述的数字，都必须在写入正文前经过数字审查。数字包括但不限于：

- 样本量
- 百分比
- P 值
- HR、OR、RR、AUC、C-index
- 均值、标准差、置信区间
- 随访时长、阈值、版本号

### 必查问题

1. 数字是否来自真实存在的材料
2. 数字是否在当前句子里用得合适
3. 数字的解释是否合理且不越界

### 审查机制

- 使用 `parallel-vibe` 做独立并行审查
- 并发参数与 SDK 以 `config.yaml:number_check.parallel_vibe` 为准
- 每个 runner 都必须覆盖上述三项检查
- 若任一 runner 给出阻塞性问题，则该数字不得写入正文
- 审查记录写入当前运行目录的 `number-check/`
- 审查模板使用 `references/templates/number-check-template.md`

### 数字写入铁律

- 不允许凭经验补数字
- 不允许从图感受、肉眼估计或语义猜测生成精确值
- 不允许把一个材料里的数字套用到另一个语境
- 不允许把统计显著性误写成效果大小，或反过来

## 逻辑审查

论文必须被视为一个整体，不允许只修局部而破坏全局逻辑。

### 逻辑树

在写作或修订过程中，必须维护当前版本的逻辑树，至少包含：

- 核心问题
- 主线论点
- 次线论点
- 每个论点对应的关键证据
- 章节与论点之间的对应关系

逻辑树主文件保存为当前运行目录的 `analysis/logic-tree.md`，格式参考 `references/templates/logic-tree-template.md`。

### 多轮逻辑审查

每轮逻辑审查都要回答：

1. 主线是否清楚
2. 证据是否足以支撑论点
3. 章节顺序是否帮助读者理解
4. 是否存在断裂、矛盾、冗余、跳跃

### 审查机制

- 使用 `parallel-vibe` 做独立并行审查
- 并发参数与 SDK 以 `config.yaml:logic_check.parallel_vibe` 为准
- 每个 runner 都要独立重建逻辑树并指出问题
- 将结果写入当前运行目录的 `logic-check/`
- 每轮都使用 `references/templates/logic-check-template.md`
- 若任一 runner 发现阻塞性逻辑问题，就必须进入下一轮修复与复审
- 直到最新一轮逻辑树没有实质性问题，才能结束

## 工作流程

### 阶段 0：初始化

1. 确认论文目录、Figure/Table 注释存在且可读
2. 定位主入口 tex，优先检查 `main.tex`
3. 扫描 `\input{}` / `\include{}`，建立章节路径映射
4. 识别构建方式与受保护格式文件
5. 运行 `python3 scripts/prepare_workspace.py --paper-dir <paper_dir> [--mode ...] [--style ...] [--topic ...] [--reference-material ...]`，规范化模式、风格、主题 slug，并创建工作区
6. 根据脚本输出的运行清单确认本轮 `run_{timestamp}` 目录、协作计划路径和隐藏工作区根目录
7. 若有参考论文/参考作者材料，提炼补充风格信号
8. 根据用户要求与现有章节状态，预判是否存在 `section-role risk`；若涉及 `Discussion` 优化，优先检查是否有“复述 Results”的倾向

### 阶段 1：理解当前论文

1. 读取全文正文与关键 front/back matter
2. 对照 Figure/Table 注释，提取每张图表支撑的论点
3. 识别已有优质段落、薄弱段落、事实风险、风格不一致位置
4. 若涉及 Figure / Supplementary Figure legend，额外梳理每个 panel 必须解释的视觉编码、术语门槛和读图障碍
5. 标记章节职责风险，特别是 `Introduction` 泄露结果、`Results` 过度解释、`Discussion` 复述结果的段落
6. 初步构建逻辑树并写入当前运行目录的 `analysis/logic-tree.md`

### 阶段 2：决定执行路径

#### `collaborative`

- 按 `config.yaml:runtime_outputs.collaborative_plan_pattern` 生成计划文件
- 推荐让计划文件名与本轮 `run_id` 一一对应，避免同一秒内多次协作运行发生重名覆盖
- 计划应聚焦“缺陷与修复建议”，而不是直接给改后全文
- 计划必须显式写出 `section-role risk`：哪些段落在重复 `Results`、哪些段落缺少真正解释、哪些段落要从“证据叙述”改成“意义叙述”
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
2. 先判断哪些内容应该另起一段，哪些内容仍属同段但应按点换行
3. 先判断该节的章节职责，再用所选风格判断“应该怎么写更像作者”
4. 若当前任务涉及 `Discussion` 重写、全面润色或“discussion 太像 results”之类请求，先套用 `general-01` 的章节分工底线，再叠加 `bensz-01` 的作者感
5. 若涉及新数字，先过数字审查
6. 若命中 `Discussion audit` 触发条件，先列出应删除的复述型句子、必须补上的解释任务和允许保留的少量定量锚点，再动笔
7. 在 `autonomous` 模式下对目标 tex 做最小必要修改，并遵守 `config.yaml:tex_readability`
8. 更新逻辑树，确保局部改动没有破坏全局

处理 Figure Legends / Supplementary Materials 时，必须额外做到：

1. 对每个 panel 解释读图所需的最小视觉语法：坐标轴、行列、颜色、点大小、条形图、注释轨道、参考线、删失标记、risk table 等分别代表什么
2. 对首次出现且不够直观的术语或缩写，补全称并给一句短定义，优先照顾非领域读者
3. 若图中使用标准化、z-score、不同 y 轴尺度、隐藏标签或灰色表示非显著/缺失，要说明其判读方式或设置原因
4. Supplementary Figure 的 legend 详尽度默认不低于主图；除非用户明确要求压缩，否则不要写成简略提纲
5. 同一段 legend 中的不同 panel、比较点或判读动作，默认各占一个物理行；若语义仍属同段，则不要插空行
6. 只保留帮助读图的必要方法细节，避免把整段 Methods 重复进 legend

### 阶段 4：章节职责终审

1. 发起并行 `section-role-check`
2. 若是 `Discussion` 重点任务，额外完成 `Discussion audit`
3. 优先修复章节串位、结果复述和解释缺失，再进入下一阶段

### 阶段 5：全文一致性

至少检查：

- Abstract、Results、Discussion 关键数字是否一致
- 缩写首次定义是否完整且全文统一
- Figure/Table 编号、正文引用和图注是否一致
- Figure / Supplementary Figure legend 是否足以让非领域读者独立完成基本读图
- Introduction 提出的问题，Results/Discussion 是否有回应
- 风格是否统一，是否仍保留作者特征

### 阶段 6：逻辑树终审

1. 对最新文本重建逻辑树
2. 发起并行逻辑审查
3. 若有问题，修复对应正文后再进下一轮
4. 直到最新一轮通过

### 阶段 7：渲染与交付

按以下优先级检测构建链：

1. 项目内置一键构建/导出脚本
2. `scripts/manuscript_tool.py`
3. `Makefile`
4. `latexmk`
5. 直接 `xelatex`

若存在 Word 导出链，也应尝试执行。构建日志放入当前运行目录的 `render/`。

## 约束

- 不修改 `artifacts/`、`*.sty`、`*.cls`、`*.bst`、`*.bbx`、`*.cbx`、`latexmkrc`
- 不改 `main.tex` 的结构，除非用户明确要求
- 不编造数字
- 不为“排版整齐”而重排无关段落或整节 `.tex`
- 用户要求“只改某节”时，严格限制改动范围
- 用户要求协作模式时，严格禁止直接修改论文

## 参考文件

- 运行准备脚本：`scripts/prepare_workspace.py`
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
