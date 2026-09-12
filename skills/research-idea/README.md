# research-idea - 用户使用指南

本 README 面向**使用者**：如何触发并正确使用 `research-idea` skill。
执行规范和硬性流程在 `SKILL.md`；默认参数在 `config.yaml`。

## 快速开始

推荐 Prompt：

```text
请使用 research-idea skill 根据我提供的资料提出关键科学问题和可证伪科学假设。
输入：下面这段项目背景/实验现象/论文草稿/文件路径/URL。
输出：`./docs/ideas/Research-Idea_{github仓库名}_{pr名}_{时间戳}.md`。
```

进阶 Prompt：

```text
请使用 research-idea skill 根据 ./notes 和 ./draft.md 提出关键科学问题和可证伪科学假设。
输入：./notes 文件夹 + ./draft.md。
输出：`/path/to/output/` 目录下的 `Research-Idea_{github仓库名}_{pr名}_{时间戳}.md`。
另外，还有下列参数约束：
- 轮次：5 轮独立审查
- 研究边界：只考虑可在 6 个月内验证的假设
```

## 功能概述

`research-idea` 遵循“没有调查就没有发言权”：先用 `research-literature-radar` 发现重要/前沿论文，再由并行子 agent 分批调用 `research-literature-interpretation`（每篇论文一个 agent，同时最多 3 个）并建立时间有序、逻辑关联的研究脉络 map；之后才由多个独立 agent 基于 map brainstorming 初始候选，最后用 `research-literature-review` 做 Premium 查新，并通过 `parallel-vibe` 默认 3 轮串行独立审查形成结论。查新前先筛选科学价值；map 连接研究线、解释与证据，候选可追溯到稳定的机会和论文编号。推荐候选还必须接受独立的科学假设价值审问，说明概念增量、创新性、颠覆/改写潜力、非平凡性、关键预测和最强替代方向。

它不替代完整实验设计。你已经确定科学问题后，再用 `research-plan` 制定实验或分析计划。
如果你只需要写文献综述正文、related work 或系统综述，请直接使用 `research-literature-review`。

## 研究判断与交付结论

科学价值、判断可信度和近期投入分别比较；不会因为一个方向容易实现就把它当成最佳科研题目。三轮审查依次挑战选题价值、检查解释与辨别能力、重新比较备选与外推边界。目标贡献和资源约束可随输入提供；未说明的资源会记为未知。

初始通常探索 3–7 个方向，最终可以只有一个或没有合格候选：

| 报告结论 | 用户得到什么 |
| --- | --- |
| 有可推荐候选 | 完成必要 Premium 查新和独立审查的候选，科学价值与近期投入两种排序，以及最强替代方向 |
| 当前范围内无合格候选 | 有证据的淘汰原因、有限重新探索与复核结果、重启条件；不代表整个领域无题可做 |
| 证据不足，暂不能推荐 | 明确的阶段性评估、缺口与恢复位置；不声称新颖性或全流程完成 |

无合格结论不能省略必要探索与审查。若近邻全文受限或执行未完成，应保留证据不足。报告只说明关键未知、最小辨别动作和改变去留的观察，不默认展开完整实验方案。规则和跨领域示例见 [研究综合指南](references/research-synthesis.md)。

## 依赖兼容

`research-idea` 当前需要发现 `research-topic-extractor`、`research-literature-radar`、`research-literature-interpretation`、`research-literature-review` 与 `parallel-vibe`。过渡期仅对 `research-topic-extractor` 和 `research-literature-review` 保留旧名 fallback；雷达与解读是候选生成前置阶段，不能静默跳过。

## 验证器与状态机

以五个 Markdown State 记录“文献调查 → 候选与查新 → 独立打磨 → 报告 → 完成”，由两个 required 自然语言 Verifier 分别核验阶段证据与科学假设价值。Agent 判断科研充分性、创新性和推荐价值，现有脚本检查报告格式，bsk 原生能力负责 Gate、绑定、事件和状态持久化。

需要 Python 3.11+ 与满足 `config.yaml.dependencies.kernel` 最低版本要求的 Kernel。先用 `bsk workspace init --task-root` 准备任务工作区，领域初始化脚本只生成研究参数与候选空模板，再直接用 `bsk state transition --skill-root` 进入和推进阶段。本 Skill 不再维护运行时、锁、检查点或重放代码。

本地 Verifier 通过 [运行操作指南](references/runtime-guide.md) 中的简短 Kernel API 调用执行；该指南说明多 Verifier 绑定回传、批量 Gate、返工、恢复、可复用的内置组件和兼容边界。Agent 在转移前重新核对来源，证据变化后重审；不再承诺自动检查所有文件变化。

最终推荐或无合格候选结论还要通过完成收敛检查：任务工作区需保存 `research-idea/output/completion-evidence.json`，列出依赖 Skill 的非空产物、每轮独立审查者结果、轮次汇总和总综合。新索引使用 `schema: research-idea-completion-v2` 时，还要记录四层完成状态、run/attempt、authoritative attempt 以及来源 SHA-256/大小/修改时间快照；`check_completion.py` 会拒绝 Gate 后变更、跨 attempt 复用和 synthetic review。缺少其中任一项时，报告可以作为草案或阶段性评估交付，但不能说成完整 completed。

## 使用示例

### 示例 1：从实验现象找假设

```text
请使用 research-idea skill。
输入：我们发现处理 A 后细胞迁移增强，但增殖没有变化；已有 RNA-seq 显示通路 B 上调。
输出：默认目录 `./docs/ideas/` 下的 Markdown 报告。
```

### 示例 2：从项目资料夹找创新点

```text
请使用 research-idea skill。
输入：./project-background/，里面有 preliminary data、读书笔记和一份 grant 草稿。
输出：`./outputs/` 目录下的 `Research-Idea_{github仓库名}_{pr名}_{时间戳}.md`。
```

## 输出文件

| 文件 | 说明 |
|------|------|
| `docs/ideas/Research-Idea_{repo}_{pr}_{timestamp}.md` | 默认最终研究想法报告路径；可用 `--output-dir` 或用户参数覆盖 |
| `.bensz-api/task-{yyyymmdd-hhmm}-{简短描述}/research-idea/` | 隐藏工作区，保存中间资料、查新记录和审查草稿 |
| `research-idea/output/completion-evidence.json`（位于任务目录内） | 完成收敛索引，记录依赖产物和独立审查证据 |
| `log/events.ndjson` 与 `research-idea/log/meta-state.json`（位于任务目录内） | bsk 维护的事件日志与领域状态快照 |

最终报告不会暴露隐藏工作区路径。

## WHICHMODEL

本 skill 需要复杂科研推理、查新综合和多轮批判性审查。默认建议：

| 场景 | 推荐模型/强度 | 理由 |
|------|---------------|------|
| 提出和筛选科学问题 | 强推理模型，高 reasoning effort | 需要识别机制缺口、可证伪性和隐含假设 |
| Premium 查新总结 | 长上下文强模型 | 需要稳定整合文献证据并避免重复已有研究 |
| 独立审查 agent | 中高 reasoning effort | 需要从不同角度找缺陷并给出可执行改写 |
| 最终报告整理 | 默认或中等强度模型 | 主要是结构化表达和证据摘要 |

模型选择会随平台和供应商更新而变化；优先使用当前环境中最强的推理模型处理“候选生成、查新判断、最佳方案选择”三步。

## FAQ

**Q：没有 GitHub PR 也能用吗？**

A：可以。文件名里的 PR 名会退化为当前分支名；仍无法识别时使用 `manual`。

**Q：为什么要查新？**

A：科学问题看起来新，不代表真的没有被研究过。该 skill 会把“已充分研究”的候选淘汰或重构，避免把旧问题换个说法。

**Q：最终会给完整实验方案吗？**

A：不会。最终报告只给科学问题、可证伪假设、选择理由和最小下一步。完整实验或分析计划应交给 `research-plan`。

## 报告兼容与开发验证

新报告以 `report_contract: research-idea-report-v2` 显式声明 outcome 与探索、查新、审查状态；可用 `artifact_ready`、`execution_recorded`、`evidence_sufficient`、`claim_eligible` 表达四层完成语义，写法见 [报告模板](references/report-template.md)。`bounded_recommendation` 与 `degraded` 是可交付但不可 completed 的降级状态。旧报告仍支持结构读取并返回 legacy 警告，不能用于新运行认证完成；脚本检查格式与引用可定位性，科学充分性仍由实际读取来源并绑定结果的审查判断。

`validate_report.py` 的 `completion_eligible=true` 只表示报告文本具备进入完成流程的资格；最终还必须运行 `check_completion.py --task-root ... --report ...`。用户指定友好文件名时，完成检查会自动读取 manifest 的 `allow_custom_name`，避免裸跑报告检查产生误导。

旧运行和事件保持原样；专用运行时 CLI 已移除，迁移与原任务内重新核验见运行指南。报告检查 CLI 保留，初始化模板 `output/candidate-schema.json` 使用空 `candidates` 与单独 `candidate_example`，初始状态明确为 insufficient/incomplete，避免把示例当真实候选。BAC 仅证明本地账本结构和事件链完整；当前 unsigned/local checkpoint 不证明现实贡献、作者身份或不可篡改性。

定向回归源码位于 `tests/research-idea/`，测试命令与环境见 [运行指南](references/runtime-guide.md)。固定材料输出比较只能发现问题；目前不以格式通过或 AI 自评分宣称整体科研质量已得到验证。
