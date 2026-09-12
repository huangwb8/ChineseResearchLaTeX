# research-idea 全面优化实施计划

## 通俗解释：究竟发生了什么

- **一句话说明：** v12 的“流程收据”已经齐全，但收据齐全不代表文献查新充分、审查真正独立或科学结论已经成立。
- **生活类比或具体场景：** 现在像是银行系统确认“申请表、签名和审批栏都填了”，却没有确认附件是否是真实原件、审批人是否独立阅读过材料，也没有确认申请内容本身是否足以支持放款。
- **对应到本问题：** 表单对应 State/Gate/完成证据；附件对应检索、全文、论文解读和 ground truth；审批对应 semantic Verifier 与 parallel review；放款对应 `recommended/completed`。
- **改变前后：** 当前只要产物存在且状态正确就可能完成；改进后必须分别证明“产物存在、阶段确实执行、证据深度达标、结论可在当前范围内成立”，缺一项就只能交付阶段性结果。

## 专业判断：问题在哪里

### Skill 设计问题

1. 完成收敛检查偏重路径、非空文件和状态字段，未验证内容是否支持声明，也未校验文件哈希、生成时间和来源绑定。
2. `execution_status=complete` 与证据充分性、查新等价性和科学可信度混为一谈，导致“Premium 已完成”被误读为“新颖性已确认”。
3. Premium 查新没有硬性全文、多源和强近邻等价性门禁；依赖 runner 崩溃后可以用 task-local workaround 继续，却仍可标记 complete。
4. 论文解读没有统一的来源深度、稳定 ID、实际读取范围、方法/结果/限制和证据引用契约。
5. Semantic Verifier 主要接受主 Agent 的结构化声明，不能独立判断文献、审查和科学结论的真实性。
6. parallel review 只有计划和结果文件，没有真实 thread、输入快照、上下文隔离和执行轨迹，无法强证明独立性。
7. BSK 只按 `run_id/attempt_id` 汇总 State invariant 所需事件，未把 Verifier/Gate 限定在“当前 State 最近一次进入之后”；同一 attempt 的旧通过结果可能跨阶段复用。它仍不能、也不应替代领域侧证明真实科研工作发生的时间。
8. 续跑后工作区 README 未自动更新，历史 insufficient 与最终 completed 并存，缺少 authoritative attempt 和 superseded 关系。

### 本次执行问题

1. v12 的检索实际以 OpenAlex 为主，很多近邻仅有摘要、网页或预印本页面；研究 map 和 interpretation 可用于选题，但不等于投稿级全文综述。
2. 13 份论文解读较短，证据粒度不足以支持“已充分排除等价工作”。
3. 9 份审查结果有差异但高度收敛，且没有足够执行元数据证明真实独立。
4. 报告中的 `recommended/complete` 比中间证据更强，虽有边界免责声明，仍存在过度认证风险。
5. 实验所需的独立 ground truth、审计者、攻击样本和 baseline evidence views 尚未建立；当前只能推荐 feasibility spike，不能证明 BAC 的实际增益。

### Skill 外部问题

1. `research-literature-search` 的 `primary_source=null` 崩溃是依赖工具缺陷；临时 workaround 不能作为稳定生产路径。
2. BAC 当前为本地、unsigned、无外部锚定账本，只能证明本地日志结构完整，不能证明现实贡献真实发生或记录无遗漏。
3. “贡献边界”涉及意图、采纳、重写、工具反馈和审批，天然需要独立编码手册、标注一致性和隐私/伦理边界。
4. 研究结论从单一 BAC 仓库抽象而来，存在自我适配、单工具链偏置和跨仓库外推不足。
5. 2026 年近邻多为快速变化的预印本，查新结论必须在正式投稿前重跑。

### BSK 责任判断

- **确属 BSK 的通用缺口：** State invariant 的证据窗口必须从当前 Skill 最近一次进入当前 State 的事件开始；窗口之前的 `verification.result` 与 `verification.gate` 即使 `run_id/attempt_id` 相同也不得放行。本项只涉及领域无关的事件顺序、运行身份和迁移审计，应在 Kernel 修复并做回放回归。
- **BSK 已提供、应直接复用：** Pack/契约/组件/handoff 哈希，`run_id/attempt_id` 绑定，required/advisory Gate 的 fail-closed 聚合，追加式事件和 State 快照。`research-idea` 不再实现第二套锁、Gate、绑定、事件账本或重放器。
- **不属于 BSK：** Premium 查新充分性、论文读取深度、证据—结论矩阵、ground truth 和 reviewer 独立性都是 `research-idea` 的领域命题，应放在专用 State/Verifier Pack、依赖产物契约和完成收敛检查中。BSK 不按 verifier ID、finding ID 或科研字段硬编码判断。
- **术语修正：** `artifact_ready`、`execution_recorded`、`evidence_sufficient`、`claim_eligible` 是四个正交完成维度，不是四个 BSK State，也不新增 Kernel verdict/状态枚举；领域 State 仍保持 literature → candidates → review → reporting → completed。

## 要达到什么目标

- `recommended` 只表示“当前证据足以进入下一阶段研究”，不再暗含实验或论文级新颖性成立。
- `completed` 同时具备可追溯的阶段执行记录、证据深度声明、依赖来源绑定、审查独立性证据和可复核的最终快照。
- Premium 查新在全文或明确降级条件下可解释；依赖失败、全文不足或强近邻未核验时自动降级为 `insufficient`/`degraded`。
- 任何人可从一次运行恢复：使用了哪些输入、哪些来源、哪些 Agent、哪一版文件、为什么通过或停止。
- v12 这类结果应诚实归类为“高潜力选题 + feasibility spike 建议”，不把 BAC 当 ground truth 或作者裁判。

不在本次计划范围内：直接开展 8–12 个 session 的科研实验；重构 BAC 核心账本协议；保证作者身份认证；修改系统级 Skill；替用户发布论文或上传外部服务。

## 改进方向

### 方向一：重建分层完成模型和报告契约

增加四个完成维度：`artifact_ready`（产物存在）、`execution_recorded`（阶段执行可追溯）、`evidence_sufficient`（达到该阶段最低证据深度）、`claim_eligible`（结论可交付）。它们属于 `research-idea` 的报告和完成证据契约，不扩展 BSK State 或 verdict 枚举。报告 frontmatter 和 `completion-evidence.json` 分别记录这些维度、证据深度、降级原因和恢复位置。

`check_completion.py` 继续负责机械收敛，但必须校验来源哈希、文件大小/时间快照、manifest 与事件的 attempt/run 绑定；semantic Verifier 只在证据充分性满足后判断科学价值。`recommended` 允许作为 bounded recommendation，`completed` 只能在四层均满足时成立。

对普通用户的变化：系统会明确告诉用户“流程做完了”与“结论证据够不够”是两件事。

### 方向二：修复文献检索和 Premium 查新证据链

修复 `primary_source=null` 的 runner 崩溃，并为每条记录保留稳定 ID、DOI、来源 URL、全文/摘要状态、PDF 获取结果、检索时间和失败原因。Premium 最低契约应包含多源策略、强近邻清单、等价性检查和未覆盖风险；只有摘要或网页时自动标记证据深度不足，不得写成无条件 complete。

对普通用户的变化：报告中的“查新完成”将能回到具体论文和读取范围，而不是只回到一个候选数量。

### 方向三：统一论文解读和研究 map 的证据格式

为 `research-literature-interpretation` 输出增加最小字段：`source_id`、`evidence_depth`、`read_scope`、问题、方法、关键结果、限制、对候选的支持/反驳、稳定引用。研究 map 中区分规范级、全文级、摘要级、网页级和源码级证据，并把待验证综合判断单独列出。

对普通用户的变化：可以看出哪些结论来自原文，哪些只是 AI 的综合推断。

### 方向四：使 Gate 和 Verifier 具备内容级、时序级约束

先在 BSK 修复通用时序窗口：离开 State 时，只接受当前 Skill 最近一次进入该 State 之后、且与当前 `run_id/attempt_id` 一致的结果和 Gate；同一通过结果不得跨阶段复用。该修复只读取标准事件字段，不认识 `research-idea` 的领域 ID 或证据字段。

`research-idea` 在每个阶段开始时生成输入 manifest，在阶段结束时生成带内容哈希的证据清单，并把摘要作为 BSK Evidence/事件 snapshot 交给专用 Pack。BSK 负责绑定和回放这些已提交的快照，不负责扫描任意外部文件或判断科研证据是否充分。若 Gate 后来源内容变化，完成收敛检查应拒绝旧快照并要求新 attempt；不能把文件大小和修改时间当作内容哈希的替代品。

为 semantic Verifier 增加“证据—结论矩阵”：每条高风险结论必须关联具体来源、反例检查和不确定性；无法核对时返回 `uncertain` 而不是 `pass`。

对普通用户的变化：系统不能在材料完成后悄悄补一组通过记录来追认完成。

### 方向五：恢复 parallel review 的真实独立性

为每个 reviewer 保存 thread ID、模型、输入快照哈希、启动/结束时间、是否可见上一轮结果、输出哈希和失败状态。每轮必须有不同判断任务；汇总文件引用全部原始结果。若只生成了角色化草稿而没有真实独立执行，应标为 `synthetic_review`，不能计入 required independent review。

对普通用户的变化：三份意见的“独立”将有执行证据，而不只是三个文件名。

### 方向六：补齐科研语义的 ground truth 和可行性门禁

在 Skill 中增加研究前置检查：贡献边界编码手册、独立真值来源、标注者一致性、审计任务、隐私/伦理审批、baseline evidence views 和最小实际重要差异。没有这些材料时，输出只能是 `insufficient` 或 `bounded_recommendation`。

对 v12 的具体落地建议是：先构造 8–12 个受控 session，使用任务脚本、编辑器/终端记录、Git patch、测试输出和人工确认表生成独立真值；BAC 仅作为被测视图之一。

### 方向七：修复工作区、文档和历史状态管理

续跑或回退后自动更新任务 README，标记 `current_attempt`、`supersedes`、最终权威报告和停止原因。历史 insufficient 保留但不可与当前 completed 混淆。同步更新 `SKILL.md`、README、运行指南、报告模板、config、CHANGELOG 和交叉引用。

对普通用户的变化：打开任务目录时能直接知道哪一次结果有效、哪一次已经被替代。

### 方向八：把依赖故障和 BAC 可信边界显式化

依赖 Skill 或检索器异常时保留失败证据，不用静默 workaround 掩盖；必要时输出 degraded 状态。报告模板固定说明 BAC 的本地完整性、签名/外部锚定状态，以及不能证明的内容。对单仓库选题增加跨工具、跨任务和投稿前重跑查新的风险提示。

对普通用户的变化：不会把本地哈希链误解为现实世界的作者认证或不可篡改证明。

## 实施范围与顺序

1. **先修复并验证 BSK 的通用时序缺口。** 增加“当前 State 进入前的通过结果不可复用、进入后的新结果可以推进、事件回放结论一致”的 Kernel 回归；这是本计划唯一需要修改 BSK 的事项。
2. **再建立业务基线和回归样本。** 保存 v12、早期 insufficient 运行、依赖崩溃和当前 completed 运行的脱敏 fixture，定义四维完成模型及既有领域状态迁移表。
3. **随后修复完成收敛与 State/Gate 接入。** 让系统拒绝“文件齐全但证据不足、attempt 不匹配、Gate 后来源内容变化”的运行；复用 BSK 的绑定、Gate、事件和快照，不建设 Skill 自有运行时。
4. **随后修复检索和解读依赖。** 解决 null 字段崩溃，加入全文/摘要/网页证据深度和 Premium 降级门禁。
5. **接着增强 Verifier 与 parallel review。** 加入证据—结论矩阵、真实执行元数据、上下文隔离和 reviewer 独立性判定。
6. **最后补齐科研前置条件和文档。** 增加 ground truth/标注/隐私/跨工具检查，更新 Skill 文档、配置、CHANGELOG 和工作区最终化逻辑。
7. **以 v12 作为反向验收。** 旧 v12 不应被静默改写为“曾经完整”；重跑后应明确显示：哪些阶段通过、哪些只达到阶段性推荐、哪些证据需要补齐。

## 如何确认完成

- 旧 v11/v12 现场测试能正确区分 `insufficient`、`degraded`、`bounded_recommendation` 和 `completed`。
- 任一依赖文件被修改、删除、替换或跨 attempt 引用时，完成收敛检查失败并指出恢复阶段。
- Premium 只有在全文/摘要深度和强近邻等价性契约满足时才可作为推荐结论的必需依赖；runner 崩溃有可定位失败记录。
- 每篇论文解读都包含稳定来源、读取范围、证据深度和限制；研究 map 能区分来源关系与待验证综合判断。
- parallel review 测试能证明每轮 reviewer 数量、输入隔离、输出哈希和汇总覆盖；无法证明独立时自动降级。
- Verifier 测试覆盖“结构通过但语义证据不足”“查新未完成”“报告与事件状态矛盾”“Gate 后证据变化”等反例。
- BSK 回归证明当前 State 进入前的结果/Gate 不能用于离开该 State；进入后的同身份新结果可推进，`status/rebuild` 后结论不变，Kernel 源码中不出现 `research-idea` 的领域 ID 或字段。
- 工作区 README 与 meta-state、报告 frontmatter、completion evidence 和 BAC 记录保持一致，并能恢复历史 attempt 关系。
- 完成代码和文档验证：`python -m pytest -q tests/research-idea`、Skill 自带测试、文档/JSON/YAML 检查、`git diff --check`、BAC inspect/verify；若涉及检索器，再加入隔离环境下的 runner 回归。
- 人工抽查至少一轮：从最终报告反向定位到来源、解读、查新、审查和事件；抽查结果记录为验证证据，不替代自动测试。

## 风险与待确认事项

- **兼容性：** 旧任务没有新字段时只能走只读兼容路径，不能凭旧字段认证新完成；需要明确迁移和降级规则。
- **成本：** 多源全文查新和真实独立审查会增加时间、网络和 token 成本，应允许明确的阶段性结果，但不能伪装成完整结果。
- **隐私：** ground truth、prompt、录像和审计者数据必须最小化、脱敏并单独授权，不能写入 BAC 或公开报告。
- **外部研究变化：** 近邻文献变化会使既有 novelty 结论失效；投稿前必须新建 attempt 重跑，而不是修改旧事件。
- **职责边界：** BSK 只修复通用事件时间窗口并继续负责绑定、Gate、事件与回放；证据 manifest 的产生、内容变化判断和科研语义留在 `research-idea` 专用 Pack/完成检查。本计划不让 Kernel 替代研究团队对实验设计、伦理审批、统计功效和论文署名的判断。
- **回滚：** 每个阶段以独立配置和新 attempt 发布；若新 Gate 误拒旧任务，可回退到只读兼容验证，不删除旧事件、不覆盖旧报告、不修改系统级 Skill。
