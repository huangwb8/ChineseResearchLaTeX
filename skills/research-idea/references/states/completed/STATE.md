---
entry_conditions: ["bensz.research-ideation.reporting"]
invariants: []
transitions: []
---

# 完成

## 状态含义

唯一最终报告已通过 validate_report、绑定的科学审查和 Kernel Gate；只证明本次提交快照达到交付要求。业务结论可为 recommended 或 no_qualified，不代表必须存在推荐候选；insufficient 不属于完成。

## 进入条件

仅从 reporting 进入，必须有当前 run/attempt 的 required Gate。Kernel 检查图和离开源状态的不变量；Agent 核对 Gate 对应本次报告与最新证据，且报告 completion_eligible 为 true。

## Agent 行动

无 Agent 操作；向用户交付正式报告，不能再写入新 attempt。运行资料只写当前任务的 research-idea/input|output|log；正式报告按用户项目约定保存。

## 输入与证据

报告及其对应内容标识、语义回传、Kernel Gate 和最终转移事件。证据由业务执行 Agent 产生，审查者读取原始依据后回传，不把字段存在或模型自信视作事实成立。

## 离开条件

终态，无离开条件和后继状态。

## 转移指引

没有后继状态；新的研究方向建立新任务。

## 失败、恢复与回滚

通过 Kernel 读取终态快照并核对最后的 Gate 与转移事件；领域快照提交不完整时停止处理，不手改快照或重写旧事件。完成后发现新证据须发起新的研究任务，不在终态新增 attempt 或回退。

## 边界与执行归属

本 State 是纯 Markdown 阶段契约，无脚本组件。Kernel 负责图、原生不变量、Gate、事件与状态持久化；Agent 负责科学语义、来源/目标匹配及变更后的重审。本文不变量由 Kernel 在离开状态时检查；自然语言要求由 Agent 执行。不另建锁、快照、事件重放或状态调度代码。
