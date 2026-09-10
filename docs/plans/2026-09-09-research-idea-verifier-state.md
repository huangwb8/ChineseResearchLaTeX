# Verifier/State 设计计划：research-idea

## 结论摘要

2026-09-09：为原有 Skill 增加一个阶段证据混合 Verifier 和五个业务 State；复用 Kernel 1.0.3 的 Pack 执行、绑定回传、Gate、StateMachine 和 EventLog。保持已有报告校验 CLI。系统安装的 0.12.4 不满足组件协议，本轮使用固定上游源码隔离验证，不更新系统安装。版本推进以 config.yaml 为准。

## 业务流程与风险地图

事实来源：`skills/research-idea/SKILL.md` 的文献调查、逐对查新、多轮独立打磨、报告验证；`scripts/init_workspace.py`、`scripts/validate_report.py`、`config.yaml`。现有 report 检查不能证明前置调查或独立审查完成，manifest 也不能恢复阶段。

文献调查 → 候选与查新 → 独立打磨 → 报告 → 完成。查新全部淘汰回候选，map 不足回文献调查，审查修改问题实质时重新查新。失败/等待作为事件保留当前阶段，避免额外 blocked 状态丢失恢复位置。

## 删除影响测试（含“不接入”结论）

- 保留 Verifier：删除后无法阻止证据缺失、内容变化后复用旧通过结果，以及结构检查冒充科学质量证明。
- 保留 State：删除后无法约束跳阶段、退回后失效下游结果、跨进程恢复。
- 不新增通用失败/取消业务节点：失败保留阶段和非通过 Gate，取消记录终止事件；通用生命周期不复制进领域图。

## Verifier 设计矩阵

| 候选 | 决策 | 稳定命题 | 分工 | 输入/证据 | Gate | 失败处理 |
| --- | --- | --- | --- | --- | --- | --- |
| bensz.research.stage-readiness | 保留 | 当前快照足以进入指定下一阶段 | 脚本检查非空证据、类型/角色、内容哈希和最终结构；Agent 判断科学充分性 | subject/source/target、context、带角色的文件证据与摘要 | required，脚本和语义组件均 pass 才推进 | uncertain/unchecked 保留阶段，补证据或人工复核 |
| 独立报告格式 Pack | 不接入 | 与已有 validate_report 重复 | 混合 Pack 调用原 helper | 最终报告 | 合并进上述组件 | 避免重复规则 |

## State 设计矩阵与最小状态图

State owner.machine 为 `bensz.research-ideation`，节点为 `literature`、`candidates`、`review`、`reporting`、`completed`；均为 kind=skill，纯阶段契约，无伪造的脚本执行。

| 节点 | 持续阶段 | 离开证据 |
| --- | --- | --- |
| literature | 主题、文献雷达、逐篇解读与 map | 主题、雷达、解读、map 及科学充分性判定 |
| candidates | 生成候选并逐一 Premium 查新 | 完整候选池、每项查新判定及证据 |
| review | 多轮独立打磨与综合选择 | 配置/用户指定轮次的独立结果和汇总 |
| reporting | 起草最终报告 | 报告结构与科学结论一致性 |
| completed | 已通过交付检查 | 终态，无后继 |

正常边：literature → candidates → review → reporting → completed。
回退边：candidates → literature；review → candidates/literature；reporting → review/candidates/literature。回退需说明和证据，但无需假装当前成果合格；回退后新 attempt 重查，旧 Gate 不能复用。

## AI/确定性分工与 Evidence Contract

证据条目包含 ref、role、项目内相对 path、content_hash、source_type、summary。输入文件限量、限大小，拒绝绝对路径、..、symlink 与越界。宿主读取文件并重算 hash，把规范化事实交给 JSON-stdio 组件；语义回传绑定 run/attempt、契约、计划、handoff 和证据哈希。

语义结果包含 verdict、facts.summary、facts.confidence、facts.uncertainties、evidence_refs。模型置信度不是 pass 阈值；没有实际执行保持 unchecked。科学充分性、摘要与全文边界、查新覆盖、可证伪性和审查独立性由 Agent 依据源证据判断，不由关键词或数量直接推断。

## Kernel 对接、Gate、重放与资源边界

按上游托管规范使用 references/verifiers 和 references/states 索引；索引独占身份与版本，State frontmatter 保存图。runtime 精确绑定 Kernel 版本，声明 required verifier。新增 Skill host CLI 加载本地注册表并通过 run_contract 执行，不声称普通 bsk verifier CLI 自动发现 Skill Pack。

事件日志使用 EventLog 哈希链，Skill 适配器重放领域事件并由 StateMachine 检查边。完成转移引用当前 attempt 的 Kernel Gate；历史证据变化后不允许提交旧回传。宿主串行写入；日志为权威来源，状态显示由重放生成。失败与中断保留最近阶段，可重试新 attempt；不覆写旧事件或静默迁移旧 manifest。

## Kernel 复用与元 Verifier/State 提炼决策

已读取上游固定提交 `796de9808711cb5a6ac070cc7783280114f4c17a` 的 Kernel README、pyproject、两个 index、相关契约以及 states/verifiers/contract_packs/runtime/workspace API。仓库无 Kernel 源码；取证源码位于本轮 shared/input，非项目新增依赖副本。

| 候选能力 | Kernel ID/版本 | 复用方式 | 差异 | 跨领域 | 提炼建议 | 理由/验证 |
| --- | --- | --- | --- | --- | --- | --- |
| 证据来源 | bensz.evidence.provenance / 1.0.0 | 不直接复用 | 空列表通过且不重算哈希 | 是 | 不新增 | 宿主做非空与快照校验，测试缺证据与变更 |
| 结构 | bensz.artifact.schema-conformance / 1.0.0 | 不直接复用 | 仅顶层键检查，不能覆盖候选/轮次/报告 | 是 | 不新增 | 复用本 Skill helper，测试结构失败 |
| 路径 | bensz.artifact.path-scope / 1.0.0 | 不直接复用 | 无文件读取授权与资源上限 | 是 | 不新增 | 宿主收敛读取边界，测试穿越/symlink |
| 引文科学支撑 | bensz.evidence.citation-truth-fit / 1.0.0 | 契约参考 | 引文蕴含不足以证明研究选题和查新充分性 | 部分 | 领域保留 | 专用自然语言契约，测试 handoff 和错绑 |
| 生命周期 | bensz.runtime.active 等 / 1.0.0 | 分层复用基础实现 | 无文献/候选/查新阶段 | 是 | 不新增 | StateMachine + EventLog；测试合法边、恢复、重放 |

### Kernel 复用结论

- 复用 Pack loader/executor/adapter、Gate、StateMachine、EventLog 的稳定协议，避免自建通用执行或哈希账本；通过真实执行及复制资产验证。
- 通用 Verifier 的证据契约弱于本任务，不直接作为研究阶段通过证明；科学规则留在 Skill，不扩展 Kernel reducer。

### Kernel 元组件提炼结论

- 不提炼新元组件：非空证据、文件快照、审查轮次等现有组合不足以证明跨两个不相邻领域需要新公共 API。
- 研究候选、Premium 查新与 map 属于领域语义，提炼会增加版本和维护耦合；将来有第二类真实消费者再评估。

### 对人类决策的影响

采用方案新增本 Skill 的 Pack、host、测试和运行说明；旧单独报告检查仍可运行，但不等于新状态流完成。旧 manifest 不自动推定完成，新 host 显式初始化并重新验证。Kernel 升级在用户运行环境单独安装，当前任务只隔离测试。

## 实施顺序（P0/P1/P2）

- P0：新增 host 与快照校验，拒绝跳阶段/错绑/越界/缺证据；测试异常及恢复。
- P1：接入索引、契约、配置、初始化入口、报告 helper 和文档，检查复制安装后加载与执行。
- P2：同步版本、README 自动技能表、CHANGELOG 与 BAC；不新增模型质量 benchmark。

## 验收与回归测试

运行 Skill 定向 pytest（完整正常路径、回退、缺失与不确定、错 run/attempt、哈希变化、非法 JSON、超时、路径范围、资产复制、索引解析）；上游 Kernel 包内 pytest；文档结构和 Diff 检查。所有临时产物位于本轮工作区。无历史 alias 的新 ID 不人为创造兼容 alias，另测 Kernel 现有 alias 解析不回归。

## 已知不确定性、回退方案和不在范围内的事项

真实文献检索与 Agent 科学审查不属于此次软件接入测试；合成回传只验证协议，不能宣称科学质量已验证。旧 Kernel 必须明确失败，不能降级为字符串状态标签。保持旧 validate_report 接口供结构检查，不把它视为完成替代。非运行安全沙箱，不防恶意宿主直接篡改源码与整条账本。

## 实施结果

P0/P1/P2 已完成。已落地 Pack、宿主、初始化接入、报告 helper、运行指南、测试及版本/贡献记录。33 项 Skill 定向测试、122 项隔离 Kernel 测试、wheel 安装后发现/初始化、文档与 Diff 检查通过。正常阶段和回退按计划实现，未引入额外业务节点。系统旧安装未修改；实际科研语义未做真实模型 benchmark。
