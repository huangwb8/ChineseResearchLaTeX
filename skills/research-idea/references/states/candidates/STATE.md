---
entry_conditions: ["bensz.research-ideation.literature", "bensz.research-ideation.review", "bensz.research-ideation.reporting"]
invariants: ["verifier-result-recorded", "verifier-gate-allow", "required-verifiers-pass"]
transitions: ["bensz.research-ideation.review", "bensz.research-ideation.literature"]
---

# 候选与查新

## 状态含义

map 已通过前置 Gate（或明确回退到此重新查新），正在生成与筛选候选，并为拟保留项执行 Premium 查新。

## 进入条件

前向进入必须由上一阶段同 source identity 的 required Gate 放行，并由 BSK 创建新的 visit/initial attempt；开始候选业务前消费 candidates action authorization。

## Agent 行动

先用 `phase_entry.py --mode start --action candidates` 授权业务；完成候选生成、筛选和查新后用 `--mode finish` 获取 handoff、记录 Gate 并创建 review 的新 visit/attempt。

依据 map 生成候选池；逐对查新并保留来源、覆盖不足、淘汰和改写理由。全部淘汰则按预算进行一次有新证据或新角度的重新探索；map 不足回文献调查。仍无合格项且淘汰证据充分时进入独立复核，关键证据不足时保留当前阶段。运行资料只写当前任务的 research-idea/input|output|log；正式报告按用户项目约定保存。

## 输入与证据

candidates、novelty；核对每个候选的科学问题、假设、预测、反证、map 来源和查新判定；允许保留一个或零个；零候选时须有范围、淘汰证据、重新探索结果（或用户明确预算限制）和 novelty 的不适用依据；证据不足不能当作无合格。证据由业务执行 Agent 产生，审查者读取原始依据后回传，不把字段存在或模型自信视作事实成立。

## 离开条件

按 [运行指南](../../runtime-guide.md) 通过 finish 模式完成 required Verifier、Kernel Gate 与 transition。全部 required 组件 completed 且 pass 才前进；其它结果保留当前阶段，证据变化时 supersede attempt 后重审。

## 转移指引

- `bensz.research-ideation.review`：阶段证据充分且当前 Gate 通过时前进。
- `bensz.research-ideation.literature`：返工边；普通前向入口不执行，需由受控 BSK 路径建立新的目标 visit/attempt。

## 失败、恢复与回滚

失败和等待保留当前 visit 与非通过回执；同 visit 内可 supersede attempt，旧授权、handoff 和 Gate 不可复用。跨 State 回退先保留原因，必须由受控 BSK 路径建立新目标 visit。

## 边界与执行归属

`phase_entry.py` 只消费 BSK 公开接口；Kernel 负责图、授权、Gate、绑定、visit/attempt、事件与状态持久化，Agent 负责科学语义和 Verifier 回传。
