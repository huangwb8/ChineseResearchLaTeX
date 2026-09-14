---
entry_conditions: ["bensz.research-ideation.review"]
invariants: ["verifier-result-recorded", "verifier-gate-allow", "required-verifiers-pass"]
transitions: ["bensz.research-ideation.completed", "bensz.research-ideation.review", "bensz.research-ideation.candidates", "bensz.research-ideation.literature"]
---

# 报告撰写

## 状态含义

独立审查与综合选择已通过 Gate，正在生成供用户阅读的最终报告。

## 进入条件

前向进入必须由上一阶段同 source identity 的 required Gate 放行，并由 BSK 创建新的 visit/initial attempt；开始报告业务前消费 reporting action authorization。

## Agent 行动

先用 `phase_entry.py --mode start --action reporting` 授权业务；完成报告及格式检查后用 `--mode finish` 获取 handoff 并记录 Gate，仅创建 completed 新 visit 且返回 `status=transitioned` 才能交付完成。

使用 report-template；调用 validate_report 和阶段 Verifier，核对最终报告与证据的一致性，不在报告暴露内部路径。运行资料只写当前任务的 research-idea/input|output|log；正式报告按用户项目约定保存。

## 输入与证据

report；唯一最终 Markdown，结构通过且论文依据、查新、假设及推荐/无合格结论均与前阶段证据一致。insufficient 可作为阶段性评估交付，但保持最近阶段，不进入 completed。证据由业务执行 Agent 产生，审查者读取原始依据后回传，不把字段存在或模型自信视作事实成立。

## 离开条件

按 [运行指南](../../runtime-guide.md) 通过 finish 模式完成 required Verifier、Kernel Gate 与 transition。全部 required 组件 completed 且 pass 才前进；其它结果保留当前阶段，证据变化时 supersede attempt 后重审。

## 转移指引

- `bensz.research-ideation.completed`：阶段证据充分且当前 Gate 通过时前进。
- `bensz.research-ideation.review`：返工边；普通前向入口不执行，需由受控 BSK 路径建立新的目标 visit/attempt。
- `bensz.research-ideation.candidates`：返工边；普通前向入口不执行，需由受控 BSK 路径建立新的目标 visit/attempt。
- `bensz.research-ideation.literature`：返工边；普通前向入口不执行，需由受控 BSK 路径建立新的目标 visit/attempt。

## 失败、恢复与回滚

失败和等待保留当前 visit 与非通过回执；同 visit 内可 supersede attempt，旧授权、handoff、Gate 和完成索引不可复用。领域快照提交不完整时停止，不手改快照或旧事件。

## 边界与执行归属

`phase_entry.py` 只消费 BSK 公开接口；Kernel 负责图、授权、Gate、绑定、visit/attempt、事件与状态持久化，Agent 负责报告一致性、科学语义和 Verifier 回传。
