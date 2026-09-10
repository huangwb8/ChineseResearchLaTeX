---
entry_conditions: ["bensz.research-ideation.candidates", "bensz.research-ideation.reporting"]
invariants: []
transitions: ["bensz.research-ideation.reporting", "bensz.research-ideation.candidates", "bensz.research-ideation.literature"]
---

# 独立打磨

## 状态含义

候选与查新已经通过 Gate（或报告阶段回退），正在逐轮独立评估、综合候选去留与业务结论。

## 进入条件

前向进入必须有当前 run/attempt 的 required Gate；回退进入必须有原因与证据。图由 Kernel StateMachine 检查，科学充分性由 Agent 判定，宿主负责 Gate 与转移的绑定。

## Agent 行动

按运行设置执行 rounds 轮，每轮 agents 个独立审查；串行轮次，记录每个 reviewer 与轮次及汇总。实质改写问题或假设须回 candidates 重新查新。运行资料只写当前任务的 research-idea/input|output|log；正式报告按用户项目约定保存。

## 输入与证据

review、synthesis；每轮不同结果与 reviewer 标识、上一轮汇总引用、冲突处理、科学价值与近期投入的独立比较，或零候选的淘汰充分性、替代方向和重启条件。每轮须承担不同判断任务并记录新增发现。证据由业务执行 Agent 产生，审查者读取原始依据后回传，不把字段存在或模型自信视作事实成立。

## 离开条件

完成该阶段工作后用宿主 prepare 发起验证，submit 回传，required 组件全 pass 才能前进；fail/uncertain/unchecked/error/timed_out 均保留当前阶段。

## 转移指引

- `bensz.research-ideation.reporting`：阶段证据充分且当前 Gate 通过时前进。
- `bensz.research-ideation.candidates`：发现该前置阶段需要补证据或改写时，用 rework 回退并失效其下游检查点。
- `bensz.research-ideation.literature`：发现该前置阶段需要补证据或改写时，用 rework 回退并失效其下游检查点。

## 失败、恢复与回滚

失败和等待保留最近阶段与非通过回执；status 重放事件恢复。新证据使用新 attempt，旧回传不得复用。取消通过宿主 cancel 记录终止事件，不伪造 completed。不得覆写事件；旧版本运行不得静默改写为新协议。

## 边界与执行归属

本 State 是阶段契约，components 为空，不宣称执行过验证。Kernel 负责图与事件完整性；Skill 宿主负责证据快照、Gate、运行身份和串行写入；Agent 负责领域语义。普通 bsk state transition 不替代本 Skill 宿主的阶段验收。
