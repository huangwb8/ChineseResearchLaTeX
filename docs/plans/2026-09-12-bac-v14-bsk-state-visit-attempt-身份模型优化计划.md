# bac-v14：BSK State visit / attempt 身份模型优化计划

## 通俗解释：究竟发生了什么

- **一句话说明：** BSK 目前用同一个编号同时表示“从上一站离开”和“在下一站开始工作”，导致下一站想开启自己的检查批次时反而被正确的防伪规则拦住。
- **具体场景：** v14 的文献阶段使用 `literature-1` 通过检查；转到候选阶段后，候选阶段按约定应使用 `candidates-1`。但 State 进入事件仍带 `literature-1`，BSK 因身份不一致拒绝候选阶段离开。
- **对应到本问题：** State visit 表示一次进入某状态的访问，attempt 表示这次访问中的一次验证尝试；二者有关联，但不是同一个生命周期。
- **改变前后：** 当前调用者只能在“全程复用一个 attempt”和“每阶段换 attempt 后被拒绝”之间选择；改进后 Kernel 明确记录 State visit、当前 attempt 及其替代关系，并继续拒绝旧证据复用。

## 专业判断：问题在哪里

- Kernel 2.1.0 的事件追加、required Verifier 聚合、Gate 计算、状态持久化与 State entry identity 不变量在 v14 均按设计工作；问题不是放宽校验，而是现有身份模型表达力不足。
- `state.transition` 是一个事件，却同时承担源 State 离开和目标 State 进入。事件信封只有一组 `run_id/attempt_id`，`check_state_invariants()` 又把该组身份视为目标 State 的进入身份。
- 该模型无法自然表达“用源阶段 attempt 完成离站，同时为目标阶段建立新的 active attempt”，也无法在停留同一 State 时安全轮换重试 attempt。
- 错误恢复文案建议“创建显式新 attempt”，但现有 State invariant 没有对应的安全重绑定入口，建议与能力不完全一致。
- `research-idea` 是首个暴露问题的调用者，但修复必须保持领域无关，不能在 Kernel 中出现 literature、candidate 或科研字段。

## 要达到什么目标

- 将稳定的运行身份、State visit 身份和阶段验证 attempt 分层，明确各自创建、继承、替代和结束规则。
- 一次 transition 能校验源 State 的 active attempt，并原子地为目标 State 建立新的 visit/attempt 身份。
- 在同一 State 内可显式开始重试 attempt；新 attempt 启用后，旧 attempt 的 Verifier、Gate 和 authorization 全部过期。
- 实时执行、崩溃恢复和事件重放产生一致状态，继续保持 fail-closed。
- 为旧事件提供确定性的只读解释，不改写历史日志。

不在本次范围内：执行具体 Skill 的业务动作、理解科研证据、替代领域 Verifier，或扫描外部产物猜测当前 State。

## 改进方向

### 方向一：定义三层身份与状态访问协议

保留 `run_id` 表示整次业务运行；新增明确的 `state_visit_id` 表示一次进入 State 的访问；`attempt_id` 只表示该访问中的一次验证尝试。State 快照应保存当前 visit 和 active attempt，Verifier/Gate/authorization 同时绑定三层身份。

对普通用户的变化：一趟流程、一个站点访问和一次检查重试不再共用同一张编号含糊的票。

### 方向二：提供原子的目标 State 身份交接

扩展 transition API，使调用者提交源 visit/active attempt，并显式请求或由 Kernel 生成目标 visit/initial attempt。Kernel 在同一事务边界内完成源 invariant、目标 entry helper、事件追加和快照提交；不能先转移再补目标身份。

公开字段可以采用 `source_identity` / `target_identity` 或等价结构，但不得继续让事件信封的一组 attempt 隐式代表两侧。CLI 应输出新目标身份，供调用者直接用于下一阶段。

对普通用户的变化：离开上一站和进入下一站的手续一次完成，不会留下身份空窗。

### 方向三：增加 State 内 attempt 轮换能力

提供领域无关的 `attempt start/supersede` 操作：只能在当前 visit 内创建，记录替代原因和前一 attempt，使用幂等键并更新 active attempt。新 attempt 的证据窗口从该事件开始；旧 attempt 仍可审计，但不能满足当前 invariant 或被 authorization 消费。

对普通用户的变化：检查失败后能正式重试，同时保留失败历史，也不会误用旧的通过结果。

### 方向四：统一不变量、Gate 与 action authorization 的窗口

State invariant、required Verifier、Gate、preflight/authorization 和 transition 必须解析同一个 active visit/attempt。任何错 run、错 visit、已 supersede attempt、进入前结果或跨 State handoff 均返回稳定原因码；错误提示只建议 Kernel 真正支持的恢复动作。

### 方向五：版本化协议并保留旧日志可读性

为新事件和快照提升协议版本。旧日志缺少 visit 字段时按旧规则重放并标为 legacy，不推断不存在的新 attempt；新写入不允许降级成旧格式。调用者可通过 capability/协议查询判断是否支持目标身份交接和 attempt 轮换。

## 实施范围与顺序

1. 先写身份状态图和事件协议决策，明确 transition 两侧、attempt supersede、回退与终态的语义。
2. 修改 reducer、State invariant、快照和 transition/attempt API，确保事件与快照原子一致。
3. 让 Verifier、Gate 和 action authorization 消费统一身份解析器，删除分散的隐式比较。
4. 补 CLI/capability、兼容读取、错误码与文档，再用通用 fixture 和至少两个不同 Skill 适配样例验证。

## 如何确认完成

- 通用三阶段 fixture 使用同一 run、不同阶段 attempt 连续推进，第二条及后续 transition 不再出现 entry identity mismatch。
- Verifier 失败后在同一 State 开启新 attempt：旧 Gate、旧 handoff 和旧 authorization 全部被拒绝，新证据可正常放行。
- transition 在事件追加或快照提交任一点故障时可恢复，不能出现目标 State 已写入但目标身份缺失的分裂状态。
- 前进、回退、自环（若声明允许）、终态、并发重复、幂等重放、篡改和 legacy 日志均有回归测试。
- 实时执行与 rebuild 得到相同的 current State、visit、active attempt 和拒绝原因。
- Kernel 测试与源码不包含 `research-idea` 领域 ID；Python 3.11+ 支持矩阵、包构建、CLI smoke、类型/静态检查和 BAC verify 通过。

## 技术补充（按需阅读）

- 新协议的核心不变量应是：`Gate.identity == active_attempt.identity`，且 `active_attempt.state_visit_id == current_state_visit.id`；transition 的源侧按该身份验收，目标侧创建新的 visit。
- `attempt_id` 是否由调用者命名可以保留为接口选择，但唯一性、状态归属和 supersede 顺序必须由 Kernel 验证。
- transition 被业务拒绝时 CLI 应提供机器可判定的非成功状态与稳定原因码；是否采用非零进程退出码需先审查兼容调用者。

## 风险与待确认事项

- 这是事件协议级变更，需要先盘点现有 State/Verifier 调用者；不能只修改 `check_state_invariants()` 而遗漏 action authorization 和 rebuild。
- 自动生成目标 attempt 更安全，但可能影响调用者的可读命名；可由 Kernel 接受 label、生成稳定 ID，并同时返回二者。
- 旧日志只能保持可读和可审计，不能无证据地获得新协议下的完成资格。

