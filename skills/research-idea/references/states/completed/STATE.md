---
entry_conditions: ["bensz.research-ideation.reporting"]
invariants: []
transitions: []
---

# 完成

## 状态含义

唯一最终报告已通过结构组件、绑定的科学审查和 Kernel Gate；只证明本次提交快照达到交付要求。

## 进入条件

前向进入必须有当前 run/attempt 的 required Gate；回退进入必须有原因与证据。图由 Kernel StateMachine 检查，科学充分性由 Agent 判定，宿主负责 Gate 与转移的绑定。

## Agent 行动

无 Agent 操作；向用户交付正式报告，不能再写入新 attempt。运行资料只写当前任务的 research-idea/input|output|log；正式报告按用户项目约定保存。

## 输入与证据

通过的报告哈希、语义回传、Kernel Gate 和最终转移事件。证据由业务执行 Agent 产生，审查者读取原始依据后回传，不把字段存在或模型自信视作事实成立。

## 离开条件

终态，无离开条件和后继状态。

## 转移指引

没有后继状态；新的研究方向建立新任务。

## 失败、恢复与回滚

失败和等待保留最近阶段与非通过回执；status 重放事件恢复。新证据使用新 attempt，旧回传不得复用。取消通过宿主 cancel 记录终止事件，不伪造 completed。不得覆写事件；旧版本运行不得静默改写为新协议。

## 边界与执行归属

本 State 是阶段契约，components 为空，不宣称执行过验证。Kernel 负责图与事件完整性；Skill 宿主负责证据快照、Gate、运行身份和串行写入；Agent 负责领域语义。普通 bsk state transition 不替代本 Skill 宿主的阶段验收。
