---
entry_conditions: ["bensz.research-ideation.candidates", "bensz.research-ideation.review", "bensz.research-ideation.reporting"]
invariants: []
transitions: ["bensz.research-ideation.candidates"]
---

# 文献调查

## 状态含义

资料已归纳，正在建立主题、雷达结果、论文解读和研究脉络 map。此状态不宣称证据充分。

## 进入条件

初始节点由宿主 init 建立；重入仅接受图中回退边。图由 Kernel StateMachine 检查，科学充分性由 Agent 判定，宿主负责 Gate 与转移的绑定。

## Agent 行动

调用主题提取、文献雷达、逐篇解读；沿用 SKILL.md 的分批并发上限，主 Agent 汇总失败与摘要/全文深度。运行资料只写当前任务的 research-idea/input|output|log；正式报告按用户项目约定保存。

## 输入与证据

theme、radar、interpretation、map；每个结论有论文锚点，未完成解读不得冒充完整 map。证据由业务执行 Agent 产生，审查者读取原始依据后回传，不把字段存在或模型自信视作事实成立。

## 离开条件

完成该阶段工作后用宿主 prepare 发起验证，submit 回传，required 组件全 pass 才能前进；fail/uncertain/unchecked/error/timed_out 均保留当前阶段。

## 转移指引

- `bensz.research-ideation.candidates`：阶段证据充分且当前 Gate 通过时前进。

## 失败、恢复与回滚

失败和等待保留最近阶段与非通过回执；status 重放事件恢复。新证据使用新 attempt，旧回传不得复用。取消通过宿主 cancel 记录终止事件，不伪造 completed。不得覆写事件；旧版本运行不得静默改写为新协议。

## 边界与执行归属

本 State 是阶段契约，components 为空，不宣称执行过验证。Kernel 负责图与事件完整性；Skill 宿主负责证据快照、Gate、运行身份和串行写入；Agent 负责领域语义。普通 bsk state transition 不替代本 Skill 宿主的阶段验收。
