# Research Literature Radar 核心—辅助文献分层计划

## 通俗解释：究竟发生了什么

- **一句话说明：** 当前 Radar 像图书管理员只把少数精读书放上桌，其余检索到的书只报一个“未入选”总数，导致找研究想法时失去领域宽度。
- **具体场景：** v17 从 180 条 canonical 候选中精读 8 篇、列出 3 篇高分落选，却只用一个数字概括另外 169 篇；后来无法复核某篇关键近邻是否曾被看见或为何被跳过。
- **对应到本问题：** Radar 核心论文仍负责深度，Search 候选则应形成可检索的辅助文献景观，而不是被二元化为“入选/无用”。
- **改变前后：** 改进后每条 canonical 候选都有稳定角色和证据层级；少数核心论文精读，其余论文仍可帮助识别术语、研究线、预印本和潜在近邻。

## 专业判断：问题在哪里

- **当前现象：** `selection.md` 只详细记录入选和少数高分落选；“主题硬过滤”主要是 Agent 语义判断，没有覆盖全部候选的机器可读决策表。
- **影响范围：** `research-idea` 无法消费完整检索景观；筛选不可重放，关键近邻可能在生成候选前消失。
- **已知原因：** Radar 的输出契约以精选论文库为中心，把 Search bundle 当召回来源而非持续可用的辅助知识层；证据深度、相关性、发表状态和文献身份可信度尚未正交表达。

## 要达到什么目标

- 保留 `research-literature-search` 的 canonical 顺序、ID、manifest/hash 和 provenance，不复制检索或去重逻辑。
- 输出一份覆盖全部 canonical 候选的 `literature-landscape.jsonl`，逐条标记研究线、角色、相关性、证据深度、发表状态、用途、不确定性和处理理由。
- 角色至少区分 `core`、`supporting`、`watchlist`、`out_of_scope`；其中 `supporting/watchlist` 不因未精读而退出后续推理。
- Radar 核心论文继续获得稳定 R 编号和全文/摘要解读入口；辅助论文沿用 Search record ID，不人为制造第二套文献身份。
- 预印本默认允许进入核心、辅助或待跟踪层；仅记录版本、日期和同行评审状态，不因 `preprint` 自动降低相关性或思想价值。
- 一个可靠 provider 与稳定标识通常足以确认文献身份；只有元数据冲突、版本合并、疑似重复或决定性近邻才要求额外核对。

不在本次处理范围：改变 Search provider 策略、要求全部论文下载全文、把 Radar 扩展成完整系统综述。

## 改进方向

### 用“文献景观”替代二元硬过滤

主题判断保留，但结果不再只有入选或跳过。每篇论文都进入一个研究线；确实无关的条目也保留最小 `out_of_scope` reason code。普通用户可以看到少数重点论文，同时下游仍可使用完整领域轮廓。

建议最小字段：`record_id`、`canonical_rank`、`role`、`cluster`、`relevance`、`evidence_depth`、`publication_status`、`identity_confidence`、`use_cases`、`reason`、`uncertainties`、`source_refs`。字段值和枚举放在 `config.yaml`，语义判断规则放在 Skill/reference，避免脚本硬编码科研结论。

### 将四种判断拆开

- 相关性：是否帮助回答当前主题。
- 证据深度：title、abstract、fulltext 等当前可读范围。
- 发表状态：preprint、published、unknown。
- 身份可信度：文献记录是否来自可追溯来源并具有稳定标识。

标题可用于聚类和待跟踪，摘要可用于辅助判断；方法、结果和等价性强结论必须受证据深度约束。预印本状态不得替代相关性判断。

### 核心论文仍然精而少

Radar 继续依据研究线覆盖、idea-level 价值、证据质量和多样性选核心集，但配额只用于避免研究线遗漏，不强迫选择低质量论文。核心选择必须能回到 landscape 条目；高相关但暂时没有全文的论文进入 `watchlist` 或核心摘要层，而不是因证据深度不足直接消失。

### 让确定性脚本负责对账

扩展现有 corpus/finalize 类脚本，只做 manifest/hash 校验、canonical 全覆盖、枚举和计数对账、重复 ID、路径边界及稳定序列化。聚类、角色、相关性和思想价值继续由 AI 判断，并保存理由与 uncertainty。

## 实施范围与顺序

1. 先定义 landscape schema、角色语义和单一来源/预印本政策，并用 v17 的 180 条候选制作不进入发布资产的回归夹具。
2. 调整 Radar 的生成与收敛脚本，使每条 canonical 候选恰好出现一次，并从中派生现有精选报告。
3. 更新 `SKILL.md`、`config.yaml`、README、CHANGELOG 和测试，版本只在 `config.yaml` 提升。
4. 修改源码前重新获取并核对 `huangwb8/skills` 的现行 `AGENTS.md`；本次计划阶段网络读取失败，不得在实施时跳过。

## 如何确认完成

- 180 条输入应产生 180 条 landscape 记录，canonical ID、顺序和候选 hash 不变。
- 核心、辅助、待跟踪和无关数量之和严格等于 manifest canonical 数量。
- 单一可靠来源的真实论文可进入 supporting/core，不因缺少第二 provider 被拒绝。
- 高相关预印本可进入 core/watchlist，并明确 `publication_status=preprint`；不得自动标记低价值。
- 只有标题的条目不得生成方法或结果结论；摘要级条目必须使用“摘要报告”等限定语义。
- 关键近邻从 supporting/watchlist 升级 core 时保留原 Search 身份和历史，不重新去重。
- 原有 Radar 独立使用场景、catalog、目录安全和布局验证保持通过。

## 风险与待确认事项

- 对数百条候选逐篇做自由文本分析会增加上下文成本；应采用批量聚类和短理由，不生成数百篇长笔记。
- Search record ID 是否足以跨 Radar 轮次稳定，需要用 DOI/arXiv/标题身份规则验证；不得让 R 编号承担跨 run 的 canonical 身份。
- 当前 Radar 要求每篇入选论文有“至少一个独立发现信号”，与单一可靠来源政策冲突，实施时应改为风险触发核对。

