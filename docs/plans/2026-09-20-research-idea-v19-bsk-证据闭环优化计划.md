# research-idea v19 与 BSK 证据闭环优化计划

## 通俗解释

v19 不是“只写出了一份看起来完整的报告”。现场可以重放出 25 条连续的 BSK 事件，五次 State 进入、四次 action 授权与消费、八条 Verifier result 和四个 allow Gate 都真实存在，最终 State 也确实是 `bensz.research-ideation.completed`。报告与三轮独立审查的内容质量总体可信。

缺口出现在控制链的最后一公里：两个最终 Verifier result 记录了完成索引的哈希，但最终 Gate 和 transition 没有保存并消费同一个哈希。现有完成检查只验证“有 Gate、有结果、身份和 applicability 对得上”，没有证明“现在看到的完成索引就是 Gate 当时审核的那一份”。另有一条论文证据在完成索引中被标成全文级，源解读文件却明确是摘要级；当前门禁也没有发现这一冲突。

本计划不重做 v19，也不增加状态或新的语义 Verifier。BSK 补齐通用的 Gate → transition 证据绑定接口；`research-idea` 使用该接口，并负责证据层级、全文升级和 reviewer 回执这些领域语义。历史 v19 保持只读，标记为“业务完成、控制链存在 legacy 未绑定缺口”，不补写旧事件。

## 结论摘要

- v19 的业务工作实质完成，报告结构、候选筛选、查新和三轮审查总体有效。
- BSK State、action authorization、Verifier、Gate、v2 身份链与事件哈希链确实运行；四条前向边的 `hypothesis-merit.applicability` 也符合领域映射。
- v19 运行时使用 BSK 2.1.2；当前本地 2.1.4 能完整读取其 25 条事件，并已具备底层 evidence-binding 能力，但这不等于 Skill State CLI 已接通该能力。
- “端到端不可变完成证明”尚未成立：最终 Gate 缺少完成索引哈希，transition 缺少 `gate_event_id`、`evidence_hash` 和 `evidence_refs`。
- BSK 2.1.4 的底层 API 已具备 evidence binding，但 `bsk state transition` 尚未暴露并执行这条路径；这是跨领域协议缺口，应在 BSK 修复。
- 当前 `research-idea` 0.13.0 仍用旧式 `dependencies.kernel` 声明，并以 PATH 和 shebang 判断解释器；它不能稳定适配 latest 托管 BSK wrapper。
- 保留五个领域 State 和两个 required Verifier。给现有 `stage-readiness` 增加确定性 evidence-consistency 组件，不新增第三个语义 Verifier。
- 不恢复私有 `completion-attestation.json`、第二套事件账本、私有 Gate 或完成运行时；完成证明统一使用 BSK 原生 Gate/transition binding 和事件重放。

## 现场判定

| 检查面 | v19 实际状态 | 判定 |
| --- | --- | --- |
| 报告结构 | `validate_report.py --allow-custom-name` 通过 | 正常 |
| 业务内容 | 候选可证伪，允许强通用日志胜出，限制声明总体克制 | 正常 |
| State | 五次进入后到达 `bensz.research-ideation.completed` | 正常 |
| action authorization | 四次 grant、四次 consumed，身份连续 | 正常 |
| Verifier | 四条边各有两个结果，共八条 | 正常 |
| Gate | 四个 Gate 均为 allow，result refs 和身份可对账 | 基本正常 |
| applicability | `not_applicable / applicable / not_applicable / applicable` | 正常 |
| 事件完整性 | 25 条事件哈希链由 BSK 2.1.4 `EventLog.read()` 验证通过 | 正常 |
| 运行快照 | `research-idea 0.13.0` 的 11 个关键文件无哈希漂移 | 正常 |
| reviewer 执行痕迹 | 3 轮 × 3 份 RESULT/thread/done 存在，轮次内容哈希不同 | 基本正常 |
| 完成索引绑定 | Verifier result 有哈希，最终 Gate 和 transition 没有贯通 | P0 缺口 |
| 证据深度一致性 | 完成索引把一份明确为摘要级的解读登记成全文级 | P0 缺口 |
| latest 托管兼容 | 集成检查报 `invalid_runtime_kernel`；托管环境回归大量失败 | P0 缺口 |
| 当前回归健康 | 同源环境 97 passed、2 failed；失败来自硬编码旧版本 | P1 缺口 |

v19 完成索引的现场 SHA256 为：

```text
sha256:433f072b9e40eb6b3489f422a950a37312e5eda614d8fe8dc03d6c98c2b44831
```

该值出现在最终两个 Verifier result 中，但没有出现在最终 Gate 和 transition 中。现有 `check_completion.py` 仍返回 PASS，因此属于已复现的控制面假阳性，而不是理论风险。

## 业务流程与风险地图

| 流程段 | 业务证据 | 控制证据 | 主要风险 | 责任层 |
| --- | --- | --- | --- | --- |
| 文献 → 候选 | 检索、雷达、解读、研究 map | stage-readiness、merit N/A、Gate | 资料不全却推进 | `research-idea` 语义，BSK 协议 |
| 候选 → 审查 | 候选、决定性近邻、淘汰理由 | 两个 result、Gate | 新颖性判断与索引错绑 | 两层共同 |
| 审查 → 成稿 | 3×3 reviewer 与综合 | merit N/A、Gate | receipt 字段错配仍通过 | `research-idea` |
| 成稿 → 完成 | 报告与 completion index | 两个 result、Gate、transition | Gate 未绑定当前索引，完成检查假阳性 | BSK P0，Skill 消费 P0 |
| 全文升级 | PDF/TXT、全文分析 | 索引 metadata | 摘要解读被错误登记为全文 | `research-idea` P0 |
| 托管启动 | 配置、入口、运行快照 | managed runtime diagnostics | wrapper 被 shebang 检查误拒绝 | `research-idea` P0 |

唯一实施假设 H1：如果 BSK 让 Skill State transition 必须消费同一 source run/visit/attempt 下的 allow Gate，并精确绑定该 Gate 的 evidence hash/refs，而 `research-idea` 同时将当前完成索引和源证据 metadata 纳入确定性对账，则任何索引改写、证据层级虚升、旧 Gate 复用或身份错绑都会在进入 completed 前或最终重放时稳定失败。

## 目标、非目标与历史口径

### 目标

- 新运行中，当前完成索引哈希、两个 Verifier result、Gate 与 transition 使用同一份 evidence binding。
- `check_completion.py` 从 BSK 原始事件或官方查询 helper 重放该绑定，不相信 Skill 自报的完成身份。
- 完成索引的 `source_id`、`evidence_depth`、`read_scope`、稳定引用与源 artifact 一致。
- reviewer 摘要能分别对到账户线程回执、runner 回执和 RESULT 内容。
- latest 托管 BSK wrapper 下能够启动、推进和完成定向回归。

### 非目标

- 不修改、补写或“修复”历史 v19 事件、Gate、索引和报告。
- 不新增领域 State，不改变科研选题、查新或三轮审查的业务方法。
- 不新增第三个语义 Verifier，不让模型承担哈希、路径和 receipt 对账。
- 不在 `research-idea` 内实现事件哈希链、Gate 聚合、transition 校验、completion attestation 或重放协议。
- 不把 `research-idea` 的四条边、证据层级或 reviewer schema 硬编码进 BSK。

### 历史兼容

- v19 与其它无 evidence binding 的旧运行只读兼容，可报告“业务完成、legacy unbound completion”，但不能获得新强认证资格。
- 不根据邻近文件猜测或回填旧 receipt，不把当前文件重新哈希后伪装成历史 Gate 输入。
- 新严格模式启用后，缺少 Gate binding 的新运行必须 fail-closed。

## 删除影响测试

| 候选能力 | 删除或不接入的影响 | 决策 |
| --- | --- | --- |
| 五个领域 State | 丢失阶段恢复点和 visit/attempt 边界 | 全部保留 |
| `stage-readiness` | 无法判断业务材料是否足以推进 | 保留、required；增加确定性一致性组件 |
| `hypothesis-merit` | 关键边无法审问创新性和非平凡性 | 保留、required；不适用边继续显式 N/A |
| 第三个 evidence-consistency 语义 Verifier | 增加模型成本，仍不能替代确定性对账 | 不新增 |
| 私有 completion attestation | 与 BSK 原生 binding 重复并形成第二套真相 | 删除该设计方向，不接入 |
| BSK Gate/transition binding | 当前索引无法与 completed 控制链不可变关联 | 必须接入 |
| reviewer receipt 领域 adapter | 执行身份、状态和结果只能做弱校验 | 保留并强化 |

## Verifier 设计矩阵

| Verifier | 稳定命题 | AI 负责 | 确定性组件负责 | Gate 行为 | 失败处理 |
| --- | --- | --- | --- | --- | --- |
| `bensz.research.stage-readiness` | 当前阶段材料真实、充分且可以推进 | 评价材料覆盖、论证和阶段就绪性 | schema、路径、hash、索引与源 artifact metadata 对账 | 四条前向边 required | 留在当前 State，新 attempt 修复 |
| `bensz.research.hypothesis-merit` | 在适用边评价假设价值；其它边明确不适用 | 创新性、非平凡性、替代方向和投入价值 | source/target → applicability 映射与枚举校验 | 当前四条前向边均 required | applicability 或 verdict 不合格即拒绝 |

证据一致性是 `stage-readiness` 的确定性组件，不是新的领域判断器。它至少核对：

- completion index 与 interpretation frontmatter 的 `source_id`、`evidence_depth`、`read_scope`、`stable_citation`。
- 全文升级记录绑定的 PDF/TXT 内容哈希及对应正式全文解读或升级记录。
- completion index、Verifier result、Gate 与 transition 的 evidence hash/refs。
- 未知 schema、缺失字段、路径越界、symlink、哈希漂移均 fail-closed。

## State 设计矩阵与最小状态图

| State | 稳定含义 | 进入条件 | 离开条件 | 本次变化 |
| --- | --- | --- | --- | --- |
| `literature` | 主题、检索、景观、解读与 map 已启动 | BSK 原子初始化 | 两个 required result 与 allow Gate | 无新 State |
| `candidates` | 候选与关键近邻已形成 | 绑定 literature Gate 的 transition | 两个 required result 与 allow Gate | transition 必须绑定 source Gate |
| `review` | 候选进入独立审查 | 绑定 candidates Gate 的 transition | 3×3 receipt 完成且 Gate allow | receipt 对账增强 |
| `reporting` | 报告与完成索引待最终门禁 | 绑定 review Gate 的 transition | 索引一致、最终 Gate allow | evidence consistency 增强 |
| `completed` | BSK 已消费最终 Gate 并完成可重放转移 | 绑定 reporting Gate、hash、refs 的 transition | 无前向边 | 不增加外部 attestation |

```text
literature → candidates → review → reporting → completed
```

`bensz.workspace.ready` 是系统起点，不计入五个领域 State。返工继续通过现有 attempt supersede/回退契约处理，本计划不推导新的返工边。

## AI/确定性分工与 Evidence Contract

### AI 负责

- 评价文献脉络、候选科学价值、可证伪性、创新性和替代方向。
- 在 applicable 边给出实质 merit 判断，在 N/A 边明确说明不适用。
- 解释 reviewer 的分歧、新发现和对候选排序的影响。

### 确定性代码负责

- 计算文件哈希，限制路径，验证 schema 与枚举。
- 核对 source/target、run、source state visit、source attempt、action authorization、Verifier result、Gate 和 transition。
- 对账 completion index 与源 interpretation/PDF/TXT、reviewer receipt 和 RESULT。
- 重放事件并报告首个控制断点，不自动补写或修复历史数据。

### 通用 Gate binding

最终阶段的两个 Verifier result 必须携带相同的：

```text
evidence_hash = sha256(current completion-evidence.json bytes)
evidence_refs = canonical task-relative evidence references
```

BSK 生成的 Gate 固化该 binding。Skill State transition 必须显式提交 `gate_event_id`、`evidence_hash` 和 `evidence_refs`；BSK 以 transition 的 `source_identity` 核对 Gate 的 run/state visit/attempt，再把 binding 写入 transition 事件。CLI 当前把 transition 事件 envelope 绑定到 target identity，因此不能简单复用“Gate identity 等于 event envelope identity”的校验；应抽出统一 helper，明确校验 source Gate 与 target transition 的跨边语义。

## BSK 改进

### P0：补齐 Skill State transition 的公共 binding 接口

涉及 BSK 仓库的建议落点：

- `src/bensz_skill_kernel/cli.py`
  - 为 `bsk state transition` 增加 `--gate-event-id`、`--evidence-hash`、可重复 `--evidence-ref`。
  - strict-v2 的受保护前向转移缺少 binding 时拒绝；原子初始化和明确的系统边按声明契约豁免，不用领域名称判断。
  - 幂等重试同时比较 Gate 与 evidence binding，参数变化必须报 idempotency conflict。
- `src/bensz_skill_kernel/runtime.py`
  - 提炼通用 Gate-binding 校验 helper，供直接 `EventLog.transition()` 与 Skill State CLI 共用。
  - 校验 Gate 存在、decision 为 allow/allow_with_warnings、属于 transition 的 source run/visit/attempt，且 hash/refs 精确一致。
  - transition 事件持久化 `gate_event_id`、`evidence_hash`、`evidence_refs`，重放投影可直接查询。
  - 防止旧 attempt Gate、错 run/visit、非 allow Gate、错 hash/refs 和不存在 Gate 被消费。
- `tests/runtime/test_cli.py`、`tests/runtime/test_kernel.py`、`tests/runtime/test_state_identity_protocol.py`
  - 覆盖合法链、缺 Gate、旧 attempt Gate、错 hash、错 refs、非 allow Gate、幂等冲突和事件重放。

### P1：统一查询与兼容口径

- 提供稳定的 Gate/result/transition 查询或 invariant helper，返回 source identity、target identity、decision、result refs 与 evidence binding。
- 让 Skill 读取 BSK 投影，而不是复制 Gate 搜索、身份拼接和 hash 比较逻辑。
- 历史无 binding 事件继续可读，但查询结果显式标记 legacy/unbound；不得把“可读取”提升为“严格认证通过”。
- 文档明确直接 transition API 与 Skill State CLI 的身份差异及原子初始化豁免条件。

### BSK 验收

```bash
python -m pytest tests/runtime/test_kernel.py \
  tests/runtime/test_cli.py \
  tests/runtime/test_state_identity_protocol.py -q
```

验收标准：合法链可完成并重放；六类错绑均在写入 transition 前失败；领域名称、边名称和 research-specific evidence 字段不进入 BSK。

## research-idea Skill 改进

### P0：采用 latest 托管声明与单一编排入口

- `skills/research-idea/config.yaml`
  - 将 Kernel 声明从 `dependencies.kernel` 迁到现行的 `runtime.kernel: {name: bensz-skill-kernel}`。
  - 不固定 BSK 版本，不重复声明 Kernel capability。
- `skills/research-idea/scripts/start_workflow.py`
  - 删除 `shutil.which("bsk")` 后读取 shebang 并与 `sys.executable` 直接相等的判定。
  - 改用托管环境约定的固定入口或 BSK 官方 diagnostics/import 检查；shell wrapper 是合法入口，不应被误判。
  - runtime snapshot 继续记录可公开的实现、版本与入口哈希，但不依赖 wrapper 首行推断解释器。
- `skills/research-idea/scripts/phase_entry.py`
  - 保持唯一阶段入口；Gate allow 后读取 BSK 返回的权威 Gate event。
  - 校验 Gate 的 evidence hash/refs 与当前 completion index 一致，再将 `gate_event_id`、hash、refs 传入 `bsk state transition`。
  - 转移失败保持当前 State，不写私有完成证明，不绕过 BSK 直接改 meta-state。
- `skills/research-idea/scripts/check_completion.py`
  - 从 BSK 原始事件或官方查询 helper 获取 result、Gate 和 transition。
  - 强制比较当前 completion index hash == Gate hash == transition hash，并比较 refs 与 source identity。
  - 对 legacy/unbound 现场给出明确诊断，不返回严格 PASS。

### P0：修复证据层级假阳性

- 在现有 `stage-readiness` pack 中增加确定性 evidence-consistency 组件。
- completion index 的 `source_id/evidence_depth/read_scope/stable_citation` 必须与目标 interpretation frontmatter 一致。
- 从 abstract 升级为 fulltext 时，新增正式、可追溯的全文解读或升级记录，直接绑定 PDF/TXT hash；不能把旧摘要解读文件在索引里改标签充当全文证据。
- evidence-depth 冲突必须在 Gate 前失败，并给出源 artifact 和冲突字段。

### P1：强化 reviewer 与论文解读回执

- `skills/research-idea/edge_rules.py`
  - 分别定义 thread receipt 与 runner receipt 的事实来源，不再把 `thread_status`、`runner_status` 都映射到通用 `status`。
  - 对账 canonical `agent_id`、展示标签、模型、input snapshot、started/ended、exit code、output hash 和 RESULT 实际哈希。
  - 未知 receipt schema、缺失 exit code 或身份字段时 fail-closed。
- 对“每篇论文由独立 agent 解读”的声明增加可复核 receipt；若宿主无法提供该证据，则把对外表述收缩为“按论文隔离的解读任务”，不得宣称已证明独立 agent 身份。

### P1：修复回归和 latest 集成

- `tests/research-idea/test_v15_control_flow.py` 不再硬编码 `0.12.0`；从 `config.yaml` 动态读取当前版本，漂移测试必须断言替换实际发生。
- `tests/research-idea/test_completion_convergence.py` 增加 Gate/transition hash、错 refs、legacy unbound 和 evidence-depth 冲突 fixture。
- 新增或扩展 managed-runtime 集成测试，覆盖 shell wrapper、`runtime.kernel` 声明和 latest BSK 真实入口。
- 同步 `SKILL.md`、`README.md`、`references/runtime-guide.md`、`CHANGELOG.md` 与 `config.yaml` 版本；版本只在 `config.yaml` 维护。

### P2：卫生与去重

- 清理 Skill 源码目录中的 `__pycache__`、`.DS_Store` 等发布噪音，并以忽略/打包测试防止复发。
- 删除能够由 BSK 官方查询 helper 替代的 Skill 自定义 Gate 搜索与协议重放代码，只保留 edge applicability、evidence metadata 和 receipt adapter 等领域逻辑。

## Kernel 对接、Gate、重放与资源边界

新运行的 reporting 完成链应为：

```text
completion index bytes
  → two verifier results with identical evidence binding
  → Kernel-computed allow Gate with the same binding
  → Skill State transition consuming that Gate from source identity
  → completed projection
  → read-only completion replay against current bytes
```

- Gate 生成和 transition 必须在 BSK 的锁与 append-only 事件边界内完成；Skill 不直接 append `verification.gate` 或 `state.transition`。
- evidence refs 使用任务内 canonical 相对定位符，不把机器私有绝对路径写入事件。
- completion check 只读，不创建 Gate、不转移 State、不自动修复索引。
- 索引变化必须 supersede 当前 attempt，重新运行 Verifier 与 Gate；旧 Gate 不可复用。
- 模型调用仅用于语义判断；确定性失败不通过增加模型轮次“投票解决”。

## BSK 单一编排入口

正常业务继续只调用：

```text
start_workflow.py → phase_entry.py start/finish/retry → BSK public CLI/API
```

`phase_entry.py` 是 `research-idea` 唯一阶段编排入口，BSK 是唯一 State/Gate/transition 协议实现。`check_completion.py` 是独立只读安全网。任何测试 helper 都不得成为第二个生产入口，任何 legacy adapter 都不得写入新强认证事件。

## Kernel 复用与元 Verifier/State 提炼决策

| 能力 | 归属 | 决策 |
| --- | --- | --- |
| 事件哈希链、run/visit/attempt、Gate、transition binding、重放查询 | BSK | 通用实现并复用 |
| 五个研究阶段及四条 applicability 映射 | `research-idea` | 保留领域定义 |
| evidence-depth、全文升级、稳定引用对账 | `research-idea` 的 stage-readiness 确定性组件 | 不提升为通用语义 Verifier |
| reviewer/interpretation receipt adapter | `research-idea` | 保留领域适配 |
| 新 State | 无 | 不新增 |
| 新语义 Verifier | 无 | 不新增 |
| 私有 completion attestation/runtime | 无 | 禁止恢复 |

只有当 evidence metadata 或 receipt schema 在至少两个不同领域 Skill 中稳定复用后，再评估提炼通用 Pack；本轮不提前抽象。

## 实施顺序

### P0-A：先改 BSK

1. 固化 public CLI/API 参数、source Gate identity 语义和 legacy 行为。
2. 实现通用 binding helper 与 Skill State transition 接入。
3. 补齐负向、幂等和重放测试。
4. 发布或安装到受控 latest 环境后，记录可复现版本与测试结果。

停止条件：合法 binding 可从 Gate 进入 transition，错绑均在事件写入前失败。

### P0-B：再改 research-idea

1. 迁移 `runtime.kernel`，替换 PATH/shebang 检查。
2. `phase_entry.py` 消费 BSK 新接口。
3. `check_completion.py` 重放三方 hash/ref binding。
4. stage-readiness 增加 evidence consistency，先复现 v19 的摘要/全文冲突，再使 fixture 通过。
5. 同步文档、配置版本和 changelog。

停止条件：latest managed integration 通过，篡改索引或伪造证据深度均稳定失败。

### P1：收紧 receipt 与回归

1. 版本化 reviewer receipt adapter，分别对账 thread/runner。
2. 为论文解读增加 receipt 或收缩声明。
3. 移除测试中的版本字面量，加入 legacy/unbound 诊断与 latest 托管集成。

停止条件：同源与 latest 环境定向回归全绿，未知 receipt schema fail-closed。

### P2：卫生与重复逻辑清理

1. 清理不应发布的缓存文件并增加打包卫生检查。
2. 用 BSK 查询 helper 替换 Skill 内重复协议代码。

停止条件：无源码目录运行垃圾，Skill 只保留领域语义。

## 验收与回归测试

### BSK 协议验收

- 合法 allow Gate + 相同 hash/refs + 相同 source identity：transition 成功。
- 缺 Gate、deny Gate、旧 attempt Gate、错 run/visit、错 hash、错 refs：transition 前失败。
- idempotency key 相同但 binding 不同：冲突失败。
- 历史无 binding 事件：可读、显式 legacy，不获得 strict completion。

### research-idea 领域验收

- 当前 completion index、Gate、transition 任一 hash 不同：`check_completion.py` 失败并指出首个断点。
- interpretation 为 `abstract` 而索引声称 `fulltext`：stage-readiness Gate 前失败。
- 合法全文升级：PDF/TXT、升级记录、解读与索引哈希全部匹配后通过。
- thread status 与 runner status 交叉填充、agent ID 不同、exit code 非成功或 RESULT hash 漂移：完成检查失败。
- 四条前向边 applicability 继续严格匹配现有映射。
- latest 托管 shell wrapper 可通过启动诊断并完成最小全链路 fixture。

### 建议命令

```bash
# BSK 仓库
python -m pytest tests/runtime/test_kernel.py tests/runtime/test_cli.py \
  tests/runtime/test_state_identity_protocol.py -q

# ChineseResearchLaTeX 仓库
python -m pytest tests/research-idea -q
python skills/verifier-state-architect/scripts/check_integration.py \
  skills/research-idea
python skills/research-idea/scripts/validate_report.py \
  docs/ideas/<fixture>.md --allow-custom-name
python skills/research-idea/scripts/check_completion.py \
  --task-root .bensz-api/<fixture-task> --report docs/ideas/<fixture>.md
```

正式验收必须保存命令、运行环境、BSK 版本、exit code 和失败摘要；不能只记录“测试通过”。

## 不确定性、回退与非范围

- BSK Skill State CLI 当前 transition event envelope 使用 target identity，而 Gate 属于 source identity；实施前先固定公共契约，避免直接套用底层 API 的同身份假设。
- latest 托管入口的正式 diagnostics API 需以实施时 BSK 当前源码为准；本计划不臆造函数名。
- 若 BSK P0 尚未发布，`research-idea` 必须继续 fail-closed 或停留在旧版只读审计模式，不得在 Skill 内临时复制协议。
- BSK 变更可通过保留 legacy read、仅对新 strict 运行强制 binding 回退；`research-idea` 变更可通过禁用新运行、保留旧现场只读回退。已写事件不得回滚或改写。
- 本计划不评价 v19 研究结论在未来新文献出现后的持续有效性，也不实施 BSK 或 Skill 源码修改。
