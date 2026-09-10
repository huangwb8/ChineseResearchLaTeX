---
entry_conditions: ["bensz.research-ideation.literature", "bensz.research-ideation.review", "bensz.research-ideation.reporting"]
invariants: ["verifier-result-recorded", "verifier-gate-allow", "required-verifiers-pass"]
transitions: ["bensz.research-ideation.review", "bensz.research-ideation.literature"]
---

# 候选与查新

## 状态含义

map 已通过前置 Gate（或明确回退到此重新查新），正在生成与筛选候选，并为拟保留项执行 Premium 查新。

## 进入条件

前向进入必须有当前 run/attempt 的 required Gate；回退进入须通过 Verifier 的 rework 判断并记录原因与证据。Kernel 检查图和离开源状态的不变量；Agent 核对 Gate 对应本次 source/target 和当前证据。

## Agent 行动

依据 map 生成候选池；逐对查新并保留来源、覆盖不足、淘汰和改写理由。全部淘汰则按预算进行一次有新证据或新角度的重新探索；map 不足回文献调查。仍无合格项且淘汰证据充分时进入独立复核，关键证据不足时保留当前阶段。运行资料只写当前任务的 research-idea/input|output|log；正式报告按用户项目约定保存。

## 输入与证据

candidates、novelty；核对每个候选的科学问题、假设、预测、反证、map 来源和查新判定；允许保留一个或零个；零候选时须有范围、淘汰证据、重新探索结果（或用户明确预算限制）和 novelty 的不适用依据；证据不足不能当作无合格。证据由业务执行 Agent 产生，审查者读取原始依据后回传，不把字段存在或模型自信视作事实成立。

## 离开条件

按 [运行指南](../../runtime-guide.md) 调用阶段 Verifier 并记录 Kernel Gate，再执行 bsk state transition。required 语义组件完成且 pass 才能前进；fail/uncertain/unchecked/error/timed_out/skipped 均保留当前阶段。需要返工时对 rework 必要性单独核验，不要求有缺陷的研究内容通过前进判据。

## 转移指引

- `bensz.research-ideation.review`：阶段证据充分且当前 Gate 通过时前进。
- `bensz.research-ideation.literature`：发现该前置阶段需要补证据或改写时，按 Verifier 的 rework 分支核验后用 bsk 回退；Agent 将目标及下游旧结论标为待复核。

## 失败、恢复与回滚

失败和等待保留最近阶段与非通过回执；通过 Kernel 读取领域快照并核对任务事件。新证据或返工使用新 attempt，旧回传不得复用。取消记录原因并停止，保持真实阶段；恢复前重读证据。领域快照提交不完整时停止处理，不手改快照或重写旧事件。

## 边界与执行归属

本 State 是纯 Markdown 阶段契约，无脚本组件。Kernel 负责图、原生不变量、Gate、事件与状态持久化；Agent 负责科学语义、来源/目标匹配及变更后的重审。本文不变量由 Kernel 在离开状态时检查；自然语言要求由 Agent 执行。不另建锁、快照、事件重放或状态调度代码。
