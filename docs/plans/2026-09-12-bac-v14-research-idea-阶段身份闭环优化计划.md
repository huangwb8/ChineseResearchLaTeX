# bac-v14：research-idea 阶段身份闭环优化计划

## 通俗解释：究竟发生了什么

- **一句话说明：** `research-idea` 已经会在阶段出口验票，但入口票和下一站票使用了互相冲突的编号，所以科研工作继续完成了，控制流程却停在第一站。
- **具体场景：** v14 像一趟五站列车：文献、候选、审查、报告、完成。文献站的两项检查都通过，闸机也显示允许离站，但初次进站没有登记运行编号；即使补上编号，现行说明又要求到候选站更换 attempt，仍会与闸机保存的进站编号冲突。
- **对应到本问题：** State 是所在车站，Verifier 是阶段检查，Gate 是放行结果，`run_id/attempt_id` 是本次访问身份；`phase_entry.py` 是把这些 BSK 操作连起来的薄适配器。
- **改变前后：** 当前会出现“报告已生成、State 仍在 literature”；改进后每个阶段都从 BSK 取得当前有效身份，完成验证后以明确的下一阶段身份转移，业务产物与控制事件保持同一条时间线。

## 专业判断：问题在哪里

- v14 的科研内容链实质执行，报告以 `insufficient` 诚实披露查新不足；10 个文献证据哈希一致，三轮审查产物齐全。这些已正常工作的能力应保留，不应因控制链缺陷而重写。
- BSK 日志只有 4 条事件：首次进入 literature、两个 required Verifier pass 和一个 Kernel allow Gate；没有 literature → candidates，后续候选、审查和报告均未形成控制事件。
- 直接原因是运行指南的首次 State transition 不带身份，而 `phase_entry.py` 强制后续使用 `run_id/attempt_id`。
- 更深层原因是“每阶段新 attempt”与当前 State entry identity 语义不兼容：上一条 transition 的 attempt 同时成为目标 State 的进入身份，下一阶段换新 attempt 后无法离开该 State。
- 当前 31 项定向测试中 3 项失败，均指向这一身份矛盾；现有 fixture 以无身份进入 literature，却期待带身份退出成功，测试预期已不符合 Kernel 2.1.0。
- 这不是单纯补一个初始化参数即可彻底解决的问题。稳定修复依赖配套的 [BSK State visit/attempt 身份模型计划](2026-09-12-bac-v14-bsk-state-visit-attempt-身份模型优化计划.md)。

## 要达到什么目标

- 初始化、四个阶段出口和最终完成形成一条真实可重放的 State/Verifier/Gate 链。
- `research-idea` 只保留领域流程与薄适配，不自建 State、Gate、事件扫描、锁或私有 attempt 账本。
- 正常推进、阶段重试、回退和续跑都有明确身份语义；旧 Gate 或旧 attempt 不能被复用。
- 控制链失败时在开展下游业务前停止，并给出当前 State、有效身份和可执行恢复位置。
- 保持报告四层完成语义与 `check_completion.py` 的 fail-closed 行为。

不在本次范围内：重新设计科研选题方法、放宽 Premium 查新标准、修改历史 v14 事件或把领域规则写入 BSK。

## 改进方向

### 方向一：统一初始化与阶段身份契约

初始化 literature 时必须创建非空 `run_id` 和由 BSK 认可的首个阶段 attempt。后续入口不再把任意命令行 attempt 当作事实，而是核对 BSK 当前 State visit 与 active attempt；缺失、错配或已被替代时在生成 Verifier handoff 前拒绝。

对普通用户的变化：第一次进入流程时就登记完整身份，不会到第一次离站才发现票号不一致。

### 方向二：按 BSK 原生生命周期推进阶段

在 BSK 提供 State visit 与 attempt 轮换接口后，薄适配器固定执行“读取当前访问 → 开始或恢复阶段 attempt → 运行 required Verifier → Kernel Gate → 转移并登记目标阶段身份”。目标阶段身份由 BSK transition 返回，不由 Skill 猜测或写入私有文件。

若 BSK 新接口尚未落地，只允许提供显式标注的兼容路径：同一身份完成无重试的直线路径，并在重试或回退时 fail-closed；不得把它宣称为完整修复。

对普通用户的变化：Agent 不需要记忆多条底层命令，也不能跳过身份交接。

### 方向三：让失败、重试与恢复成为正式路径

Verifier 未通过时保持当前 State，并由 BSK 显式开启新 attempt、替代旧 attempt；证据变化后必须重新生成 handoff 和 Gate。回退边也使用同一套访问/attempt 契约，旧结果只读保留但不可继续放行。

对普通用户的变化：修订材料后可以安全重试，不必删除日志或伪造一次“从未失败”的运行。

### 方向四：收敛文档、脚本和完成诊断

同步 `SKILL.md`、运行指南、`phase_entry.py`、初始化说明和完成检查：只保留一个正式入口；示例命令必须携带真实身份；错误输出区分“业务证据不足”“身份错配”“Kernel 不兼容”和“尚未进入下一 State”。`check_completion.py` 继续作为交付前的独立安全网，并引用导致未完成的首个控制事件。

## 实施范围与顺序

1. 先冻结 research-idea 对 BSK 新身份接口的消费契约，并保留 v14 作为失败基线。
2. 等 BSK 身份模型可用后，修正初始化和薄适配器，使目标阶段身份由 Kernel 原子返回。
3. 接入重试、回退和续跑，删除文档中“每次检查自行换 attempt”这类与真实接口冲突的描述。
4. 更新配置、README、Skill CHANGELOG、根 CHANGELOG 与版本号；旧现场只读兼容，不回填事件。

## 如何确认完成

- 在 Kernel 2.1.0 基线上，v14 脱敏 fixture 仍被准确识别为 State 身份断链，而不是误判 completed。
- 在目标 Kernel 上，从 workspace.ready 到 completed 的五阶段 CLI 集成测试通过；每个 State 都有进入身份、required Verifier、allow Gate 和离开事件。
- 第二阶段使用不同 attempt 能正常推进；错 attempt、旧 handoff、旧 Gate、证据变化和跳阶段均在写入下游产物前失败。
- 至少覆盖一次 Verifier 失败后重试、一次回退再推进和一次中断续跑；实时状态与事件重放结果一致。
- 正常路径的报告校验与完成收敛均通过；`insufficient` 等阶段性结果仍可交付，但不会被标成 completed。
- research-idea 定向测试、Skill 冒烟、文档/配置校验、`git diff --check` 与 BAC verify 通过。

## 风险与待确认事项

- BSK 新身份协议是前置依赖；在它稳定前只修文档或首次命令会留下第二阶段必现故障。
- 薄适配器不得重新膨胀成第二套 Kernel。任何通用身份、重放和并发逻辑都应留在 BSK。
- 旧事件没有目标阶段身份字段，只能按旧协议只读解释，不能自动升级后获得新的完成资格。

