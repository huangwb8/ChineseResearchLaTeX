# Research Idea 文献景观与证据门禁计划

## 通俗解释：究竟发生了什么

- **一句话说明：** 当前 Research Idea 先看少数精读论文，再为每个候选生成庞大综述，却没有持续利用最初检索到的完整领域地图。
- **具体场景：** v17 将 180 条前置候选压缩为 8 篇精读，之后每个候选又选择 115 篇；直到第三轮审查才发现最关键近邻全文和等价性仍未核验。
- **对应到本问题：** 核心论文应像地图上的主干道路，Search 候选则是周围街道；不能只看主干，也不能为了“全面”逐条走遍所有街道。
- **改变前后：** 改进后候选生成同时看到核心精读证据和辅助文献景观，发现关键近邻时按需升级阅读；Verifier 在昂贵流程之前检查真正的证据缺口。

## 专业判断：问题在哪里

- Research Idea 当前要求 Radar/Interpretation/Map 作为 literature 角色，但没有要求完整 Search canonical 候选形成可消费的辅助层。
- `stage-readiness` 在 v17 candidates 阶段以高置信度放行，后来 review 又根据同一批关键缺口将充分性改为 incomplete，说明门禁时点和输入契约不够准确。
- 当前规则把“多源、全文”写成 Premium 充分性的普遍条件；这会混淆文献身份、发表状态、证据深度和科学 claim 强度。
- `hypothesis-merit` 在尚未形成价值结论的边上通过“不适用 pass”，虽然有 attempt 绑定保护，语义仍容易被误读。

## 要达到什么目标

- 候选生成同时消费 Radar 核心论文、逐篇 interpretation 和覆盖全部 canonical 候选的辅助 landscape。
- 核心论文使用 R 锚点；辅助文献沿用 Search 稳定 record ID，并可在成为关键近邻时晋升为 R，不创建平行 canonical 身份。
- 证据使用遵循层级：标题用于发现/聚类，摘要用于相关性和作者自报判断，全文用于决定性的机制、结果和等价性判断。
- 预印本默认纳入前沿景观；以清晰限定语提醒用户评审状态，不把 preprint 自动判为低价值。
- 一个可靠来源通常足以确认文献存在；仅在冲突、版本合并、疑似重复或决定新颖性的唯一近邻时要求额外核验。
- State 图保持 `literature → candidates → review → reporting → completed`，不因本次内容策略增加新 State。

不在本次处理范围：修改 BSK Kernel、把每篇辅助文献做全文解读、把研究想法报告变成系统综述。

## 改进方向

### 建立“核心证据 + 辅助景观 + 待升级近邻”输入

Research map 不再只列 R 文献和 O 机会，还应按研究线引用辅助候选的聚类摘要、覆盖范围和代表记录。候选 C 必须说明它依据哪些核心 R、哪些辅助研究线，以及哪些潜在近邻仍待升级核验。

### 将查新改为按风险升级

候选形成后，先从 landscape 识别最可能否定新意的条目。摘要足以排除明显不等价工作；疑似等价或决定性近邻才定向获取全文、调用单篇 interpretation 或补检。不得以累计文献数、综述字数、PDF/Word 导出作为查新充分性的代理。

### 修订 Stage Readiness Verifier

保留 `bensz.research.stage-readiness`，不新增同义 Verifier。调整两个关键边：

- literature → candidates：要求 Search manifest/canonical hash、landscape 全量对账、核心集和解读、research map；允许单来源和预印本，检查证据层级措辞，不要求辅助文献全文。
- candidates → review：要求每个保留候选都有强近邻清单、摘要级排除理由、需要全文的决定性近邻及 unresolved 状态。若已知决定性近邻尚未核验，可以进入“带缺口的独立审查”，但不能被写成 `evidence_sufficient=true`；是否仍允许该 State 转移需在契约中明确区分“审查就绪”和“科学充分”。

为避免 v17 式矛盾，Verifier 必须把 `pipeline_ready` 与 `scientific_evidence_sufficient` 分开返回；前者允许进入审查，后者只参与最终 claim eligibility。不能再用一次 pass 同时表达二者。

### 收紧 Hypothesis Merit 的适用语义

保留 `bensz.research.hypothesis-merit`，只让它认证真正存在推荐/淘汰结论的边。实施时先核对最新生产 BSK 是否支持 action-specific required Verifier：

- 若支持，在 config/orchestrator 中按 action 声明 required；
- 若不支持，保留当前全局 required 兼容路径，但输出必须具有明确的 `applicability`，不适用结果不得进入 completion evidence，也不得在报告中称为“价值通过”。

不新增第三个语义 Verifier。文献身份/hash/结构对账使用确定性检查；科学相关性和证据充分性继续由 AI 判断。

### 保持 State 最小化

现有五个领域 State 对恢复、Gate 和审计有实际价值，删除会损失阶段身份；本次不增加 landscape、enrichment 或 fulltext State，这些是 literature/candidates 内的动作和证据状态。失败后继续使用新 attempt 和现有返工边。

### 对齐最新托管规范

未来实施会修改 Research Idea，因此必须同时清理当前 `runtime.kernel.version`、`required_capabilities` 等旧式运行时固定，改为只声明 Kernel 包名，并使用托管 BSK 固定入口验证。保留 State/Verifier Pack 自身版本。单一编排入口继续存在，但要按最新生产接口复验，而不是依赖 v17 的隔离 Kernel。

## Verifier/State 删除影响结论

| 组件 | 结论 | 理由 |
| --- | --- | --- |
| stage-readiness Verifier | 保留并改契约 | 删除会失去各阶段证据角色、深度和缺口门禁；v17 证明它能阻止错误 completed，但需更早区分流程就绪与科学充分 |
| hypothesis-merit Verifier | 保留并收紧适用性 | 删除会失去非平凡性、替代方向和可证伪价值审问；不应承担文献结构检查 |
| 五个 Research Idea State | 全部保留，不新增 | 它们对应稳定业务阶段并支持 attempt/Gate/恢复；文献角色不是持续生命周期状态 |
| 新的文献质量 Verifier | 不新增 | 可由 stage-readiness 的 Evidence Contract 和确定性 landscape 校验组合完成，新增会重复判断并扩大 Gate 复杂度 |

## AI 与确定性分工

- **确定性：** manifest/hash/schema、canonical 全覆盖、ID 唯一、角色枚举、计数对账、证据路径、attempt/Gate 绑定。
- **AI：** 研究线聚类、相关性、核心/辅助角色、近邻等价性、claim 强度、科学价值和 uncertainty。
- **混合：** 脚本收集 publication/evidence/source 事实，AI 按证据层级判断能否支持具体论断。

## 实施范围与顺序

1. 先完成 Radar landscape 契约，使 Research Idea 有稳定的全量输入。
2. 再完成 Review 的软篇数与强近邻选文，避免 Research Idea 调用旧的强制填充行为。
3. 更新 Research Idea 的 map、候选、novelty、报告和 completion evidence 契约。
4. 修订两个 Verifier Pack 与 orchestration 输入，State 图不变；Pack 契约发生变化时独立提升 Pack 版本。
5. 同步 `SKILL.md`、config、references、README、CHANGELOG 和测试，Skill 版本只在 config 更新。
6. 实施前重新取得上游 `AGENTS.md`；随后用最新托管 BSK 执行结构检查和真实成功/fail-closed 路径。

## 如何确认完成

- 用 v17 风格夹具运行时，180 条 canonical 候选全部进入 landscape，8 篇核心仍可精读，其余文献不会只剩汇总数字。
- 候选生成输入同时引用 R 核心证据和辅助研究线；无需把数百条全文塞入上下文。
- 高相关预印本和单一可靠来源论文可参与候选与新颖性判断，报告明确其状态和证据深度。
- 已知决定性近邻只有标题/摘要时，系统能进入审查以暴露问题，但 `scientific_evidence_sufficient` 与 `claim_eligible` 必须保持 false。
- 仅当决定性近邻已得到与 claim 相匹配的核验，最终推荐/无合格结论才可通过 completed Gate。
- hypothesis-merit 的不适用回执不能被完成索引消费。
- 测试覆盖未知 action、State 错配、required 缺失/uncertain、Gate 非放行、旧 attempt 复用、landscape hash 漂移和关键近邻升级后的重新审查。
- 最新托管 BSK 结构加载、编排成功路径和 fail-closed 路径均有证据；不能以静态可发现替代实际执行。

## 风险与待确认事项

- “可以进入 review”与“证据已经充分”必须分层，否则 Verifier 会再次出现 v17 式先 pass 后推翻。字段和 Gate 消费方式需在实现前用最新 BSK 接口验证。
- 辅助 landscape 可能很大，应向候选生成提供聚类摘要和按需读取索引，而不是一次加载全部摘要。
- 本次无法联网取得 `huangwb8/skills` 最新 `AGENTS.md`；这只影响未来实施，不影响本计划，但源码修改前必须补齐该检查。
- 不建议修改 `research-literature-search` 1.0.4：它当前已表达 preprint profile、单次可靠来源和 priority-fallback-topup，所需变化主要发生在消费者。

