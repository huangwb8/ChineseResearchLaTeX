---
entry_conditions: ["bensz.research-ideation.literature", "bensz.research-ideation.review", "bensz.research-ideation.reporting"]
invariants: []
transitions: ["bensz.research-ideation.review", "bensz.research-ideation.literature"]
---

# 候选与查新

## 状态含义

map 已通过前置 Gate（或明确回退到此重新查新），正在生成候选并逐对 Premium 查新。

## 进入条件

前向进入必须有当前 run/attempt 的 required Gate；回退进入必须有原因与证据。图由 Kernel StateMachine 检查，科学充分性由 Agent 判定，宿主负责 Gate 与转移的绑定。

## Agent 行动

依据 map 生成候选池；逐对查新并保留来源、覆盖不足、淘汰和改写理由。全部淘汰则在本阶段重新生成；map 不足回文献调查。运行资料只写当前任务的 research-idea/input|output|log；正式报告按用户项目约定保存。

## 输入与证据

candidates、novelty；核对每个候选的科学问题、假设、预测、反证、map 来源和查新判定；至少保留一个可推进候选。证据由业务执行 Agent 产生，审查者读取原始依据后回传，不把字段存在或模型自信视作事实成立。

## 离开条件

完成该阶段工作后用宿主 prepare 发起验证，submit 回传，required 组件全 pass 才能前进；fail/uncertain/unchecked/error/timed_out 均保留当前阶段。

## 转移指引

- `bensz.research-ideation.review`：阶段证据充分且当前 Gate 通过时前进。
- `bensz.research-ideation.literature`：发现该前置阶段需要补证据或改写时，用 rework 回退并失效其下游检查点。

## 失败、恢复与回滚

失败和等待保留最近阶段与非通过回执；status 重放事件恢复。新证据使用新 attempt，旧回传不得复用。取消通过宿主 cancel 记录终止事件，不伪造 completed。不得覆写事件；旧版本运行不得静默改写为新协议。

## 边界与执行归属

本 State 是阶段契约，components 为空，不宣称执行过验证。Kernel 负责图与事件完整性；Skill 宿主负责证据快照、Gate、运行身份和串行写入；Agent 负责领域语义。普通 bsk state transition 不替代本 Skill 宿主的阶段验收。
