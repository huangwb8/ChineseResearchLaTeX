---
entry_conditions: ["bensz.research-ideation.candidates", "bensz.research-ideation.reporting"]
invariants: ["verifier-result-recorded", "verifier-gate-allow", "required-verifiers-pass"]
transitions: ["bensz.research-ideation.reporting", "bensz.research-ideation.candidates", "bensz.research-ideation.literature"]
---

# 独立打磨

## 状态含义

候选与查新已经通过 Gate（或报告阶段回退），正在逐轮独立评估、综合候选去留与业务结论。

## 进入条件

前向进入必须有当前 run/attempt 的 required Gate；回退进入须通过 Verifier 的 rework 判断并记录原因与证据。Kernel 检查图和离开源状态的不变量；Agent 核对 Gate 对应本次 source/target 和当前证据。

## Agent 行动

按运行设置执行 rounds 轮，每轮 agents 个独立审查；串行轮次，记录每个 reviewer 与轮次及汇总。实质改写问题或假设须回 candidates 重新查新。运行资料只写当前任务的 research-idea/input|output|log；正式报告按用户项目约定保存。

## 输入与证据

review、synthesis；每轮不同结果与 reviewer 标识、上一轮汇总引用、冲突处理、科学价值与近期投入的独立比较，或零候选的淘汰充分性、替代方向和重启条件。每轮须承担不同判断任务并记录新增发现。证据由业务执行 Agent 产生，审查者读取原始依据后回传，不把字段存在或模型自信视作事实成立。

## 离开条件

按 [运行指南](../../runtime-guide.md) 调用阶段 Verifier 并记录 Kernel Gate，再执行 bsk state transition。required 语义组件完成且 pass 才能前进；fail/uncertain/unchecked/error/timed_out/skipped 均保留当前阶段。需要返工时对 rework 必要性单独核验，不要求有缺陷的研究内容通过前进判据。

## 转移指引

- `bensz.research-ideation.reporting`：阶段证据充分且当前 Gate 通过时前进。
- `bensz.research-ideation.candidates`：发现该前置阶段需要补证据或改写时，按 Verifier 的 rework 分支核验后用 bsk 回退；Agent 将目标及下游旧结论标为待复核。
- `bensz.research-ideation.literature`：发现该前置阶段需要补证据或改写时，按 Verifier 的 rework 分支核验后用 bsk 回退；Agent 将目标及下游旧结论标为待复核。

## 失败、恢复与回滚

失败和等待保留最近阶段与非通过回执；通过 Kernel 读取领域快照并核对任务事件。新证据或返工使用新 attempt，旧回传不得复用。取消记录原因并停止，保持真实阶段；恢复前重读证据。领域快照提交不完整时停止处理，不手改快照或重写旧事件。

## 边界与执行归属

本 State 是纯 Markdown 阶段契约，无脚本组件。Kernel 负责图、原生不变量、Gate、事件与状态持久化；Agent 负责科学语义、来源/目标匹配及变更后的重审。本文不变量由 Kernel 在离开状态时检查；自然语言要求由 Agent 执行。不另建锁、快照、事件重放或状态调度代码。
