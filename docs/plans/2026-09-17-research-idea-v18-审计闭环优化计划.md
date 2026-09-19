# research-idea v18 审计闭环优化计划

## 通俗解释

v18 的研究工作确实完成了，BSK 的 State、Verifier 和 Gate 也真实运行；问题不在“有没有执行”，而在最后的证明材料还留有三个缝隙：Gate 验过的完成索引后来又被改写，reviewer 摘要没有逐项核对原始回执，一条本应“不适用”的科学价值验证被误写成“适用”仍获放行。

这次优化不重做科研流程，也不增加更多状态或模型评审。目标是把现有控制链收紧成可重放、可对账、篡改即失败的闭环：Gate 前的业务证据一旦消费便不再变化；进入 completed 后另写 Kernel 完成证明；reviewer 摘要必须能回到原始 runner 回执；每条前向边都按固定规则核对 `hypothesis-merit` 是否适用。

## 结论摘要

- 保留 `literature → candidates → review → reporting → completed` 五个 State，不把完成索引或 attestation 建成新 State。
- 保留 `stage-readiness` 与 `hypothesis-merit` 两个 Verifier，不增加新的语义 Verifier。
- P0 修复 Gate 后索引漂移：将 Gate 前业务证据索引与 completed 后 Kernel completion attestation 分离，任何一方被改写都令完成检查失败。
- P0 修复 applicability 漏检：在单一编排入口提交前、Gate allow 后转移前、最终事件重放时核对全部四条前向边。
- P1 修复 reviewer 对账：索引保存原始 receipt 引用与快照，完成检查逐字段对照 `thread.json`、`done.json` 和 RESULT 内容。
- BSK 继续只负责协议、身份、Gate 和事件；哪条研究边需要 `hypothesis-merit` 属于 `research-idea` 领域规则，不写入通用 Kernel。
- 当前 completion-v5 和历史事件只读兼容，不补写、不伪造新回执，也不自动获得新的严格完成证明资格。

## 专业判断与风险地图

| 缺陷 | v18 证据 | 当前漏检位置 | 风险 | 优先级 |
| --- | --- | --- | --- | --- |
| Gate 后完成索引漂移 | reporting Gate 消费的索引哈希与当前文件哈希不同，但完成检查通过 | Gate 输入、completed 身份与最终文件没有不可变串联 | 报告可显示 completed，但无法证明当前索引就是 Gate 审阅版本 | P0 |
| reviewer 索引未与回执对账 | r1b、r1c 的起止时间被写成 r1a 时间，9 个 RESULT 哈希仍匹配 | 只检查摘要字段非空，不读取原始 runner receipt | 错误或伪造的执行身份、模型、时间和状态可能进入完成证据 | P1 |
| applicability 误标仍获放行 | `review → reporting` 被写成 `applicable/pass`，契约要求 `not_applicable` | Kernel 只检查 required result 协议；完成检查只看最终边 | 不适用回执可能被误解为科学价值认证，并污染审计语义 | P0 |

风险边界：这些缺陷不否定 v18 的实际科研产物、25 条 BSK 事件、5 次 State transition、4 次 action authorization、8 次 Verifier result 和 4 次 allow Gate；它们否定的是“当前文件集合已经构成不可变端到端证明”这一更强结论。

### v18 现场与责任归属

本计划的判断以 `/Volumes/2T01/Github/bensz-auto-contribution/docs/ideas/v18.md` 和 `task-20260915-2107-课题方向-v18` 中的现场为准：

- `research-idea/output/completion-evidence.json` 仍是 `research-idea-completion-v5`，记录了 `idea-run-v18`、最终报告快照、依赖产物和 9 个 reviewer 摘要，但没有独立的 completed 后 attestation；因此索引不可变性和完成身份串联属于 Skill 完成证据设计与 BSK Gate 绑定共同缺失的问题。
- `research-idea/log/runtime-snapshot.json` 显示 v18 使用 `research-idea 0.12.0`、BSK Kernel `2.1.2`，已有 state visit、attempt、Gate 和严格身份能力；所以本计划不是从零设计状态机，而是补足证据引用和重放接口。
- `log/events.ndjson` 的最终 reporting Gate（`seq=24`）只留下两个 verifier 的 `result_refs`，随后 `seq=25` 转入 completed；事件没有把 Gate 实际消费的业务索引哈希作为通用 evidence binding 固定下来，这是 BSK 需要补的协议能力。
- v18 的 reviewer 原始文件位于 `parallel-vibe/2026-09-15-21-59`、`22-07`、`22-26` 各轮目录。`completion-evidence.json` 中的摘要字段与这些 `thread.json`、`done.json`、`RESULT.md` 尚未形成逐字段、逐哈希的完成检查，这是 Skill 需要补的 receipt adapter 和对账逻辑。
- 事件中 `literature → candidates` 的 merit 结果为 `not_applicable`，`candidates → review` 为 `applicable`，最终 reporting 边为 `applicable`；计划中的 applicability 规则应由 Skill 提交并重放，BSK 只负责确保 required result、Gate 和 transition 引用的是同一次受权运行。

## 目标与非目标

### 目标

- Gate 消费的业务证据索引在 Gate 后保持字节级不可变。
- completed 后的权威身份、Gate、transition、报告和业务索引由独立 attestation 串联。
- reviewer 摘要可逐字段追溯到原始 thread、runner 和 RESULT 回执。
- 全部四条前向边的 `hypothesis-merit.facts.applicability` 与领域契约一致。
- 正常运行继续通过；任何哈希、身份、回执或 applicability 漂移均 fail-closed，并指出首个断点。

### 非目标

- 不修改历史 v18 现场、旧 Gate、旧事件或旧 completion-v5 文件。
- 不重新设计研究选题、文献雷达、查新、三轮审查或报告内容标准。
- 不增加 State、语义 Verifier、私有事件账本或第二套 Gate。
- 不把 `research-idea` 的边适用性硬编码进 BSK。
- 不绑定某个 BSK 具体版本；实施时先确认 latest 生产运行时的真实接口。

## 两个责任层分别怎么改

这次不是把所有缺陷都塞进 `research-idea`，也不是要求 BSK 理解研究语义。v18 的材料显示，问题同时落在两个责任层：Skill 生成并解释领域证据，BSK 负责把一次运行的身份、Gate 和转移做成不可绕过的协议记录。

### `research-idea` Skill：负责领域规则、业务证据和完成检查

Skill 需要优化的是“什么证据算对、哪条研究边适用什么检查，以及如何把 reviewer 的业务摘要对回原始回执”：

- 在 Skill 内维护唯一的 `source → target → expected applicability` 映射。`literature → candidates` 和 `review → reporting` 必须是 `not_applicable`，`candidates → review` 和 `reporting → completed` 必须是 `applicable`。`phase_entry.py` 在提交前、收到 Gate allow 后转移前各检查一次，`check_completion.py` 在事件重放时再检查一次。
- 将 Gate 前的 `completion-evidence.json` 定义为一次 attempt 的只读业务索引。它保存报告、依赖产物、查新、审查轮次以及每个 reviewer 的原始 receipt 路径、哈希和规范化快照；索引一旦作为 Gate evidence 被消费，Skill 不得原地更新，证据变化必须开启新 attempt。
- 新增 completed 后才生成的 `completion-attestation.json`，把已消费的业务索引哈希、报告哈希、Gate/transition/completed 身份串起来。该文件由 `phase_entry.py` 在成功转移后原子生成；`check_completion.py` 只读验证，不负责补写。
- 为 reviewer receipt 增加版本化 adapter，逐字段核对 `thread.json`、`done.json`、runner 状态、起止时间、模型、输入 snapshot、退出码、output hash 和实际 RESULT 文件；字段缺失、版本未知、路径越界或任一哈希漂移都拒绝签发严格完成证明。
- 将 `completion-v5` 作为 legacy 只读输入，只能给出诊断，不能从邻近文件猜测回执或自动升级为新 attestation。同步 `SKILL.md`、运行指南、report template、CHANGELOG、`config.yaml` 和专项 fixture。

这部分的验收对象是研究流程本身：领域映射不会被误写，Gate 消费的业务证据不会静默变化，reviewer 摘要能回到原始回执，历史现场不会被伪造补齐。

### BSK：负责通用协议、权威身份和 Gate 绑定

BSK 不应知道 `hypothesis-merit` 在哪条研究边适用；它需要优化的是让 Skill 提供的领域证据无法脱离一次受保护的运行链：

- 扩展 Gate/handoff 的通用证据绑定接口，使 Gate 记录实际消费的 evidence hash（以及必要的 evidence ref），而不是只记录 `result_refs`。Gate allow 后，任何 evidence hash、handoff、attempt 或 action authorization 不一致都不能继续 transition。
- 保持并强化 run/state visit/attempt、action authorization、Gate、transition 的权威身份串联和 append-only 事件语义；transition 只能消费当前 visit/attempt 的已授权 Gate，旧 Gate、旧 handoff 或错 action authorization 必须被拒绝。
- 提供可重放的 Gate/result/transition 查询接口，让 Skill 的 `check_completion.py` 能从事件投影读取事实，而不是依赖 Skill 自己复制一份“看起来正确”的身份字段。BSK 只验证协议身份和引用完整性，业务文件内容仍由 Skill 核验。
- 若 latest BSK 支持 action/edge-specific required Verifier，提供通用的 action 元数据或 required-set 能力，让调用方按边声明 required 集合；若暂不支持，至少保证 Skill 仍能在 Gate 前后做领域 applicability 检查。不得把 `research-idea` 的四条边硬编码进 Kernel。
- 明确 transition 成功与外部完成 attestation 写入是两个结果：BSK 不替 Skill 生成业务 attestation，也不因 attestation 写入失败回滚已经提交的 transition；同一 transition receipt 可以被确定性重试读取。

这部分的验收对象是协议安全性：即使调用方传入旧结果、改过的文件哈希或伪造的 completed 身份，BSK 也不能把它们重新包装成一次新的合法转移。

### 两层之间的接口边界

`research-idea` 提交：`source/target`、业务 evidence hash、两个 verifier result 和领域 applicability；BSK 返回：Gate decision、权威 Gate 身份和 transition receipt。Skill 再用这些返回值生成 attestation 并执行最终重放。BSK 不解释报告科学内容，Skill 不自行制造 Kernel 身份；任一层发现不一致都 fail-closed。

## 删除影响测试

| 候选 | 删除或不接入的影响 | 决策 |
| --- | --- | --- |
| 五个现有 State | 会丢失阶段恢复点、visit/attempt 身份与可重放转移链 | 全部保留 |
| `stage-readiness` | 无法判断阶段产物和流程输入是否足以推进 | 保留、required |
| `hypothesis-merit` | 无法在关键边审问创新性、非平凡性和推荐/淘汰质量 | 保留；当前全局 required 兼容路径继续使用 |
| 新的“completion” State | 与现有 completed 重复，且把证据对象误当生命周期状态 | 不接入 |
| 新的 receipt/attestation 语义 Verifier | 对账与哈希核验是确定性工作，调用模型只会增加成本和不确定性 | 不接入 |
| Kernel 通用文件完整性 Verifier | 不能替代 reviewer 字段语义和领域 applicability 规则 | 本轮不设为 required |

## Verifier 设计矩阵

| Verifier | 保留/删除 | 稳定命题 | AI 与确定性分工 | Gate 行为 | 失败处理 |
| --- | --- | --- | --- | --- | --- |
| `bensz.research.stage-readiness` | 保留 | 当前 source → target 的阶段材料真实、充分且流程可推进 | AI 判断证据语义；脚本核对绑定、枚举、文件哈希和结果身份 | 四条前向边均 required | 非 pass、错绑或证据漂移时留在当前 State |
| `bensz.research.hypothesis-merit` | 保留 | 在关键边认证候选/最终结论的科学价值；其它边明确不适用 | AI 只在适用边做价值审问；脚本依据边映射校验 applicability | latest BSK 不支持 action-specific required 时继续全局 required | 适用性错误、非 pass、错绑或未知值均不得 transition |

前向边的唯一领域映射如下：

| source → target | 期望 applicability |
| --- | --- |
| literature → candidates | `not_applicable` |
| candidates → review | `applicable` |
| review → reporting | `not_applicable` |
| reporting → completed | `applicable` |

返工边继续遵循现有 rework 契约，不凭本计划推导新的适用性规则；若未来要让返工边进入严格完成重放，应先显式版本化其映射和测试。

## State 设计矩阵与状态图

| State | 稳定含义 | 主要进入证据 | 主要离开证据 | 本次变化 |
| --- | --- | --- | --- | --- |
| literature | 已建立主题、检索、景观、解读和研究 map | workspace ready 与初始身份 | 文献阶段 required Gate | 无 |
| candidates | 已形成候选及决定性近邻核对 | literature transition receipt | 候选阶段 required Gate | applicability 强校验 |
| review | 已进入独立审查与综合 | candidates transition receipt | review 阶段 required Gate | receipt 对账、applicability 强校验 |
| reporting | 已形成报告和完成前业务证据 | review transition receipt | reporting required Gate | 消费不可变业务证据索引 |
| completed | 控制链已完成且可生成最终证明 | reporting transition receipt | 无前向离开 | 新增外部 attestation，不新增 State |

最小状态图保持：

```text
literature → candidates → review → reporting → completed
```

完成证据是状态链的证明材料，不是状态本身。

## AI/确定性分工与 Evidence Contract

### AI 负责

- 判断阶段证据是否支持推进。
- 在 `candidates → review` 和 `reporting → completed` 做真实 hypothesis-merit 审查。
- 在不适用边明确返回 `not_applicable`，不得把流程通过描述成科学价值通过。
- 解释 reviewer 的新增发现、分歧和候选影响。

### 脚本负责

- source/target 到 expected applicability 的唯一映射。
- handoff、result、Gate、run/state visit/attempt、action authorization 和 transition 身份核对。
- 文件路径规范化、哈希计算、原始 receipt 读取、字段对账和事件重放。
- Gate 前业务索引与 Gate 后 attestation 的原子写入和 schema 校验。
- 发现未知枚举、缺失字段、错绑、路径越界或内容变化时 fail-closed。

### 两层完成证据

1. `research-idea/output/completion-evidence.json`：Gate 前生成的业务证据索引。包含报告、依赖产物、查新、审查轮次、reviewer receipt 引用及其快照；reporting Gate 消费后禁止再写。
2. `research-idea/output/completion-attestation.json`：仅在 reporting → completed 成功后由单一编排入口原子生成。包含业务索引哈希、当前报告哈希、reporting Gate 身份/哈希、transition 身份/哈希、completed run/visit/attempt 和运行契约快照引用。

attestation 不能反向改变 Gate 输入，也不由完成检查自行生成。这样可以消除“Gate 前文件要求预先写入尚未产生的 completed 身份”这一循环依赖。

## Gate、完成证明与事件重放

### reporting Gate 前

- 完成业务索引，校验 schema、路径、报告哈希、依赖产物哈希和 reviewer receipt 对账。
- 计算并固定业务索引哈希，将其作为 reporting handoff/Gate 的明确 evidence ref。
- Gate 创建后不得再修改业务索引；如业务证据变化，必须开启新 attempt 并重新生成 handoff、Verifier result 和 Gate。

### Gate allow 后、transition 前

- `phase_entry.py` 从 Gate 的实际 `result_refs` 重新读取两个 required result。
- 核对 result 与当前 run/state visit/attempt、source/target、handoff hash 及 expected applicability。
- 任一不一致时拒绝 transition；已有 allow Gate 保留为失败审计证据，不得当作可复用票据。

### transition 成功后

- 从 BSK 返回值和事件投影取得 completed 权威身份，不由 Agent猜测。
- 原子写入 completion attestation；写入失败不回滚已发生的 Kernel transition，但完成状态保持“控制链已转移、交付证明未收敛”，可使用同一 transition receipt 重试确定性 attestation 生成，不重跑 Gate。
- 禁止补写或改写 Gate 前业务索引。

### 最终完成检查

`check_completion.py` 只读执行以下重放：

1. 验证 attestation schema、运行快照和路径边界。
2. 验证当前业务索引哈希等于 attestation 记录值，也等于 reporting Gate 实际消费的 evidence hash。
3. 验证当前报告哈希等于业务索引与 attestation 的共同记录值。
4. 验证 Gate 的 result refs、reporting source identity、transition receipt 和 completed target identity 首尾相接。
5. 按事件顺序重放四条前向边，并核对每条边的两个 required result、Gate decision 和 applicability。
6. 逐轮逐 reviewer 核对 receipt、RESULT 和 completion index；任一字段不一致即失败。
7. 输出 `first_control_break` 和稳定错误码，例如 `gate_evidence_hash_mismatch`、`reviewer_receipt_mismatch`、`merit_applicability_mismatch`。

## reviewer 原始回执对账

completion 新 schema 中每个 reviewer 至少记录：

- RESULT 文件路径及内容哈希。
- `thread.json` 与 `done.json` 的任务内相对路径及各自内容哈希。
- `thread_id`、实际模型、输入 snapshot hash、started/ended、thread status、runner status、exit code、output hash 的规范化快照。

完成检查以原始 receipt 为事实来源，并将索引快照逐字段与其对照；只验证“字段非空”不再足够。规则如下：

- receipt 缺失、JSON 损坏、路径越界、字段缺失或哈希不一致均 fail-closed。
- `thread_id`、模型、输入哈希、起止时间、状态、退出码、输出哈希任一不一致均报出具体 reviewer 和字段。
- 结束时间不得早于开始时间；runner/thread 均须 completed，exit code 须符合成功契约。
- output hash 必须同时匹配 done receipt 与实际 RESULT 文件。
- completion-v5 只读解析时不从邻近文件猜测或回填 receipt；最多给出 legacy 诊断，不能签发严格 attestation。

## BSK 单一编排入口

继续使用 `skills/research-idea/scripts/phase_entry.py` 作为正常业务的唯一阶段入口：

- `start` 消费当前 State-bound action authorization。
- `finish` 执行提交前 applicability 检查、请求 Kernel Gate、Gate 后实际 result 复核、允许时 transition。
- reporting → completed 成功后，由同一入口调用确定性 helper 原子生成 attestation。

`check_completion.py` 保持独立只读安全网，不创建 Gate、不转移 State、不修复历史数据。receipt 解析、哈希规范化和 applicability 映射可抽成同 Skill 内的小型纯函数模块，供入口和完成检查共用，避免两套规则漂移；它不是第二套运行时。

## Kernel 复用与元组件提炼决策

| 能力 | 归属 | 决策 | 理由 |
| --- | --- | --- | --- |
| run/visit/attempt、Gate、transition、事件 | BSK | 直接复用 | 属于跨领域协议与权威身份 |
| action-specific required Verifier | BSK 可选增强 | 实施时探测 latest；可用时另行评估迁移，不阻塞本计划 | 可消除不适用边的占位结果，但当前不能假定存在 |
| source/target 对 merit applicability 的映射 | research-idea | 保留在 Skill | 是领域语义，不适合写入通用 Kernel |
| reviewer receipt 语义与完成 schema | research-idea | 保留在 Skill | 与本 Skill 的三轮独立审查契约绑定 |
| 通用不可变 evidence/attestation 协议 | 暂不提炼 | 完成两次跨领域复用后再评估 | 当前只有单一领域实例，过早抽象会增加兼容面 |

BSK 上游若未来支持 edge/action-specific required Verifier，可让不适用边不再生成 `hypothesis-merit` 占位结果；迁移前必须确认事件重放和旧现场兼容，不得删除 Skill 侧的最终语义校验。

## 实施顺序

### P0：`research-idea` 建立不可变完成证明，BSK 提供证据绑定接口

- **Skill：** 修改 `phase_entry.py`、`check_completion.py` 和完成证据文档，定义新 completion schema 与 attestation schema；reporting Gate 只消费 Gate 前业务索引，transition 后只写 attestation。
- **BSK：** 提供并记录 Gate 实际消费的 evidence hash/ref，并在 Gate 后拒绝 handoff、attempt、授权或 evidence hash 的错绑；不把业务索引内容复制成 Kernel 自己的第二份事实。
- **联调：** 用 BSK 返回的权威 Gate/transition/completed 身份生成 attestation，增加报告 hash、索引 hash 和身份首尾相接的闭环验证。
- 完成条件：Gate 后修改业务索引或报告时，完成检查稳定失败；正常链可从 immutable index 生成并验证 attestation。

### P0：`research-idea` 覆盖全部前向边，BSK 保证 required-set 可被可靠消费

- **Skill：** 建立单一 source/target 映射纯函数；`phase_entry.py` 在提交前和 Gate 后各检查一次，`check_completion.py` 重放四条边。
- **BSK：** 若有 action/edge-specific required Verifier 接口则接入通用 required-set；若没有，继续消费 Skill 提交的两个 required result，但不替 Skill 判断适用性。
- 完成条件：`review → reporting` 的 `applicable` 被拒绝，两个关键边的 `not_applicable` 被拒绝，其余两个非关键前向边的 `not_applicable` 通过。

### P1：`research-idea` 完成 reviewer receipt 对账，BSK 暴露可重放回执

- **Skill：** 扩展新 completion schema，保存 receipt 路径、哈希与规范化字段快照；在完成检查中读取 thread/done/RESULT 并逐字段核对，输出 reviewer 定位信息。
- **BSK：** 提供 Gate/result/transition 的只读事件查询和稳定引用，确保 Skill 对账时取得的是该次 run/visit/attempt 的原始协议回执，而非后来拼装的摘要。
- 完成条件：时间、状态、模型、输入哈希、退出码或输出哈希任一漂移都能被定向测试捕获。

### P1：文档、版本与诊断收敛

- 同步 `SKILL.md`、`README.md`、`references/runtime-guide.md`、report template、Skill CHANGELOG、根 CHANGELOG 和 `config.yaml`。
- 版本只改 `config.yaml:skill_info.version`；若实施时基线仍为 0.12.0，建议按 schema 变化升级到下一个 minor 版本。
- 增加稳定错误码和 first-control-break 摘要，避免只输出笼统“完成检查失败”。

### P2：可选 BSK 上游增强

- 核对 latest 生产 BSK 是否已有 action/edge-specific required Verifier、evidence hash binding 和可重放查询接口。
- 若已有，单独制定兼容迁移；若没有，向 BSK 提交最小通用需求，但 `research-idea` 的 P0/P1 不等待该能力。
- 可选评估论文解读 batch receipt；它是审计增强，不属于本次三项正式缺陷的阻塞项。

## 分层验收矩阵

| 场景 | `research-idea` Skill 期望结果 | BSK 期望结果 |
| --- | --- | --- |
| 正常四阶段前向链 | 四个 Gate 与 transition 可重放，完成检查通过 | 只接受当前 visit/attempt 的授权 Gate 并产生首尾相接 receipt |
| Gate 前业务索引与 completed attestation 正确分离 | 两个文件身份清楚，前者无 completed target identity 循环依赖 | Gate 固定实际消费的 evidence hash，不要求预写 completed 身份 |
| Gate 后修改业务索引 | 报告 `gate_evidence_hash_mismatch`，失败 | 后续调用无法用旧 Gate 继续合法 transition |
| 当前报告哈希与 Gate/attestation 记录不一致 | 失败 | 返回可重放的 Gate/transition 身份供 Skill 定位 |
| reviewer started/ended 任一不一致 | 定位到 reviewer 和字段，失败 | 提供原始 result/事件引用，不接受摘要替代 |
| reviewer 状态、exit code 或 output hash 不一致 | 失败 | 不因 Skill 的摘要字段而放宽协议引用 |
| `review → reporting` 使用 `applicable` | transition 前拒绝，完成重放亦失败 | 只验证 required result 与当前边/授权一致，不解释领域语义 |
| `literature → candidates` 使用 `not_applicable` | 允许 | 消费 Skill 提交的合法 required result 集 |
| `candidates → review` 使用 `not_applicable` | 拒绝 | 若支持 action-specific required，则按调用方声明的 required-set 执行 |
| `reporting → completed` 使用 `not_applicable` | 拒绝 | 不替 Skill 生成 attestation |
| 复用旧 attempt、旧 handoff、旧 Gate 或错 action authorization | 拒绝 | 协议层 fail-closed |
| completion-v5 历史现场 | 只读诊断，不生成严格 attestation | 保留 legacy event read，不伪造新身份 |
| 当前回归基线 | 现有 98 项继续通过，并新增三类专项用例 | 新增 evidence binding、重放和错绑拒绝用例 |

实现后的定向验证至少包括：Skill 的新旧 schema fixture、四条边参数化测试、receipt 每字段突变测试、索引/报告哈希突变测试；BSK 的 evidence binding、旧 Gate/错授权拒绝和事件重放测试；一次真实 latest BSK 托管集成 smoke、Skill 文档与配置校验、`git diff --check` 和 BAC verify。

## 兼容、迁移与回退

- 新运行只写新 schema；旧 completion-v5 保持只读，不原地升级。
- 历史现场需要严格证明时，应从可信业务证据开启新 attempt、重新执行 required Verifier 和 Gate，而不是补写旧记录。
- attestation 写入失败可基于同一成功 transition receipt 重试确定性生成；不得重放 transition 或制造第二个 completed 身份。
- 若新检查误伤正常路径，回退代码和 schema 写入口，但保留已经写入的新文件只读；不得删除事件或把失败改写成 pass。
- 若 latest BSK 接口与计划假设不同，先冻结生产运行时证据并调整 Skill 适配层，不通过固定旧版本规避。

## 不确定性与范围外事项

- 当前 BSK 是否已提供 action-specific required Verifier 必须在实施当天以 latest 生产运行时为准，本计划不预设答案。
- 原始 runner receipt 的字段名可能因执行器版本不同而有合法差异；实现时应先形成受版本约束的规范化 adapter，再比较统一字段，未知版本 fail-closed。
- attestation 原子写入不等于密码学签名；本计划保证内容寻址、身份串联和可重放，远程签名或可信时间戳另行设计。
- 本计划不证明 AI 的科研判断一定正确，只保证“哪些判断由谁、基于什么证据、在哪条边被消费”可核对且不可静默漂移。
