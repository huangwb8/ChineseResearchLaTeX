---
entry_conditions: ["bensz.research-ideation.candidates", "bensz.research-ideation.reporting"]
invariants: ["verifier-result-recorded", "verifier-gate-allow", "required-verifiers-pass"]
transitions: ["bensz.research-ideation.reporting", "bensz.research-ideation.candidates", "bensz.research-ideation.literature"]
---

# 独立打磨

## 状态含义

候选与查新已经通过 Gate（或报告阶段回退），正在逐轮独立评估、综合候选去留与业务结论。

## 进入条件

前向进入必须由上一阶段同 source identity 的 required Gate 放行，并由 BSK 创建新的 visit/initial attempt；开始审查前消费 review action authorization。

## Agent 行动

先用 `phase_entry.py --mode start --action review` 授权审查；完成独立审查与综合后用 `--mode finish` 获取 handoff、记录 Gate 并创建 reporting 的新 visit/attempt。

按运行设置执行 rounds 轮，每轮 agents 个独立审查；串行轮次，记录每个 reviewer 与轮次及汇总。实质改写问题或假设须回 candidates 重新查新。运行资料只写当前任务的 research-idea/input|output|log；正式报告按用户项目约定保存。

## 输入与证据

review、synthesis；每轮不同结果与 reviewer 标识、上一轮汇总引用、冲突处理、科学价值与近期投入的独立比较，或零候选的淘汰充分性、替代方向和重启条件。每轮须承担不同判断任务并记录新增发现。证据由业务执行 Agent 产生，审查者读取原始依据后回传，不把字段存在或模型自信视作事实成立。

## 离开条件

按 [运行指南](../../runtime-guide.md) 通过 finish 模式完成 required Verifier、Kernel Gate 与 transition。全部 required 组件 completed 且 pass 才前进；其它结果保留当前阶段，证据变化时 supersede attempt 后重审。

## 转移指引

- `bensz.research-ideation.reporting`：阶段证据充分且当前 Gate 通过时前进。
- `bensz.research-ideation.candidates`：返工边；普通前向入口不执行，需由受控 BSK 路径建立新的目标 visit/attempt。
- `bensz.research-ideation.literature`：返工边；普通前向入口不执行，需由受控 BSK 路径建立新的目标 visit/attempt。

## 失败、恢复与回滚

失败和等待保留当前 visit 与非通过回执；同 visit 内可 supersede attempt，旧授权、handoff 和 Gate 不可复用。reviewer 缺 thread/runner completed 回执时只能保留内容证据，不计入完整独立审查。

## 边界与执行归属

`phase_entry.py` 只消费 BSK 公开接口；Kernel 负责图、授权、Gate、绑定、visit/attempt、事件与状态持久化，Agent 负责科学语义、独立执行 provenance 和 Verifier 回传。
