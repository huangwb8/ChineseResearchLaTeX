---
entry_conditions: ["bensz.research-ideation.review"]
invariants: ["verifier-result-recorded", "verifier-gate-allow", "required-verifiers-pass"]
transitions: ["bensz.research-ideation.completed", "bensz.research-ideation.review", "bensz.research-ideation.candidates", "bensz.research-ideation.literature"]
---

# 报告撰写

## 状态含义

独立审查与综合选择已通过 Gate，正在生成供用户阅读的最终报告。

## 进入条件

前向进入必须有当前 run/attempt 的 required Gate；回退进入须通过 Verifier 的 rework 判断并记录原因与证据。Kernel 检查图和离开源状态的不变量；Agent 核对 Gate 对应本次 source/target 和当前证据。

## Agent 行动

完成报告及格式检查后，用 `phase_entry.py --action reporting` 获取 BSK 原生 handoff；提交真实语义回传后由同一入口记录 Kernel Gate，仅转移返回 `status=transitioned` 才能交付完成。

使用 report-template；调用 validate_report 和阶段 Verifier，核对最终报告与证据的一致性，不在报告暴露内部路径。运行资料只写当前任务的 research-idea/input|output|log；正式报告按用户项目约定保存。

## 输入与证据

report；唯一最终 Markdown，结构通过且论文依据、查新、假设及推荐/无合格结论均与前阶段证据一致。insufficient 可作为阶段性评估交付，但保持最近阶段，不进入 completed。证据由业务执行 Agent 产生，审查者读取原始依据后回传，不把字段存在或模型自信视作事实成立。

## 离开条件

按 [运行指南](../../runtime-guide.md) 调用 required Verifier 并记录 Kernel Gate，再执行 bsk state transition。全部 required 语义组件完成且 pass 才能前进；fail/uncertain/unchecked/error/timed_out/skipped 均保留当前阶段。需要返工时对 rework 必要性单独核验，不要求有缺陷的研究内容通过前进判据。

## 转移指引

- `bensz.research-ideation.completed`：阶段证据充分且当前 Gate 通过时前进。
- `bensz.research-ideation.review`：发现该前置阶段需要补证据或改写时，按 Verifier 的 rework 分支核验后用 bsk 回退；Agent 将目标及下游旧结论标为待复核。
- `bensz.research-ideation.candidates`：发现该前置阶段需要补证据或改写时，按 Verifier 的 rework 分支核验后用 bsk 回退；Agent 将目标及下游旧结论标为待复核。
- `bensz.research-ideation.literature`：发现该前置阶段需要补证据或改写时，按 Verifier 的 rework 分支核验后用 bsk 回退；Agent 将目标及下游旧结论标为待复核。

## 失败、恢复与回滚

失败和等待保留最近阶段与非通过回执；通过 Kernel 读取领域快照并核对任务事件。新证据或返工使用新 attempt，旧回传不得复用。取消记录原因并停止，保持真实阶段；恢复前重读证据。领域快照提交不完整时停止处理，不手改快照或重写旧事件。

## 边界与执行归属

`phase_entry.py` 只收敛 BSK 调用，不维护状态或事件；Kernel 负责图、Gate、绑定、run/attempt、事件与状态持久化，Agent 负责科学语义和 Verifier 回传。
