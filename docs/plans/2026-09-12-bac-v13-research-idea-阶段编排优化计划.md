# bac-v13：research-idea 阶段编排优化计划

## 通俗解释：究竟发生了什么

- **一句话说明：** 当前流程像只有入口检票，后面的候选、查新、审查和报告可以绕过检票继续前进。
- **具体场景：** v13 只留下 `workspace.ready → literature`，但候选、Premium 查新、synthetic review 和最终报告仍然生成。状态机记录的是“人还在文献阶段”，文件却已经走到了报告阶段。
- **对应到本问题：** State 是当前所在窗口，Verifier 是阶段验收，Gate 是下一阶段的放行凭证；下游 Skill 目前没有必须持有凭证的入口。
- **改变前后：** 现在 Agent 可以直接调用下游 Skill；改进后，未先通过当前阶段 Gate 的请求会在产生下游产物前失败，并留下可恢复的 attempt 记录。

## 专业判断：问题在哪里

- v13 的唯一状态转移发生在初始化；后续业务动作没有调用 `bsk state transition`，因此没有 Verifier、Gate 或 State 事件。
- `research-idea` 的 `SKILL.md` 将业务步骤连续描述，控制章节和 `runtime-guide.md` 才说明如何手工提交验证，导致协议依赖 Agent 记忆而不是入口约束。
- 2026-09-10 删除 `idea_runtime.py`、`phase_evidence.py` 后，没有留下新的 state-aware 必经入口；“直接使用 CLI/API 足够”的假设被 v12/v13 时序证据否定。
- 旧的完成检查主要判断最终报告和终态，不能阻止阶段越级，也不能识别全部产物完成后再补录 Gate 的情况。

## 要达到什么目标

- 任意候选、查新、review、reporting 动作都只能从与当前 State 匹配的入口启动。
- 阶段结束时自动形成 Verifier 输入、绑定结果、Gate 和 State transition；Agent 不再手工拼接关键控制事件。
- 每次阶段执行都绑定 `run_id`、`attempt_id`、输入 manifest 和证据快照；失败、暂停、回退和续跑均可恢复且不覆盖历史。
- v13 这类现场在重放时被明确判为“阶段越级/控制证据缺失”，不能被追认为完整运行。

不在本次范围内：修改 BSK Kernel 的通用实现、证明科研结论正确、替用户重跑昂贵的文献检索，或修改历史报告内容。

## 改进方向

### 方向一：建立唯一的 state-aware 阶段入口

新增或恢复 `research-idea` 的统一编排入口，负责读取当前 State、校验允许的动作、创建 attempt、生成输入 manifest，并向下游 Skill 发放带状态和哈希绑定的 handoff。候选、查新、review、reporting 不再接受无 handoff 的直接启动。

对普通用户的变化：流程会在错误阶段立即停下，而不是先产出一堆之后无法认证的文件。

### 方向二：把 Verifier、Gate、transition 嵌入阶段边界

每个阶段使用固定的“进入 preflight → 执行业务 → 结束验证 → Gate → transition”顺序。`required` Verifier 缺失、返回 `uncertain/unchecked`、证据哈希变化、目标 State 不匹配或 attempt 过期时默认拒绝。

对普通用户的变化：通过下一阶段不再依赖 Agent 是否记得手工补几条事件。

### 方向三：为下游产物建立时序和来源契约

候选、novelty、review、reporting 产物必须声明来源阶段、attempt、生成时间、内容哈希和上游 handoff。下游 Skill 启动前执行 preflight；产物生成后若没有相应阶段事件，完成收敛直接失败。

对普通用户的变化：每份结果都能回答“在哪个阶段、基于哪次输入、经过哪次放行产生”。

### 方向四：保留诚实的失败和阶段性结果

查新失败、证据不足或依赖不可用时，停留在当前阶段并记录失败 Gate、重试位置和降级原因。`insufficient` 或 bounded recommendation 可以交付，但不能伪装成已完成完整状态链。

## 实施范围与顺序

1. 先在 `research-idea` 的运行契约和阶段文档中固定动作—State—Gate 映射及 fail-closed 规则。
2. 再实现统一入口、handoff/preflight 和阶段结束收敛，优先覆盖 candidates、review、reporting 三个越级点。
3. 更新 `SKILL.md`、`references/runtime-guide.md`、报告模板和配置，使文档步骤与真实入口一致。
4. 最后补充兼容读取、历史 attempt 标记和迁移说明；旧事件只读，不自动补写新事件。

## 如何确认完成

- 在 `literature` 状态直接请求 candidates、review 或 reporting 时，在写入下游产物前失败，并记录原因、当前 State 和恢复位置。
- 正常路径中每个阶段均出现匹配的 Verifier、Gate 和 State transition，且 Gate 时间早于下游产物。
- 先生成全部产物再批量回填 Gate/State 的 fixture 必须被拒绝。
- 回退或续跑创建新 attempt；旧 attempt 的 Gate、产物和报告仍可审计但不能复用。
- v13 现场重放结果为越级/证据缺失，而不是 `completed`；`git diff --check`、Skill 定向测试、文档校验和 BAC verify 通过。

## 技术补充（按需阅读）

- 领域 State 保持 `literature → candidates → review → reporting → completed`，失败/等待通过事件表达，不新增无稳定语义的状态节点。
- 领域判断仍由 `research-idea` 的 Verifier 契约和 Agent 完成；通用身份、Gate、事件和持久化复用 BSK，不在 Skill 内另建账本或状态机。
- 必须新增回归样本：越级启动、事后回填、错 `run_id/attempt_id`、Gate 后证据变化、依赖失败和中断续跑。

## 风险与待确认事项

- 现有调用者可能依赖直接写文件或直接调用下游 Skill，需要提供明确的兼容错误信息和迁移入口。
- 强制 preflight 会暴露过去被隐藏的证据缺口，旧任务应降级为只读审计，不应静默补证。
- 真实文献和 review 的科学质量仍需领域人工判断；本计划只保证执行路径和控制证据不再缺失。
