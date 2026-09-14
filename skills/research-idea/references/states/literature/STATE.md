---
entry_conditions: ["bensz.workspace.ready", "bensz.research-ideation.candidates", "bensz.research-ideation.review", "bensz.research-ideation.reporting"]
invariants: ["verifier-result-recorded", "verifier-gate-allow", "required-verifiers-pass"]
transitions: ["bensz.research-ideation.candidates"]
---

# 文献调查

## 状态含义

资料已归纳，正在建立主题、雷达结果、论文解读和研究脉络 map。此状态不宣称证据充分。

## 进入条件

首次只由 `start_workflow.py` 从 workspace.ready 进入，必须同时得到 v2 run/state visit/initial attempt 与运行快照；无需前置科研 Gate。开始文献业务前必须消费 literature action authorization。

## Agent 行动

先用 `phase_entry.py --mode start --action literature` 授权业务；完成阶段产物后用 `--mode finish` 获取 BSK 原生 handoff，提交真实语义回传，由同一入口记录 Gate 并创建 candidates 的新 visit/attempt。

调用主题提取、文献雷达、逐篇解读；沿用 SKILL.md 的分批并发上限，主 Agent 汇总失败与摘要/全文深度。运行资料只写当前任务的 research-idea/input|output|log；正式报告按用户项目约定保存。

## 输入与证据

theme、radar、interpretation、map；每个结论有论文锚点，未完成解读不得冒充完整 map。证据由业务执行 Agent 产生，审查者读取原始依据后回传，不把字段存在或模型自信视作事实成立。

## 离开条件

按 [运行指南](../../runtime-guide.md) 通过 finish 模式完成 required Verifier、Kernel Gate 与 transition。全部 required 组件 completed 且 pass 才能前进；其它结果保留当前阶段，证据变化时 supersede attempt 后重新授权和审查。

## 转移指引

- `bensz.research-ideation.candidates`：阶段证据充分且当前 Gate 通过时前进。

## 失败、恢复与回滚

失败和等待保留当前 visit 与非通过回执；证据修复后在同一 visit 内 supersede attempt，旧授权、handoff 和 Gate 失效。legacy 身份、运行漂移或快照不完整时停止，不手改快照或旧事件。

## 边界与执行归属

`start_workflow.py` 与 `phase_entry.py` 只消费 BSK 2.1.1 公开接口；Kernel 负责图、授权、Gate、绑定、visit/attempt、事件与状态持久化，Agent 负责科学语义和 Verifier 回传。
