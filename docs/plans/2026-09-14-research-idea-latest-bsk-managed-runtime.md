# Verifier/State 设计计划：research-idea

## 结论摘要

- 决策日期：2026-09-14；目标 Skill 版本：0.10.0；经系统安装器确认的最新生产 BSK：2.1.2。
- 保留五个领域 State、两个 required 语义 Verifier 和 `scripts/phase_entry.py` 单一编排入口。删除任一 State 会损失恢复/阶段可见性，删除任一 Verifier 会损失阶段证据或科学价值闸门。
- 目标 Skill 只在 `config.yaml:runtime.kernel` 声明 `name: bensz-skill-kernel`；删除 `dependencies.kernel.version`、`runtime.kernel.version` 与 `runtime.required_capabilities`。实际 BSK 版本由托管安装器和任务证据追溯。
- 运行前用系统级 `install-bensz-skills` 执行 `--force-runtime-update`；Python API 固定使用 `~/.bensz-skills/envs/benszapi/bin/python`，CLI 固定使用 `~/.bensz-skills/bin/bsk`。
- `verifier-state-architect/scripts/check_integration.py` 在 BSK 2.1.2 下因过时导入误报依赖不可用；本轮已本地脱敏记录该缺陷。官方 helper 结果保持“受阻”，改用真实加载器与行为回归提供独立证据，不冒充 helper 通过。
- 实施状态：**受阻，未修改 `skills/research-idea`**。生产 BSK 2.1.2 仍要求 `runtime.kernel.version` 与运行版本精确相等；仅声明包名会在 State/Verifier 加载阶段失败。上游主分支已为 2.2.0 并调用新的声明校验器，但 PyPI 尚未发布该版本，托管规范禁止用主分支或手工 pip 覆盖生产环境。

## 业务流程与风险地图

`literature → candidates → review → reporting → completed` 是稳定领域生命周期。每条前向边先消费 State-bound action authorization，再由两个 required Agent Verifier 对同一 run/state visit/attempt 的证据回传，BSK 生成 Gate，只有 `allow` 才转移并创建目标 visit/attempt。

主要风险是：旧版/错误解释器污染、固定版本导致升级即拒绝、绕过单一入口、required 回传缺失或错绑、旧 Gate/attempt 复用、证据变化后未重审、把通用机械检查当作科研语义认证。现有运行快照、入口绑定、完成收敛检查和事件投影继续承担恢复与审计。

## 删除影响测试（含“不接入”结论）

| 候选 | 删除影响 | 结论 |
| --- | --- | --- |
| literature/candidates/review/reporting/completed State | 丢失阶段恢复点、State visit/attempt 身份、Gate 归属和可重放转移链 | 保留五个 State |
| `bensz.research.stage-readiness` | 无法判断阶段产物与上游证据是否足以推进 | 保留、required |
| `bensz.research.hypothesis-merit` | 流程完整可掩盖低价值、重复或不可辨别的假设 | 保留、required |
| BSK 内置文件/路径/事件 Verifier | 可辅助机械边界，但不能解释科研证据和假设价值；新增为 required 会扩大回传与维护成本 | 本轮不接入 |
| 新 State/Verifier | 当前稳定阶段和两类语义命题已覆盖决策点 | 不接入 |

## Verifier 设计矩阵

| 候选 | 保留/删除 | 稳定命题或状态含义 | AI/脚本分工 | 输入与证据 | Gate/转移 | 失败与人工复核 |
| --- | --- | --- | --- | --- | --- | --- |
| stage-readiness 3.0.0 | 保留 | 当前阶段证据真实、充分且支持目标边 | AI 读源证据；BSK 校验协议与绑定 | subject/context/evidence、来源锚点、run/visit/attempt | required；非 pass 不转移 | `uncertain/unchecked` 补证据或人工复核 |
| hypothesis-merit 1.0.0 | 保留 | 推荐/淘汰结论经科学价值、创新性与替代方向审问 | AI 作语义判断；BSK 绑定与聚合 | 候选、近邻、map、审查、报告 | required；非 pass 不转移 | 等价性或重要性不明时返回 uncertain |

## State 设计矩阵与最小状态图

| 候选 | 保留/删除 | 稳定命题或状态含义 | AI/脚本分工 | 输入与证据 | Gate/转移 | 失败与人工复核 |
| --- | --- | --- | --- | --- | --- | --- |
| 五阶段 State 4.0.0 | 保留 | 文献、候选、审查、报告、完成的持续阶段 | Agent 执行业务；入口消费 BSK API/CLI | 阶段产物、事件、快照、Gate | 四条前向受控 action；返工边由受控恢复处理 | 留在当前 visit，supersede attempt 后重审 |

最小状态图：`literature → candidates → review → reporting → completed`。返工可回到受影响的更早阶段；终态不原地追加新 attempt。

## AI/确定性分工与 Evidence Contract

- 确定性：托管解释器/启动器定位、JSON 结构、路径范围、Pack ID/version、run/visit/attempt 绑定、Gate/result_refs、转移回执、事件投影与内容哈希。
- AI：研究证据充分性、假设价值、创新性、相关性、冲突与恢复建议。
- 混合：脚本构造和绑定请求，Agent 按 `VERIFIER.md` 返回 `subject/context/evidence/verdict/summary/evidence_refs/confidence/uncertainties`；BSK 只认可协议枚举。证据不足使用 `uncertain/unchecked`，不把模型自评写成 pass。

## Kernel 对接、Gate、重放与资源边界

- `runtime.kernel` 只声明包名；Pack ID 和 Pack version 继续由索引与 `runtime.verifiers` 维护。
- 安装器负责最新生产运行时；Skill 不直接向托管 prefix 执行 pip，也不从项目/PATH 猜测 Kernel。
- `required` 缺失、失败、未完成、错绑、超时或未知结果均 fail-closed；旧 attempt 的 Gate 不复用。
- State 与事件由 BSK 持久化并可重放；领域语义留在 Skill Pack。输入路径规范化到项目和任务范围，子进程使用参数数组，禁止 shell 拼接。

## BSK 单一编排入口（适用时）

适用。`config.yaml:runtime.orchestration.entrypoint` 继续指向 `scripts/phase_entry.py`，四个 action 映射保持不变。入口负责读取当前身份、构造同一 attempt 请求、解析全部 required Verifier、生成 Gate、allow 后转移并严格核对目标 State。`SKILL.md:## 控制` 将其声明为正常业务唯一路径；底层 BSK 仅供入口、诊断和恢复。

## Kernel 复用与元 Verifier/State 提炼决策

| 候选能力 | 现有 Kernel ID/版本 | 复用方式 | 契约差异 | 跨领域 | 提炼建议 | 主要理由 | 验证动作 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 状态身份、attempt、Gate、事件 | BSK 2.1.2 公开运行协议 | 直接复用 | 无领域语义 | 是 | 不新增元组件 | 已覆盖生命周期与审计；复制会分叉真相源 | 成功/失败/重试/重放回归 |
| 文件、路径、事件完整性 | `bensz.artifact.*`、`bensz.runtime.event-integrity` 1.0.0 | 可组合辅助 | 不判断科研充分性 | 是 | 本轮不加入 required | 现有完成检查已覆盖消费点；额外 Gate 增加回传成本 | 保留候选，后续按真实缺陷评估 |
| 阶段科研充分性 | 无等价内置 ID | Skill 专用适配 | 需要读领域证据与阶段语义 | 否 | 不提炼 | 跨不相邻领域证据不足；抽象后只剩空泛“充分” | 专用 Pack 行为回归 |
| 假设价值与创新性 | 无等价内置 ID | Skill 专用适配 | 依赖候选、近邻、替代方向 | 否 | 不提炼 | 与 research-idea 强耦合；独立版本化收益低于误用风险 | 专用 Pack handoff/绑定回归 |

复用结论：直接复用 BSK 的通用运行协议；不复制内置机械 Verifier。依据一是 2.1.2 已提供完整 State visit/attempt/Gate/事件能力，二是现有入口只需消费协议即可保持可重放。元组件结论：暂不提炼科研语义组件。依据一是尚无两个不相邻领域的等价证据，二是抽象会把易变领域判断错误地下沉到 Kernel。

## 实施顺序（P0/P1/P2）

- P0：修改 `config.yaml`、三个 BSK 消费脚本和控制文档。证据为最新托管规范与 2.1.2 实际诊断；影响是正常入口切换到托管 Python/固定 bsk；验证为声明加载、成功/fail-closed、错误解释器拒绝；完成条件是源码不再固定包版本/capability；回退为仅撤销本轮文件改动，保留托管环境 last-known-good。
- P1：更新目标测试、README、运行指南、State 文案、Skill/根 CHANGELOG 和版本。验证为定向 pytest、结构/链接/JSON/YAML 与 diff 检查；完成条件是代码、配置、文档一致。
- P2：记录官方 helper 兼容缺陷并保留替代验证摘要。完成条件是本地脱敏记录存在且不公开上传；不修改系统级 Skill。

## 验收与回归测试

1. 安装器 `--force-runtime-update`、固定 `bsk --version/diagnostics/capabilities` 成功。
2. 官方 `check_integration.py` 结果单独记录；若继续受阻，不写成通过。
3. 使用托管 Python直接加载 State/Verifier 声明、canonical ID、图边和 orchestration。
4. 运行 `tests/research-idea`，覆盖启动、授权、required handoff、Gate allow/拒绝、错绑、State 不匹配、attempt supersede 与完成收敛。
5. 从无关工作目录执行固定托管入口的 smoke；检查源码目录无缓存污染。
6. 运行 Skill 结构、本地链接、配置解析、`git diff --check` 与 BAC verify。

## 已知不确定性、回退方案和不在范围内的事项

- 官方集成 helper 与 2.1.2 不兼容，静态检查受阻；替代证据不会冒充 helper 结果。
- 2.1.2 真实回归在移除版本声明后共运行 18 项：2 项通过，9 项失败、7 项错误，所有失败均收敛到 `runtime kernel mismatch`。试验性源码改动已逐项撤回，仓库中的 `research-idea` 保持 0.10.0 可运行契约。
- Agent Verifier 的真实科研质量不由合成回传证明；本轮只验证协议、绑定和 fail-closed 行为。
- 不修改 BSK 包、系统级已安装 Skill 源码、历史事件、旧计划或远程仓库；不新增 Kernel 元组件。

## 生产版发布后的恢复入口

1. 重新由系统安装器执行 `--force-runtime-update`，确认生产版已包含仅声明包名的加载契约。
2. 先运行 `check_integration.py`；若 helper 仍受阻，保留其失败证据并单独修复/升级 `verifier-state-architect`。
3. 按 P0/P1 修改 `research-idea`，使用托管 Python 跑完整成功与 fail-closed 回归；不得仅因上游主分支已有代码就跳过生产版确认。
