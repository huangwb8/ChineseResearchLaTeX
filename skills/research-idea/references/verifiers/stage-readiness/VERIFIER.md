# 研究阶段证据充分性

## Verification target

判断本次 subject.source → subject.target 是否具备继续流水线所需证据，并把流程就绪与科学充分分开表达。advance 的 pass 只表示 `pipeline_ready=true`，不自动表示 `scientific_evidence_sufficient=true` 或 `claim_eligible=true`；rework 的 pass 只表示返工有依据。不证明某假设为真、不保证全世界从未研究过，也不代表最终研究成功。拟推荐或拟淘汰结论的创新性、颠覆潜力和非平凡性由 `bensz.research.hypothesis-merit` 单独认证。

## Inputs and evidence

subject 包含 operation（advance 或 rework）、source 和 target canonical State ID；context 提供 rounds、agents、allow_custom_name 及证据路径映射。evidence 为非空列表，每项有唯一 ref、source_type、summary、content_hash；路径映射限定授权项目内相对路径。内容标识须来自当前文件，不能填写虚构 hash。各轮审查证据说明 round、reviewer、源稿与汇总关系。

前进所需角色：literature → candidates 为 theme/search-manifest/landscape/radar/interpretation/map；candidates → review 为 candidates/novelty-neighbors；review → reporting 为 review/synthesis；reporting → completed 为 report、validate_report 和完成证据索引。landscape 必须覆盖 Search manifest 的全部 canonical record ID，并绑定 manifest/candidate hash。角色和数量由 Agent 检查真实成员覆盖，不能以空文件、重复副本或关键词充数。rework 使用原因、受影响证据和恢复位置，不适用前进角色要求。

Agent 必须阅读 ref 对应文件和所引用的论文依据；summary 只是索引，不能代替源证据。主题、雷达、解读、map、候选、查新、独立审查结果、汇总与报告均由业务 Agent 产生。引用外部 Skill 结果时用项目内相对来源，禁止复制私有指令或敏感数据。缺证据时报告缺口，不自行补造。

## Execution

先运行 required 的 `evidence-consistency` 确定性组件，再由当前 Agent 执行 required 的 `scientific-review`。前者只核对 completion index、论文解读 frontmatter、全文源文件哈希、论文解读执行回执和 reviewer thread/done/RESULT 回执；未知 schema、缺字段、越界路径、符号链接、哈希或证据层级冲突均 fail-closed，不评价科研价值。后者读取当前 State、目标 State、证据及源文件，先核对图边与 subject.operation；未知操作或非法图边返回 fail。Kernel 生成 handoff并验证绑定回传，不自行调用模型。报告阶段另运行已有 validate_report.py，读取 passed 与 completion_eligible；它只检查本 Skill 格式。

operation=rework 时只允许退到图中更早阶段：核验返工原因、受影响上游及下游、下一步补证据动作，证据充分则 pass。此 pass 仅支持回退，不能用来推荐或完成；不要求被推翻的研究结论通过。无清楚依据时 uncertain。

operation=advance 时按目标判断：

- 进入 candidates：主题与输入一致，Search manifest/canonical hash 可核对，landscape 对 canonical 候选逐条覆盖且核心、辅助、待跟踪和范围外计数对账；雷达核心集均有解读结果及证据深度，map 同时综合 R 核心证据和辅助研究线，并保留时间演化。标题只用于发现/聚类，摘要只支持相关性和作者自报判断；全文才支持决定性的机制、结果和等价性结论。单一可靠来源和预印本均可参与，不得因此自动判低价值。
- 进入 review：每个候选均来自 map，科学问题具体，假设有关键预测与真正能推翻它的反证路径；每项保留候选列出强近邻、摘要级排除理由、决定性近邻及 unresolved 状态。已知决定性近邻尚未全文核验时，只要缺口被完整暴露，`pipeline_ready` 可以为 true 以进入独立审查，但 `scientific_evidence_sufficient` 与 `claim_eligible` 必须为 false。只有冲突、版本合并、疑似重复或决定新颖性的唯一近邻才要求额外来源核验；不能按累计篇数、综述字数或导出文件判断充分。零候选可以进入 review，但须有当前范围内充分的淘汰证据、一次实质重新探索结果（或用户明确预算边界）。
- 进入 reporting：审查达到本 run 约定的轮数与每轮人数，每轮分别完成价值挑战、解释/辨别能力、重新选择与迁移检查；修改轮数时仍覆盖三类任务。每个结果给出新增发现、候选影响与分歧；草稿未变化仍须证明本轮判断，不以字节一致充数。零候选仍复核淘汰、遗漏替代方向与重启条件；同一模型不天然构成独立证据。各轮串行继承汇总，冲突与风险被处理；如果改写影响科学问题或假设等价性，应 fail 并回 candidates 重新查新。科学价值、判断可信度与近期投入分别比较，最强替代方向和资源敏感性透明，不能用可行性抵消低科学价值。
- 进入 completed：报告与已通过的前置证据一致，没有未查新的实质改写；所有决定性近邻已取得与最终 claim 强度匹配的核验，`pipeline_ready`、`scientific_evidence_sufficient` 与 `claim_eligible` 均为 true。recommended 有价值成立且完成必要查新/审查的保留候选，no_qualified 有充分淘汰与约定探索/复核证据，insufficient 不能进入 completed。分别检查排序/替代方向或淘汰范围/重启条件，以及查新、反证、限制和最小下一步；引文与事实有依据，无中间路径泄露。格式正确不能替代此判断。

当前主 Agent 可以执行该语义组件，但必须实际读取证据、写理由；已有业务独立审查和科学假设价值认证不能被此组件替代。Kernel 不调用模型，handoff 仅为待办。不得发起网络写入；必要外部只读核验由宿主按业务流程执行。源文件读取限定授权项目，运行日志写工作区；Pack 资产只读。

## Output and verdicts

使用 Kernel component-result 协议，从 handoff 复制 pack/component/contract/plan/run/state visit/attempt/hash 绑定字段，或在同一可信执行会话使用 handoff.bind_result；不能将旧审查重新绑定给新 handoff。executor 记录脱敏角色与实际模型。结果含 execution_status、verdict、evidence_refs，以及 facts.summary、facts.confidence（0..1）、facts.uncertainties、facts.pipeline_ready、facts.scientific_evidence_sufficient、facts.claim_eligible；findings 说明缺陷和恢复动作。三个布尔字段必须显式给出，不能从 verdict 或 confidence 推断。置信度不是通过阈值。

- pass：本阶段开展下一步所需输入齐全且 `pipeline_ready=true`；允许在 candidates → review 暴露已知科学缺口，但必须令后两个字段为 false。reporting → completed 只有三个字段均为 true 才能 pass。
- fail：结构缺失、来源矛盾、科学命题不充分或实质改写未重新查新。
- uncertain：资料有限、网络不可观测、证据相关性无法判断，保留疑点供补证据/人工复核。
- unchecked：尚无实际绑定的语义判断；error/timed_out：执行失败；skipped：依赖未完成。

两个 required 组件均 completed 且 pass 才允许对应转移；Kernel 原生不变量检查当前 run/attempt 的记录及 Gate。Agent 必须核对 source/target 和最新证据，旧 attempt 或其它转移的结果不可复用。

## Failure and boundaries

非法 JSON、缺证据、空证据、回传错绑或未解决不确定性不放行。输入/执行错误由 Kernel 拒绝；证据内容变化、范围不足和语义错误由 Agent 判定。先保存失败原因，补证据后新建 attempt；人工意见也是待核验的证据，没有强制通过开关。

Kernel 校验提交的证据标识与结果绑定，不自动重读任意路径或发现全部上游文件变化。Agent 在验证及转移前核对文件内容；变化后回退到受影响阶段，将下游旧结论标为待复核，不改写事件。事件记录不证明来源真实或执行者身份经过外部认证。

限定只读授权项目资料和必要的外部只读核验，拒绝绝对/越界证据路径及符号链接逃逸；大文件只用必要摘要并保留来源。不得保存访问令牌、隐私、完整论文原始数据或隐藏指令到日志。内置文件/路径/引用 Verifier 可按运行指南辅助核验，但不能代替本科学判断。
