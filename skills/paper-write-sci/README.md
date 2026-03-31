# paper-write-sci

本 README 面向使用者：告诉你什么时候用 `paper-write-sci`，怎么触发，默认会产出什么。
执行规范看 `SKILL.md`，默认参数看 `config.yaml`。

## 用法

最推荐的用法：

```text
请使用 paper-write-sci skill 优化我的 SCI 论文。
输入：
- 论文源代码目录：/path/to/paper
- Figure/Table 注释：/path/to/notes.md
输出：
- autonomous 模式：直接修改论文正文，并在需要时重新渲染 PDF/Word
- collaborative 模式：只生成 plans/WritePaperSCI_{topic}_{run_id}.md 供我审查
```

带参数约束的用法：

```text
请使用 paper-write-sci skill 润色我的 SCI 论文。
输入：
- 论文源代码目录：/path/to/paper
- Figure/Table 注释：/path/to/notes.md
- 参考作者材料：/path/to/reference.docx

另外，还有下列参数约束：
- 模式：collaborative
- 风格：bensz-01
- 只处理：Discussion 和 Abstract
```

## 你会得到什么

### 默认 `autonomous`

- 直接修改目标正文 tex 文件
- 自动做数字审查、章节职责审查和逻辑审查
- 自动按“整篇论文所有正文 tex”而不是“当前文件”检查缩写首次定义与全文统一
- 默认遵守 `.tex` 的“分段分点”策略：新段落用空行，同段内多个点优先逐行写，方便回源定位
- 其余中间文件统一进入本轮运行目录 `<paper_dir>/.paper-write-sci/run_{timestamp}/`
- 如果项目有可用构建链，会尝试重新渲染 PDF/Word

### `collaborative`

- 不直接改论文
- 只输出 `plans/WritePaperSCI_{topic}_{run_id}.md`
- 计划聚焦论文缺陷、证据、建议动作、关联图表、章节分工风险、风险等级
- 计划之外的中间文件仍收纳到本轮运行目录 `<paper_dir>/.paper-write-sci/run_{timestamp}/`

## 两种模式

| 模式 | 什么时候用 | 会不会直接改论文 |
|---|---|---|
| `autonomous`（默认） | 你希望 AI 自主推进并尽快落地 | 会 |
| `collaborative` | 你想先审计划，再决定是否执行 | 不会 |

如果你不特别说明，skill 默认使用 `autonomous`。

## `.tex` 分段分点策略

因为这个 skill 直接编辑 `.tex`，所以默认不仅关心 PDF/Word 渲染效果，也关心源文件是否便于人类回看。

- `分段`：真的需要另起一段时，用 `1` 个或以上空行分开；这会在渲染结果中形成新段落
- `分点`：多个点仍属于同一段时，不插空行，而是让每个“并列信息单元”各占一个物理行；这里的“点”优先指并列证据、panel、比较项或局限项，不是任意一句话
- 常见适用场景：同一段里的多图/多表证据、多组对比、panel-by-panel legend、同一段内连续展开的多个观点或局限
- 默认不会机械地每句都拆行，也不会为了套用规则重排整节
- 这套规则只面向纯正文自然语言段落；不会主动改写 `%` 注释拼接、宏参数、命令密集行、环境头尾等 line-sensitive 的 LaTeX 结构

## 风格系统

这个 skill 不追求“通用 AI 味”的论文，而是尽量写得更像人类作者。

当前内置风格：

| 风格 | 适用领域 | 特点 |
|---|---|---|
| `bensz-01`（默认） | 生物医学 | 问题导向、方法命名、关键数字强、Figure legend 更详尽且对非领域读者友好、局限性诚实具体 |
| `general-01` | 通用 SCI | 综合官方写作建议，适合未指定领域的稳健写法 |

风格来源说明：

- `bensz-01`：来源于内部作者材料的风格提炼；正文写法主要参考 `manuscript_unformat.docx`，Figure / Supplementary Figure legend 的详尽导读风格主要参考 `manuscript.docx`
- `general-01`：综合 Nature formatting guide、Scientific Reports submission guidelines 与 Elsevier Researcher Academy 的通用 SCI 写作建议整理而成

你也可以提供参考论文或作者材料。skill 会先学习风格特征，再按事实材料写作，但不会照抄原句。

当任务是“全面润色”“重写 Discussion”或明显要求把 `Discussion` 从 `Results` 复述中拉出来时，skill 会先用 `general-01` 守住章节分工底线，再叠加 `bensz-01` 的作者感，避免把“像作者”误写成“继续报数”。

## 使用示例

### 示例 1：全文优化

```text
请使用 paper-write-sci skill，根据 LaTeX 项目和 Figure/Table 注释，完整优化这篇 SCI 论文。
输入：
- 论文目录：/path/to/paper
- 图表注释：/path/to/notes.md
```

### 示例 2：只改某一部分

```text
请使用 paper-write-sci skill，只优化 Results。
输入：
- 论文目录：/path/to/paper
- 图表注释：/path/to/notes.md

约束：
- 不要改 Introduction、Methods、Discussion
```

### 示例 3：先给计划，不直接改

```text
请使用 paper-write-sci skill。
输入：
- 论文目录：/path/to/paper
- 图表注释：/path/to/notes.md

约束：
- 模式：collaborative
- 先生成计划，我确认后再执行
```

### 示例 4：模仿作者风格润色

```text
请使用 paper-write-sci skill 润色论文。
输入：
- 论文目录：/path/to/paper
- 图表注释：/path/to/notes.md
- 参考作者材料：/path/to/reference.docx

约束：
- 风格：bensz-01
- 保持现有结构，只优化表达、逻辑和数字呈现
```

### 示例 5：通用 SCI 风格

```text
请使用 paper-write-sci skill 优化我的论文。
输入：
- 论文目录：/path/to/paper
- 图表注释：/path/to/notes.md

约束：
- 风格：general-01
- 重点改善 Abstract、Introduction、Discussion
```

## 审查机制

### 数字审查

只要正文里要写数字，skill 就要检查三件事：

- 这个数字是否来自真实存在的结果材料
- 这个数字写在这里是否合适
- 对这个数字的解读是否合理

默认会基于 `parallel-vibe` 并行审查，配置是 `5` 个 thread、每个 thread `1` 个 runner、SDK 仅 `Codex`。相关中间文件在 `<paper_dir>/.paper-write-sci/run_{timestamp}/number-check/`。

### 章节职责审查

除了数字和总体逻辑，skill 还会单独检查每一节是否在做它该做的事。

- `Results` 应主要报告事实，不抢做 `Discussion`
- `Discussion` 应主要解释意义、边界、文献关系和转化价值，不压缩重写上一节
- 若用户意图包含“优化讨论”“讨论像结果”“discussion 太像 results”“减少重复”“更像人写的 discussion”等表达，会强制触发 `Discussion audit`

相关中间文件在 `<paper_dir>/.paper-write-sci/run_{timestamp}/section-role-check/`。

### 逻辑审查

skill 会维护一棵论文逻辑树，反复检查：

- 主线是否清楚
- 证据是否支撑论点
- 章节之间是否协同
- 是否存在断裂、矛盾、冗余、跳跃

相关中间文件在 `<paper_dir>/.paper-write-sci/run_{timestamp}/logic-check/`，逻辑树主文件在 `<paper_dir>/.paper-write-sci/run_{timestamp}/analysis/logic-tree.md`。

### 缩写一致性审查

skill 不把“缩写首次定义是否完整且全文统一”理解为单个 tex 文件内自洽，而是默认按整篇论文所有正文 tex 联合检查。

- 会先建立全文缩写清单，再开始局部修改
- 首次出现位置以全篇为准，不以当前正在编辑的文件为准
- Abstract、Figure Legends、Supplementary Materials 里的缩写也要回到全文口径统一判断
- 相关中间文件默认写入 `<paper_dir>/.paper-write-sci/run_{timestamp}/analysis/abbreviation-inventory.md` 与 `<paper_dir>/.paper-write-sci/run_{timestamp}/analysis/consistency-check.md`

## 输出文件

默认输出位置如下：

| 路径 | 作用 |
|---|---|
| `<paper_dir>/plans/WritePaperSCI_{topic}_{run_id}.md` | 协作模式计划文件 |
| `<paper_dir>/.paper-write-sci/run_{timestamp}/analysis/paper-structure.md` | 本轮章节路径映射 |
| `<paper_dir>/.paper-write-sci/run_{timestamp}/analysis/figures-tables.md` | 本轮图表与论点梳理 |
| `<paper_dir>/.paper-write-sci/run_{timestamp}/analysis/abbreviation-inventory.md` | 本轮全文缩写清单与首次出现位置 |
| `<paper_dir>/.paper-write-sci/run_{timestamp}/analysis/logic-tree.md` | 本轮逻辑树 |
| `<paper_dir>/.paper-write-sci/run_{timestamp}/analysis/reference-style.md` | 本轮参考作者材料提炼结果 |
| `<paper_dir>/.paper-write-sci/run_{timestamp}/analysis/consistency-check.md` | 本轮全文一致性与缩写复核记录 |
| `<paper_dir>/.paper-write-sci/run_{timestamp}/analysis/runtime-context.json` | 本轮运行清单 |
| `<paper_dir>/.paper-write-sci/run_{timestamp}/number-check/` | 本轮数字审查中间文件 |
| `<paper_dir>/.paper-write-sci/run_{timestamp}/section-role-check/` | 本轮章节职责审查与 `Discussion audit` 中间文件 |
| `<paper_dir>/.paper-write-sci/run_{timestamp}/logic-check/` | 本轮逻辑审查中间文件 |
| `<paper_dir>/.paper-write-sci/run_{timestamp}/render/` | 本轮构建日志 |

## 配置项

`config.yaml` 中最常改的参数：

| 参数 | 默认值 | 作用 |
|---|---|---|
| `mode.default` | `autonomous` | 默认运行模式 |
| `style.default` | `bensz-01` | 默认风格 |
| `style.schema_file` | `references/styles/style-template.md` | 新增风格时参考的统一模板 |
| `tex_readability.paragraph_strategy` | `blank_line_for_new_paragraph` | 新段落的空行策略 |
| `tex_readability.point_strategy` | `one_point_per_line_without_blank_line` | `.tex` 同段分点换行策略 |
| `tex_readability.avoid_mechanical_line_breaks` | `true` | 防止退化成逐句断行 |
| `number_check.parallel_vibe.threads` | `5` | 数字审查并行线程数 |
| `section_role_check.parallel_vibe.threads` | `5` | 章节职责审查并行线程数 |
| `section_role_check.discussion.max_quantitative_anchor_per_paragraph` | `1` | `Discussion` 每段默认允许的核心定量锚点上限 |
| `abbreviation_check.scope` | `full_manuscript_all_editable_tex` | 缩写检查默认按整篇论文所有正文 tex 联合执行 |
| `abbreviation_check.require_global_rescan_before_finish` | `true` | 结束前必须做一次全文缩写复扫，不能只看当前文件 |
| `logic_check.parallel_vibe.threads` | `5` | 逻辑审查并行线程数 |
| `logic_check.max_iterations` | `3` | 逻辑审查最大轮次 |

## 不适用场景

以下情况不要使用这个 skill：

- 只想改 LaTeX 模板、版式、样式参数
- 只想管理参考文献
- 只想处理图片、图形、配色或排版
- 不是 LaTeX 论文项目

## 常见问题

### 计划文件为什么不放进 `.paper-write-sci/`？

因为协作模式下，计划本身就是明确交付给人类审查的对外产物，所以单独放在 `<paper_dir>/plans/`。除此之外，其它中间文件仍然统一收纳到 `.paper-write-sci/run_{timestamp}/`。

### 为什么要给同一篇论文按轮次拆成不同 `run_{timestamp}`？

因为同一篇论文往往会经历多轮修改。把每一轮的分析、审查与构建日志隔离到独立 run 目录里，后续回看时更容易追踪“这一轮改了什么、为什么这么改、审查结论是什么”，也能避免新一轮工作覆盖上一轮证据。

### 会不会修改 `main.tex` 或样式文件？

默认不会。skill 只应修改正文内容相关文件，不应碰 `main.tex` 的结构和样式文件，除非你明确要求。

### 我没有参考作者材料，还能用吗？

可以。没提供时会按 `config.yaml` 的默认风格处理；当前默认值是 `bensz-01`。

### 我只想先看问题，不想动论文，怎么说？

把模式指定为 `collaborative`，或者直接说“先给计划，不要直接改论文”。

### 这个 skill 会不会编数字？

不应该。它要求新增或改写数字前先做数字审查；任一并行 runner 发现阻塞性问题，该数字都不应写入正文。

### 为什么有些 `.tex` 看起来同一段却分成多行？

这是故意的。只要语义仍属于同一段，skill 会优先用“同段分点换行”而不是插空行断段，这样既不改变 PDF/Word 的段落效果，也更方便你从渲染结果回到 `.tex` 时直接定位到对应那个点。
