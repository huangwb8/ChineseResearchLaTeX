# 科学假设价值与创新性

## Verification target

判断拟推荐或拟淘汰的科学假设是否经过实质价值审问。pass 只表示当前证据支持“值得推荐”或“当前范围内无合格候选”的业务结论；不证明假设为真、不保证一定颠覆领域，也不保证全世界没有近邻工作。

## Inputs and evidence

subject 包含 operation、source、target 和可选 outcome。context 提供 rounds、agents、评估范围、资源边界、用户目标及证据路径映射。evidence 为非空列表，每项有唯一 ref、source_type、summary、content_hash；推荐结论至少覆盖 candidate、novelty、review、synthesis、report 或等价的上游材料。无合格结论至少覆盖被淘汰候选、淘汰依据、重新探索或用户预算边界、独立复核和报告。

Agent 必须读取候选、近邻工作、研究脉络 map、审查记录和最终报告；summary 只是索引。科学价值判断必须引用具体 evidence_refs，不接受“模型认为有创新”“专家可能感兴趣”等无证据断言。

## Execution

唯一组件 merit-review 由当前 Agent 执行。Kernel 生成 handoff 并验证绑定回传，不自行调用模型。先核对 source/target 是否为 `candidates → review` 或 `reporting → completed`；其它前进边若尚未形成候选、推荐或无合格结论，可返回 pass，但 facts.summary 必须明确“本次转移不作科学假设价值认证，未放行推荐结论”。rework 时只判断返工是否有价值审问缺口，不替代 stage-readiness 的图边核验。

operation=advance 时按结论判断：

- recommended：至少一个保留候选必须通过价值审问。该候选要说明相对最近邻工作的概念增量，成功后改变的机制理解、理论框架、测量范式或决策，失败后排除的重要解释，以及为什么不是换对象、换数据、加参数、组合方法或流程更完整。必须有能区分竞争解释的关键预测、最强替代方向、会推翻优先级的条件和证据可信度边界。高可行性、资源适配或“还没人这么做”不能抵消低科学价值。
- no_qualified：必须证明当前候选池已经经过同等价值审问，被淘汰不是因为流程未完成或全文受限。淘汰理由应指出平凡、重复、定义性假设、无知识增量、无法区分竞争解释或仅工程优化等具体缺陷，并包含一次有新证据或新解释角度的重新探索，或用户明确预算边界。
- insufficient：不得 pass 为完成；若证据不足以判断价值、创新性、颠覆潜力或最近邻等价性，返回 uncertain，并指出需要补齐的证据和恢复阶段。

至少审问以下维度：

1. 重要问题：假设瞄准的未解释现象、机制缺口、边界条件或决策矛盾是否值得研究。
2. 概念增量：相对最近邻工作新增的不是对象、参数或流程，而是解释框架、机制连接、测量范式、适用边界或竞争假设区分能力。
3. 颠覆/改写潜力：若成立，会改变哪些已有理解；若失败，会排除哪些有分量的解释。
4. 非平凡性：常规解释、简单基线、直接复现、工程组合或显然下一步为何不足。
5. 可辨别预测：预测能区分至少两个竞争解释，并说明关键反例。
6. 替代方向：与最强替代科学问题相比，为什么当前候选更值得优先，或为什么均不合格。
7. 边界诚实：明确判断可信度、资源限制、近邻全文限制和会改变结论的证据。

已有 stage-readiness 通过不能替代本 Verifier。本 Verifier 也不能替代文献查新或多轮独立审查；它只在这些证据基础上做价值认证。

## Output and verdicts

使用 Kernel component-result 协议，从 handoff 复制 pack/component/contract/plan/run/attempt/hash 绑定字段，或在同一可信执行会话使用 handoff.bind_result。executor 记录脱敏角色与实际模型。结果含 execution_status、verdict、evidence_refs、facts.summary、facts.confidence、facts.uncertainties 和 findings。facts.summary 必须概括“为什么值得推荐/为什么无合格/为什么不足”，不能只写流程已完成。

- pass：推荐或无合格结论已通过上述价值审问，且证据引用具体、无未解决的关键疑点；或本次转移尚未包含推荐、淘汰或完成结论，facts.summary 明确标记为不适用。后者不能被复用于后续推荐或完成。
- fail：候选平庸、重复、定义性、缺少概念增量、缺少可辨别预测、用可行性掩盖低价值，或报告推荐与证据不一致。
- uncertain：近邻等价性、证据深度、领域重要性或替代方向不足以判断。
- unchecked：尚无实际绑定的语义判断；error/timed_out/skipped 表示执行失败、超时或不适用。

required 语义组件 completed 且 pass 才允许对应转移。旧 attempt、其它候选或其它转移的价值判断不可复用。

## Failure and boundaries

缺少候选、查新、审查、综合或报告证据时 fail 或 uncertain；不得补造专家共识、隐含领域趋势或未读论文结论。直接近邻全文不可得、用户目标不清且会改变价值排序、或候选实质改写未重新查新时返回 uncertain 或 fail，并指定恢复动作。

限定只读授权项目资料和必要外部只读核验，拒绝绝对/越界证据路径及符号链接逃逸。不得保存访问令牌、隐私、完整论文原始数据或隐藏指令到日志。人工意见也是证据，不能作为强制通过开关。
