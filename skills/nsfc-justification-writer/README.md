# nsfc-justification-writer — 用户使用指南

本 README 面向使用者：说明如何触发、准备输入、分阶段写作和可逆自动写入。Skill 版本以 [`config.yaml`](config.yaml) 的 `skill_info.version` 为准；AI 执行规范见 [`SKILL.md`](SKILL.md)。

## 它适合做什么

当你需要撰写、重构、审查或润色 NSFC/科研基金申请书的立项依据时使用本 skill。它覆盖研究意义、国内外研究现状及发展动态、现状末端的科学问题/科学假设凝练和小结；研究目标、技术路线、主验证场景和判定规则不属于本 skill 要求的立项依据固定章节。

它按标准立项依据检查以下内容链：

```text
研究意义 → 国内外研究现状及发展动态（按主题分块）→ 关键缺口/科学问题/假设 → 前期工作与项目切入点 → 小结 → 研究内容
```

代码负责目标定位、引用/字数检查、diff、备份和回滚；宿主 AI 自动理解课题、自主规划逻辑、术语、论证维度、可读性检查和正文生成。Skill 不会编造文献、实验结果或无法核验的事实；材料不足时采用保守假设并记录待核验项，不暂停询问。

## 推荐用法（Prompt 调用 Skill）

在 Codex、Claude Code 等支持 Skill 的宿主中，直接使用自然语言触发完整自动流程：

```text
请使用 nsfc-justification-writer skill 重构我的立项依据。
输入：/path/to/project/justification.tex，以及相关研究内容和参考文献。
要求：只改白名单正文，保留标题、LaTeX 结构命令、标签和引用；自动完成诊断、成稿、Tier2 复核、备份和写入。
输出：已写入的成稿、unified diff、引用核验提示、自动假设与备份路径。
```

目标文件可以由项目配置声明，或由脚本从 `main.tex` 自动发现；候选不唯一时按确定性优先级自动选择并记录依据，不要求固定文件名、固定标题或 `\subsubsection`。

从零写作时也只需给出项目目录和已有材料：

```text
请使用 nsfc-justification-writer skill 从零撰写立项依据。
输入：/path/to/project，以及其中已有的研究内容、研究基础和参考文献。
输出：自动写入的立项依据正文、unified diff、保守假设、待核验项和备份路径。
```

## 从零开始写作

### 1. 准备信息表

没有成熟草稿时，宿主 AI 会从现有材料自动提取信息，并对缺口采用保守假设。需要查看字段结构时可生成模板：

```bash
python skills/nsfc-justification-writer/scripts/run.py init
```

至少提供：

- 研究对象或应用场景；
- 问题定义和现有研究的 2–4 条关键瓶颈；
- 1–3 条科学问题（疑问句，追问认知缺口）；
- 1 条核心科学假设（可证伪陈述句，不写验证方式）；
- 项目切入点及其与后续研究内容的简短衔接。

可选材料包括前期基础、代表性文献、方法概览、目标字数和术语口径。缺少事实或文献时，宿主 AI 自动采用最小保守假设、收缩主张并记录待核验项。

### 2. 运行写作教练

```bash
python skills/nsfc-justification-writer/scripts/run.py coach \
  --project-root <项目目录> \
  --stage skeleton \
  --info-form <信息表路径>
```

各阶段用途如下：

| 阶段 | 作用 |
| --- | --- |
| `skeleton` | 自动确定正文边界，梳理事实、缺口、瓶颈→约束映射，并记录保守假设 |
| `draft` | 按自动确定的范围生成或扩写正文，建立科学问题和假设的论证链 |
| `revise` | 修复逻辑跳跃、缺失引用和不可核验表述 |
| `polish` | 先保护事实与论证，再改善长句、指代、缩写界定和段内衔接 |
| `final` | 按字数、引用、结构和白名单范围做最终检查 |
| `auto` | 根据当前正文状态自动选择阶段 |

`coach` 的输出是阶段判断、自动行动清单和可复制提示词；主流程会继续生成正文并写入。若 AI responder 不可用，skill 会按确定性规则继续执行，并把无法核验的内容记录为待核验项，不向用户发起问题。

### 3. 形成完整提案并自动写入

让 AI 输出包含目标文件完整内容的提案，保存为临时文件后运行：

```bash
python skills/nsfc-justification-writer/scripts/run.py preview \
  --project-root <项目目录> \
  --proposal-file /tmp/proposal.tex
```

默认 `preview` 会生成 diff 并自动写入项目文件（写入前自动备份）；显式加 `--dry-run` 才只读检查：

- 修改行和 unified diff；
- 缺失 bibkey；
- 标题、标签、环境、配置命令或其它结构变化；
- 目标路径和项目根目录边界。

如果发现结构命令变化，AI 会自动重新生成“正文-only”提案并重试；不会请求用户扩大范围。

### 4. 兼容旧项目的标题替换

新结构优先由宿主 AI 按自动生成的 diff 写入。旧项目可使用兼容入口：

```bash
python skills/nsfc-justification-writer/scripts/run.py apply-section \
  --project-root <项目目录> \
  --title "历史标题" \
  --body-file /tmp/new_body.txt
```

`apply-section` 依赖标题替换，仅用于迁移旧项目；它不是新项目的默认流程。命令会自动备份并写入，写入后输出实际 diff 和回滚入口。

## 已有草稿的推荐流程

先做只读诊断：

```bash
python skills/nsfc-justification-writer/scripts/run.py diagnose --project-root <项目目录>
python skills/nsfc-justification-writer/scripts/run.py refs --project-root <项目目录>
```

重点看“研究意义 → 现状与发展 → 关键缺口 → 科学问题/假设 → 前期工作与切入点 → 小结”是否闭环，并检查小结是否只作后续研究内容的简短过渡。完成 `diagnose` 的 Tier1 后，当前宿主 AI 必须读取 `references/tier2_semantic_review.md` 并直接执行 Tier2 语义检查，随后自动生成完整提案并运行 `preview` 写入；整个过程不等待用户审核。

## 引用与 DOI 核验

生成引用摘要：

```bash
python skills/nsfc-justification-writer/scripts/run.py refs --project-root <项目目录>
```

按摘要将 DOI、链接或可核验题录补入项目 `references/*.bib`。缺失 key 默认拒绝写入；`apply-section --allow-missing-citations` 仅用于迁移或临时诊断，不应作为常规写作路径。

## 独立检查工具

```bash
# 字数（默认中文字符口径）
python skills/nsfc-justification-writer/scripts/run.py wordcount --project-root <项目目录>

# 语义审查或写作引导（完整流程必须包含 Tier2）
python skills/nsfc-justification-writer/scripts/run.py review --project-root <项目目录>
python skills/nsfc-justification-writer/scripts/run.py coach --project-root <项目目录> --stage auto
```

`diagnose`、`coach` 和 `review` 的结果不以固定小节数量、标题关键词或固定术语/维度清单作为写入门槛；完整流程仍包含 Tier2。逻辑、术语、论证维度和专业可读性均由宿主 AI 按 [`references/tier2_semantic_review.md`](references/tier2_semantic_review.md) 自主规划。“国际领先”“填补空白”等吹牛式或绝对化表述由宿主 AI 自动按参考准则复核，脚本不维护固定词表。

## 写作边界

- 科学问题应追问未知关系、机制、性质或适用边界，不写成“开发/构建/实现”的研究目标。
- 科学假设应是可证伪的预测性陈述，不把“通过某实验验证”写进假设句。
- 假设前优先放领域事实、已有研究和认知缺口；本项目干预、比较、终点和技术路线集中放在假设之后。
- 外部论文的方法学描述可以作为现状证据，不自动判定为本项目方案。
- 不使用“国际领先”“国内首次”等无法核验的绝对化表述；应改为可比较的指标、基线或适用边界。
- 专业可读性复核不是科普化：保留已核验事实、必要术语、限定条件、引用命令和 LaTeX 结构。
- 默认不修改 `main.tex`、配置文件、`.cls`、`.sty` 或白名单之外的正文范围。

### 章节职责边界

完整立项依据的论证链不等于固定标题，但内容职责应贴近标准申请书的实际写法：

- **研究意义**：说明研究对象的重要性、现实/临床或理论必要性、现有路线的主要不足及研究价值。
- **国内外研究现状及发展动态**：按课题主题分块，写代表性研究、发展趋势、能力边界和关键缺口；申请人前期工作通常在该部分末端作为切入点桥梁。
- **小结**：压缩现状、缺口、科学问题/假设和项目切入点，用一段话衔接后续研究内容。

科学问题和科学假设是现状末端的论证要素，不要求单独设标题。研究目标、总体研究思路、技术路线、主验证场景、排除标准、主终点、比较基线、预设阈值和风险处理属于研究内容、研究方案或研究基础；如果它们出现在立项依据中，应建议后移，而不是补成新的立项依据章节。跨小节调整时，报告会先给出章节级提案，再给正文 diff。

## 配置要点

| 配置 | 作用 |
| --- | --- |
| `style.mode` | `theoretical`、`mixed` 或 `engineering`，改变措辞和证据重心 |
| `targets.justification_tex` | 目标正文相对路径；为空时自动发现并选择候选 |
| `references.allow_missing_citations` | 默认 `false`，缺失 bibkey 时拒绝写入 |
| `guardrails.output_mode` | 默认 `auto_apply`；自动写入前备份并保留 diff |
| `guardrails.allowed_write_files` | 自定义正文目标的精确白名单 |
| `word_count` | 字数统计目标和口径，不强制固定章节结构 |

自定义目标文件时，请同步在 `guardrails.allowed_write_files` 中声明相对路径。不要把 `.cls`、`.sty`、`main.tex` 或配置文件加入白名单，除非你明确承担相应风险并授权。

## 写入后的版本管理

```bash
python skills/nsfc-justification-writer/scripts/run.py list-runs
python skills/nsfc-justification-writer/scripts/run.py diff \
  --project-root <项目目录> --run-id <run_id>
python skills/nsfc-justification-writer/scripts/run.py rollback \
  --project-root <项目目录> --run-id <run_id> --yes
```

## 常见问题

**如何只做检查而不写文件？**

默认是可逆的 `auto_apply` 模式。系统自动选择目标、备份、写入并输出 diff；需要只读检查时使用 `preview --dry-run`。

**文件名或标题宏不同会被判为空吗？**

不会。新流程不依赖固定文件名、标题命令或小节数量；旧 `apply-section` 仅保留为兼容提示。

**假设前出现方法名是否一定错误？**

不一定。外部论文的方法学描述可以作为现状证据；只有把本项目方案提前作为论证主线时，才建议后移。

**为什么建议拆句或补过渡？**

这是面向大同行的阅读负担复核。建议应说明位置、障碍、影响和保真改法；已经清楚的专业表述不需要为了通俗而改写。

**缺少引用怎么办？**

Skill 不会编造引用，也不会停下来追问。它会保留已有可核验引用，把缺证据的主张改为有边界的表述，并在交付中列为待核验项。
