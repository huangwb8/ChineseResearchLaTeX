# 研究阶段证据充分性

## Verification target

判断本次 subject.source → subject.target 的**固定证据快照**是否支持进入下一研究阶段。pass 表示机械完整性与科学充分性均满足；不证明某假设为真、不保证全世界从未研究过，也不代表最终研究成功。

## Inputs and evidence

subject 指定来源与目标 canonical State ID；context 提供固定 rounds、agents、allow_custom_name，宿主注入授权 project_root。evidence 为非空列表，每项具有唯一 ref、role、项目内相对 path、source_type、summary、实算 content_hash。review 角色另含 round、reviewer。角色需求、默认轮次和资源上限见 config.yaml，不在此复制数值。

Agent 必须阅读 ref 对应文件和所引用的论文依据；summary 只是索引，不能代替源证据。主题、雷达、解读、map、候选、查新、独立审查结果、汇总与报告均由业务 Agent 产生。引用外部 Skill 结果时用项目内相对来源，禁止复制私有指令或敏感数据。缺证据时报告缺口，不自行补造。

## Execution

先运行 evidence-shape 脚本：规范化路径、重算文件哈希、检查非空角色与不同审查结果数量、调用已有 validate_report。该组件只检查事实结构，不能判定论文真假、科学价值或研究新颖性。

scientific-review 是宿主执行的 Agent 组件，读取固定证据后按目标判断：

- 进入 candidates：主题与输入一致，雷达覆盖范围有说明，入选论文均有解读结果及证据深度，map 有时间顺序、研究线、关键转折、争议、缺口与论文锚点；不能用摘要推断全文结论，未完成解读不应通过。
- 进入 review：每个候选均来自 map，科学问题具体，假设有关键预测与真正能推翻它的反证路径；每项 Premium 查新有真实执行来源、查询/覆盖边界和判定。区分未研究、部分研究和已充分研究；后者须淘汰或实质改写后重新查新，至少一个可保留候选。禁止凭文件名或 Premium 字样推定已查新。
- 进入 reporting：审查达到本 run 约定的轮数与每轮人数，每个结果覆盖不同问题、证据或反例；同一模型不天然构成独立证据。各轮串行继承汇总，冲突与风险被处理；如果改写影响科学问题或假设等价性，应 fail 并回 candidates 重新查新。综合选择理由透明。
- 进入 completed：报告与已通过的前置证据一致，没有未查新的实质改写；候选、最佳方案、查新、可证伪性、限制和最小下一步表达完整；引文与事实有依据，无中间路径泄露。格式正确不能替代此判断。

当前主 Agent 可以执行该语义组件，但必须实际读取证据、写理由；已有业务独立审查不能被此组件替代。Kernel 不调用模型，handoff 仅为待办。不得发起网络写入；必要外部只读核验由宿主按业务流程执行。源文件读取限定授权项目，运行日志写工作区；Pack 资产只读。

## Output and verdicts

使用 Kernel component-result 回传协议，保留 handoff 的 pack/component/contract/plan/run/attempt/hash 绑定；executor.type=agent，id 为脱敏角色标识，model 为实际模型名。提供 execution_status、verdict、evidence_refs 和 facts，其中 facts 包含非空 summary、0..1 的 confidence、uncertainties 列表；findings 解释缺陷及修复方向。置信度不是通过阈值。

- pass：所有命题有实证支撑、引用具体 evidence_refs、无未解决不确定性。
- fail：结构缺失、来源矛盾、科学命题不充分或实质改写未重新查新。
- uncertain：资料有限、网络不可观测、证据相关性无法判断，保留疑点供补证据/人工复核。
- unchecked：尚无实际绑定的语义判断；error/timed_out：执行失败；skipped：依赖未完成。

required 两个组件均完成且 pass 才允许前进；脚本成功退出或返回 pass、模型自评、旧 attempt 的通过结果均不能单独放行。

## Failure and boundaries

非法 JSON、越界、空文件、超限、哈希变化、回传身份/契约/证据错绑均不放行。先保留失败回执，再修复证据并 prepare 新 attempt；uncertain 需要补证据或人类意见后重新核验，不提供强制通过开关。回退只允许图中前置阶段，必须记录原因与证据并失效下游检查点。

路径/哈希检查是本地可信宿主的质量边界，不是操作系统沙箱；日志不能证明执行者没有伪造科学证据，来源真实性和语义仍须可复核。不得保存访问令牌、隐私、完整论文原始数据或隐藏指令到运行日志。
