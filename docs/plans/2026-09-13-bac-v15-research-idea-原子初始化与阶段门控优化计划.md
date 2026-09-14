# bac-v15：research-idea 原子初始化与阶段门控优化计划

## 通俗解释：究竟发生了什么

- **一句话说明：** `research-idea` 会在最后检查车票，但开工时的取票、进站和登记仍是三件分开的事；漏掉第一次登记后，后面工作即使全部做完也无法证明按规定流程完成。
- **具体场景：** 当前流程像先自行进站、再到每个站点补验票。v15 第一次进入 literature 时没有登记运行身份，后续 Verifier 和 Gate 虽然显示允许，却属于另一张票；候选、查新和审查仍可继续，最终只能降级交付。
- **对应到本问题：** 任务目录是车站，State 是所处阶段，run/state visit/attempt 是运行身份，Verifier 是检查，Gate 是放行票据，`phase_entry.py` 是阶段适配器。
- **改变前后：** 当前错误通常在任务末尾才暴露；改进后，初始化一次建立完整身份，每个阶段开始和结束都核对同一条 BSK 身份链，身份不合法时不启动标准下游工作。

## 专业判断：问题在哪里

- v14、v15 的首次 `workspace → literature` 事件都没有 `run_id`，并使用 `attempt_id=default`；后续新建的身份无法成为当前 State 的合法离站凭据。
- 当前初始化仍分为 `bsk workspace init`、`init_workspace.py` 和裸 `bsk state transition`。最关键的首次身份创建没有纳入唯一确定性入口，正确性依赖 Agent 手工维护多个变量和命令。
- v15 实际运行时使用了 0.9.0 旧入口：事件幂等键缺少当前 0.9.1 已加入的 action 段；系统安装清单显示 0.9.1 在该任务结束后才刷新。源码版本、安装版本和实际执行版本没有形成可审计绑定。
- 现有 `phase_entry.py` 只控制阶段离站，不控制业务阶段开始。Agent 即使收到身份或转移失败，也仍能直接调用下游 Skill 和写入产物；`check_completion.py` 只能在最终交付时拒绝 completed。
- BSK 2.1.1 已提供 State visit、attempt supersede、State-bound Gate 和 action authorization，`research-idea` 仍维持 Kernel 2.1.0 的单 attempt 兼容路径，尚未消费已经落地的新能力。
- v15 的 `bounded_recommendation`、四层完成语义和最终 fail-closed 是正确能力，必须保留；本计划不重新设计科研选题方法。

## 要达到什么目标

- 用一个公开入口原子完成工作区准备、领域参数初始化、运行快照记录和首次 literature State 身份创建。
- 新任务必须使用 BSK v2 State identity；不得产生缺少 run、visit 或有效 attempt 的初始 State。
- 标准工作流在每个业务阶段开始前获得与当前 State 绑定的授权，在阶段产物完成后再通过 required Verifier、Gate 和 transition 离站。
- 运行时记录实际执行的 Skill 版本、关键契约哈希、Kernel 版本和解释器标识，能够识别源码与安装副本漂移。
- 失败、证据变化、重试、回退和中断续跑使用 BSK 2.1.1 原生 visit/attempt 能力，不再以“建立新任务”作为正常恢复方式。
- 保持报告格式、科学证据与控制完成三者分离；任何控制链缺口继续只能交付 `insufficient`、`degraded` 或 `bounded_recommendation`。

不在本次范围内：修改 BSK 通用身份语义、放宽 Premium 查新标准、重写历史 v12–v15 事件，或让 Skill 自建第二套 State/Gate/事件运行时。

## 改进方向

### 原子化首次启动

扩展现有初始化入口，使其调用 BSK 完成 workspace 准备、领域 manifest 建立、运行快照记录和 v2 literature 身份创建。run 与首个 attempt 可接受调用者提供的可读标签，但权威 State visit 由 Kernel 生成并返回。任一步失败都不得留下“领域资料已初始化但 State 身份不可用”的半成品。

对使用者而言，开工只执行一个入口，不再手工拼三条命令或记忆身份参数。

### 把阶段开始授权放到业务主路径

为 literature、candidates、review、reporting 定义稳定的阶段 action。启动该阶段的下游 Skill 前，适配器先向 BSK 请求 State-bound preflight；只有当前 visit/active attempt 与 action 匹配才返回可消费授权。阶段汇总后，再由现有 Verifier/Gate/transition 完成离站。

这不能阻止用户任意写文件，但可以保证官方 `research-idea` 工作流不会在 State 错误后继续调度下游步骤。

### 消费 BSK 2.1.1 原生身份生命周期

启动时基于 capability 而非单纯版本号确认 `state_visit_identity`、`attempt_supersede`、`state_bound_verifier_gate` 和 `state_bound_action_authorization`。每次进入新 State 使用新的 visit/initial attempt；Verifier 失败或证据变化时在当前 visit 内 supersede attempt，旧 handoff、Gate 和授权自动失效。

删除“全程复用同一个 attempt”的生产兼容路径；如仍需支持 Kernel 2.1.0，只保留明确标为 legacy、不可宣称完整运行的只读诊断路径。

### 固化实际执行版本与环境

启动时记录实际 Skill 根、`config.yaml` 版本、阶段脚本和 State/Verifier 契约哈希、Kernel 版本、能力集合及解释器指纹。记录采用项目相对标识或哈希，不把本机绝对路径写入报告或 BAC。检测到 `python` 与 `bsk` 不属于同一环境、安装副本晚于任务启动更新或源码/安装哈希不一致时，在业务开始前拒绝。

### 强化完成证据与独立审查 provenance

`completion-evidence.json` 从 BSK 当前 completed visit/attempt 和运行快照派生绑定字段，不允许人工选择权威身份。独立审查除 RESULT 哈希外，还应核对 thread/runner 的结束状态；缺完成标志时只能标记为有内容但执行 provenance 不完整。

### 收敛文档和错误语义

`SKILL.md`、运行指南、README 和 State 文档只保留一个正式启动入口和一个阶段推进入口。错误码明确区分安装版本漂移、解释器错配、legacy identity、action 未授权、Verifier 不通过和 State transition 失败，并在首次错误处停止。

## 实施范围与顺序

1. 先冻结 `research-idea` 对 BSK 2.1.1 capability、v2 初始身份、阶段 action 和运行快照的消费契约，并把 v15 脱敏现场作为失败基线。
2. 实现原子启动入口，移除普通运行文档中的裸初始 transition，确保新任务不再生成 legacy State。
3. 为四个业务阶段接入开始前 authorization 和结束时 Verifier/Gate/transition，贯通 attempt supersede、回退与续跑。
4. 让完成索引、审查 provenance 和环境诊断消费同一运行快照；同步配置、State/Verifier 契约、README、CHANGELOG 和 Skill 版本。
5. 在源码版和安装版分别执行真实五阶段回归，确认安装同步后再做新的业务实战。

## 如何确认完成

- v15 脱敏 fixture 稳定返回 `legacy_state_identity`，不写入新的 Verifier/Gate，也不启动 candidates 工作。
- 新任务只调用一次启动入口即可进入带非空 run、visit、attempt 的 literature；删去任一身份字段均在产生首条 State 事件前失败。
- 从 literature 到 completed 的真实五阶段流程通过；每个阶段都有开始授权、业务产物、两项 required Verifier、Kernel Gate、State transition 和目标 visit。
- Verifier 失败后 supersede attempt 能重新审查；旧 handoff、旧 Gate、旧 action authorization 和旧完成索引均被拒绝。
- 模拟项目源码 0.9.1、安装副本 0.9.0 时，启动前报告 `skill_runtime_drift`；同步安装后运行快照能证明实际版本与关键哈希一致。
- 模拟默认 Python 加载旧 Kernel、`bsk` 属于新环境时，启动前报告 `kernel_interpreter_mismatch`，不把它误报成 capability 缺失。
- 第一、二轮审查只有 RESULT、没有完成回执时，不再计入完整独立审查；完整 runner/thread 证据可正常通过。
- `validate_report.py`、`check_completion.py`、research-idea 定向测试、Skill 文档检查、安装后 smoke、`git diff --check` 和 BAC verify 全部通过。

## 风险与待确认事项

- 阶段 action authorization 的目的，是约束官方调度路径，不应声称能够阻止任意外部文件写入。
- 原子启动需要 BSK 提供严格身份初始化接口；在 BSK 修复发布前，Skill 侧只能做 preflight 和拒绝，不能复制 Kernel 持久化逻辑。
- 是否继续声明兼容 Kernel 2.1.0，应以真实能力矩阵决定；若生产路径依赖 2.1.1，应提高最低版本，而不是在同一入口维护两套复杂语义。
- 旧任务保持只读可审计，禁止通过补写身份或回填 Gate 获得新的 completed 资格。

