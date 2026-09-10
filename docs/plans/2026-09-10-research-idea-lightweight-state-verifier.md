# Verifier/State 设计计划：research-idea 轻量化

## 结论摘要

2026-09-10：基于当前 Skill（配置版本 0.5.1）、已安装并核验的 bensz-skill-kernel 1.0.3 / Python 3.12，以及上游当日 AGENTS.md 与 skill-pack-hosting.md 制定。保留五个真实业务阶段和一个自然语言阶段验证器，删除 Skill 自建运行时与机械证据 Pack；以 Markdown 约定直接调用 Kernel CLI/API。实现由 skill-creator 接续，不修改 Kernel 或系统安装副本。

## 业务流程与风险地图

文献调查 → 候选及查新 → 独立审查 → 报告 → 完成。必须保留研究线/O/R 锚点、价值与投入分离、Premium 查新、约定轮次及人数、零候选与 insufficient 边界。科学判断由读取真实来源的 Agent 完成；文件存在、字段完整和模型自信不能证明科研充分性。

## 删除影响测试（含“不接入”结论）

- 保留阶段及语义验证器：否则无法明确恢复位置、前置证据与完成边界。
- 删除 idea_runtime.py：其锁、事件回放、Gate、绑定和状态持久化由 Kernel 提供，不在 Skill 重建。
- 删除 phase_evidence.py 与 Pack 脚本：取消额外证据快照系统；角色覆盖和科学独立性按契约检查，文件与路径可选用内置 Verifier。
- 保留 validate_report.py：它检查本 Skill 的报告格式和三种 outcome，属于领域功能。
- 精简 init_workspace.py：仅生成研究任务参数、候选空模板和正式报告路径；工作区创建直接交给 bsk，不生成状态或事件。

## Verifier 设计矩阵

| 候选 | 结论 | 命题与输入 | Gate / 失败 |
| --- | --- | --- | --- |
| stage-readiness | 保留单一 Agent 组件 | subject.operation/source/target、研究设置、真实证据引用；前进判断充分性，回退判断返工必要性 | required；非 pass 停留，返工通过不表示研究完成 |
| evidence-shape | 删除脚本组件 | 角色覆盖与轮次保留在语义契约，报告格式由已有 helper 检查 | 不再声称自动重算所有证据文件 |
| 通用文件/路径/引用检查 | 按需使用内置组件 | 按各内置输入契约 | advisory 检查不能替代 required 阶段审查 |

## State 设计矩阵与最小状态图

| 状态 | 不可删除的含义 | 离开证据 |
| --- | --- | --- |
| literature | 候选尚无文献基础 | theme/radar/interpretation/map |
| candidates | 待筛选和查新 | candidates/novelty |
| review | 待独立批判性审查 | review/synthesis |
| reporting | 待报告一致性检查 | report + 报告格式结果 |
| completed | 完成且不可续写 | 前置充分性、最终报告一致；不接受 insufficient |

内置 workspace.ready → literature → candidates → review → reporting → completed。各中间阶段可退回图中更早阶段；等待/取消记录原因并停止，不增加领域状态。每个非终态离开时使用 Kernel 原生 verifier-result-recorded、verifier-gate-allow、required-verifiers-pass。State 无脚本组件。

## AI/确定性分工与 Evidence Contract

Agent 读取证据，检查非空角色、成员覆盖、独立审查及语义，给出 summary、confidence、uncertainties、evidence_refs、verdict；不能用置信度阈值替代判断。Kernel 承担 Pack 解析、handoff/bind_result、结果协议、Gate、身份和日志/状态。validate_report 只验证领域格式。

证据以 ref/source_type/summary/content_hash 索引；request.context 保存 source/target 对应的任务设置及路径映射。内容变化、语义改写、返工或契约变化后由 Agent 重新读取并建立新 attempt；不再维护自动 checkpoint/hash 失效引擎。保留 uncertain/unchecked 与人工补证据路径。

## Kernel 对接、Gate、重放与资源边界

- 直接用 bsk workspace init --task-root、bsk state transition --skill-root、bsk status/rebuild；领域快照由 TaskWorkspace.read_meta_state 读取。rebuild 仅修复通用投影，不能宣称能重建领域快照。
- 本地 Verifier 的普通 CLI 发现尚不可用，用文档里的 FilesystemVerifierRegistry.run_contract / handoff.bind_result / EventLog.record_verification 调用，不新增运行时脚本。
- run_id 固定，attempt_id 每次检查唯一；同一身份传给验证与转移。Kernel 验证绑定，Agent 核对当前来源/目标、证据内容和最近结果。中断在通过和转移之间时先核对证据再续行；快照损坏或提交不完整停止并保留日志。
- 当前 State 加载器对 runtime.kernel.version 做字符串全等，不能接受 >=1.0.3。最低依赖要求移至 dependencies.kernel；runtime 仅维护 State/Verifier 声明。安装器负责版本范围，实际验证固定 1.0.3，不编写版本解析器。
- 限定授权项目相对路径与必要摘要；禁止路径穿越、私有指令和敏感数据。大型文献只引用必要来源；Kernel 执行超时沿用其参数，不重写 sandbox/锁/事件引擎。

## Kernel 复用与元 Verifier/State 提炼决策

已读取安装包 states/index.json、verifiers/index.json、states.py、cli.py、workspace.py、contract_packs.py、runtime.py，以及 workspace-ready 和下列相关内置契约。内置组件均为 1.0.0；包本体为 1.0.3。

| 候选能力 | 内置 ID / 版本 | 复用方式、契约差异 | 跨领域 / 提炼 | 验证 |
| --- | --- | --- | --- | --- |
| 工作区入口 | bensz.workspace.ready / 1.0.0 | 直接复用，literature 声明入口 | 是 / 已有 | CLI 首次进入 |
| 文件、路径 | bensz.artifact.file-existence、bensz.artifact.path-scope / 1.0.0 | 按需直接用 subject.path(s)、allowed_paths | 是 / 已有 | 存在/越界 |
| 来源字段 | bensz.evidence.provenance / 1.0.0 | 非必需；只检字段，不重算 hash，空列表也可 pass | 是 / 不扩展 | 不充当充分性 |
| 引用核验 | bensz.document.markdown-link-integrity、bensz.evidence.citation-truth-fit / 1.0.0 | 按需组合；可达性与语义分开 | 是 / 已有 | 不可观测保留未知 |
| 完成 | bensz.runtime.task-completeness / 1.0.0 | 不采用；truthy 字段不表达科研完成 | 是 / 不扩展 | 三种 outcome |
| 科研阶段与充分性 | 无完全匹配组件 | 留 Skill 契约，稳定 canonical ID 不变 | 否 / 不提炼 | 图和 Agent 绑定 |

### Kernel 复用结论

- 复用工作区、状态图、原生 invariant、组件执行/绑定和 Gate；直接 CLI/API 足够，不需要 Skill 自有控制框架。
- 文件/引用组件按其实际契约选用；来源字段和一般完成标记不能代替科研充分性。保留小型领域格式脚本成本低于抽象通用验证器。

### Kernel 元组件提炼结论

- 不提炼新 Kernel 组件：需共享的身份、Gate、日志能力已有实现。
- 科研价值、Premium、零候选语义依赖本 Skill，无两个不相邻领域的稳定复用证据；新增通用组件只增加维护责任。

对维护者的影响：移除旧 init/prepare/submit/status 宿主接口，改文档和集成测试；旧报告读取保留，旧事件只读，不自动迁移。Pack 契约升主版本，Skill 在 0.x 开发阶段升次版本并显式标记接口不兼容。

## 实施顺序（P0/P1/P2）

- P0：先更改契约、索引、runtime 声明及运行文档；验证 required 缺失、不确定和错误绑定不能推进。
- P1：删除重复运行代码，精简初始化；替换旧宿主测试为直接 Kernel 集成和文档示例测试，保留报告质量回归。
- P2：更新 README、CHANGELOG、贡献记录；检索活跃文档中的旧命令引用，完成复制安装后发现验证。

## 验收与回归测试

运行 tests/research-idea：报告三种结论、非法图边、缺失/uncertain Gate、Agent 待处理和错绑、合法推进/回退、终态、文档 API 示例、工作区初始化和独立复制。运行 scripts/validate_skill_docs.py、README 列表检查、git diff --check、BAC verify。测试合成回传只验证协议，不冒充真实科学结论。

## 已知不确定性、回退方案和不在范围内的事项

不新增 Kernel，不更新系统技能，不执行真实科研选题，不重跑昂贵多 Agent 科研评测。取消自动文件哈希重检后由 Agent 在每次转移前重读并核对证据，这是明确的保障范围变化。保留旧运行，不能把新契约追认给旧结果；有未完成提交的领域快照使用 Kernel 修复入口或停止处理，不由 Skill 自行实现恢复引擎。
