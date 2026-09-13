---
entry_conditions: ["bensz.research-ideation.literature", "bensz.research-ideation.review", "bensz.research-ideation.reporting"]
invariants: ["verifier-result-recorded", "verifier-gate-allow", "required-verifiers-pass"]
transitions: ["bensz.research-ideation.review", "bensz.research-ideation.literature"]
---

# 候选与查新

## 状态含义

map 已通过前置 Gate（或明确回退到此重新查新），正在生成与筛选候选，并为拟保留项执行 Premium 查新。

## 进入条件

前向进入必须有当前 run/attempt 的 required Gate。State 图保留回退边，但当前 Kernel 2.1.0 兼容入口不执行 rework；Agent 核对 Gate 对应本次 source/target 和当前证据。

## Agent 行动

完成候选生成、筛选和查新后，用 `phase_entry.py --action candidates` 获取 BSK 原生 handoff；提交真实语义回传后由同一入口记录 Kernel Gate 并转移到 review。

依据 map 生成候选池；逐对查新并保留来源、覆盖不足、淘汰和改写理由。全部淘汰则按预算进行一次有新证据或新角度的重新探索；map 不足回文献调查。仍无合格项且淘汰证据充分时进入独立复核，关键证据不足时保留当前阶段。运行资料只写当前任务的 research-idea/input|output|log；正式报告按用户项目约定保存。

## 输入与证据

candidates、novelty；核对每个候选的科学问题、假设、预测、反证、map 来源和查新判定；允许保留一个或零个；零候选时须有范围、淘汰证据、重新探索结果（或用户明确预算限制）和 novelty 的不适用依据；证据不足不能当作无合格。证据由业务执行 Agent 产生，审查者读取原始依据后回传，不把字段存在或模型自信视作事实成立。

## 离开条件

按 [运行指南](../../runtime-guide.md) 调用 required Verifier 并记录 Kernel Gate，再执行 bsk state transition。全部 required 语义组件完成且 pass 才能前进；fail/uncertain/unchecked/error/timed_out/skipped 均保留当前阶段。需要返工时对 rework 必要性单独核验，不要求有缺陷的研究内容通过前进判据。

## 转移指引

- `bensz.research-ideation.review`：阶段证据充分且当前 Gate 通过时前进。
- `bensz.research-ideation.literature`：历史图边；当前兼容模式发现需补证据时标记下游待复核并停止，不执行回退。

## 失败、恢复与回滚

失败和等待保留最近阶段与非通过回执；通过 Kernel 读取领域快照和事件投影。当前兼容模式不支持新 attempt、失败重试或返工回退，旧回传不得复用；取消记录原因并停止，保持真实阶段。领域快照提交不完整时停止处理，不手改快照或重写旧事件。

## 边界与执行归属

`phase_entry.py` 只收敛 BSK 调用并读取 Kernel 当前进入身份，不维护状态或事件；Kernel 负责图、Gate、绑定、run/attempt、事件与状态持久化，Agent 负责科学语义和 Verifier 回传。完整 visit/attempt 轮换须等待 Kernel 原生接口。
