---
entry_conditions: ["bensz.workspace.ready", "bensz.research-ideation.candidates", "bensz.research-ideation.review", "bensz.research-ideation.reporting"]
invariants: ["verifier-result-recorded", "verifier-gate-allow", "required-verifiers-pass"]
transitions: ["bensz.research-ideation.candidates"]
---

# 文献调查

## 状态含义

资料已归纳，正在建立主题、雷达结果、论文解读和研究脉络 map。此状态不宣称证据充分。

## 进入条件

首次从内置 workspace.ready 用 bsk state transition 进入，无需前置科研 Gate。重入仅接受图中回退边；Agent 先核验返工依据，Kernel 检查图和当前 run/attempt 的 Gate。

## Agent 行动

完成本阶段业务产物后，用 `phase_entry.py --action literature` 获取 BSK 原生 handoff；提交真实语义回传后由同一入口记录 Kernel Gate 并转移到 candidates。

调用主题提取、文献雷达、逐篇解读；沿用 SKILL.md 的分批并发上限，主 Agent 汇总失败与摘要/全文深度。运行资料只写当前任务的 research-idea/input|output|log；正式报告按用户项目约定保存。

## 输入与证据

theme、radar、interpretation、map；每个结论有论文锚点，未完成解读不得冒充完整 map。证据由业务执行 Agent 产生，审查者读取原始依据后回传，不把字段存在或模型自信视作事实成立。

## 离开条件

按 [运行指南](../../runtime-guide.md) 调用 required Verifier 并记录 Kernel Gate，再执行 bsk state transition。全部 required 语义组件完成且 pass 才能前进；fail/uncertain/unchecked/error/timed_out/skipped 均保留当前阶段。需要返工时对 rework 必要性单独核验，不要求有缺陷的研究内容通过前进判据。

## 转移指引

- `bensz.research-ideation.candidates`：阶段证据充分且当前 Gate 通过时前进。

## 失败、恢复与回滚

失败和等待保留最近阶段与非通过回执；通过 Kernel 读取领域快照并核对任务事件。新证据或返工使用新 attempt，旧回传不得复用。取消记录原因并停止，保持真实阶段；恢复前重读证据。领域快照提交不完整时停止处理，不手改快照或重写旧事件。

## 边界与执行归属

`phase_entry.py` 只收敛 BSK 调用，不维护状态或事件；Kernel 负责图、Gate、绑定、run/attempt、事件与状态持久化，Agent 负责科学语义和 Verifier 回传。
