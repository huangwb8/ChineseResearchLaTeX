# research-idea 完成证据收敛优化计划

日期：2026-09-11。状态：待实施。本计划基于一次相邻仓库中的 `research-idea` 实战运行复盘制定；本次只写优化计划，不修改 Skill 行为。

## 通俗解释：究竟发生了什么

- **一句话说明：** 报告内容本身像一份可用的研究建议，但证明“这份建议确实按完整流程做完了”的票据没有收齐。
- **具体场景：** 像一次科研项目报销：正文报告相当于研究成果，文献记录、查新记录、三轮审查、状态门禁和校验日志相当于发票、审批单和验收单。
- **对应到本问题：** `research-idea` 的最终 Markdown 是成果；任务目录里的 map、候选、查新、审查文件是过程票据；`bsk` 状态、Verifier Gate 和 `validate_report.py` 输出是验收记录。
- **改变前后：** 现在可能出现“报告写得不错，但验收记录停在 literature 阶段”的情况。改进后，执行者只有在报告、状态、Gate、审查轮次、查新证据和校验命令一致时，才能把结果说成完整推荐。

## 专业判断：问题在哪里

- **当前现象：** 这次运行最终报告声明 `outcome: recommended`，且 `exploration`、`novelty`、`review` 均为 `complete`；报告用 `--allow-custom-name` 可通过结构校验，内容也符合新 v2 报告的大部分要求。
- **过程证据缺口：** 任务事件日志只有一次 `workspace.ready -> literature` 转移，没有后续 `candidates`、`review`、`reporting`、`completed` 转移，也没有 required Verifier 结果或 Gate 记录。
- **独立审查缺口：** 目录中只有一个 `parallel-vibe/output/round1-summary.md`，而 `research-idea/output/review-rounds.md` 是主 Agent 汇总出的三轮摘要，不能证明默认三轮、每轮三名独立审查者实际执行。
- **依赖产物缺口：** `research-literature-review` 目录只有查询 JSON，缺少可复核的 Premium 查新输出；`research-literature-interpretation` 目录没有逐篇解读文件。报告中的近邻比较有实质内容，但过程目录没有足够支撑“依赖 Skill 已按契约完成”。
- **校验入口歧义：** 用户指定 `docs/ideas/v11.md` 时，`manifest.allow_custom_name` 为 true；`validate_report.py --report ... --allow-custom-name` 通过，但 `SKILL.md` 的示例命令没有带该参数，裸跑会因为文件名失败。
- **测试入口不一致：** 仓库级 `tests/research-idea` 可通过；但 Skill 包内 `skills/research-idea/tests/test_runtime.py` 仍引用已移除的 `idea_runtime.py`，直接运行会收集失败。这会削弱后续维护者对“当前 Skill 测试已覆盖”的信心。

这些现象说明，本次缺陷不是单纯的写作质量问题。更准确地说，`research-idea` 已经能引导 Agent 产出不错的科研判断，但还缺少一个执行者难以漏掉的最终收敛机制，把报告内容、阶段状态、依赖证据、审查轮次和验证命令绑定成同一个完成事实。

## 要达到什么目标

- **完成后的变化：** 任何 `recommended` 或 `no_qualified` 报告交付前，都能用一个清楚的验收入口确认：状态已到正确阶段，required Gate 存在且通过，报告结构校验使用了正确参数，依赖产物和审查轮次满足契约。
- **用户可观察结果：** 最终交付说明不再只说“报告通过校验”，而能区分“内容质量可读”“结构校验通过”“运行状态已 completed”三种不同层级。
- **不在本次处理范围：** 不重新设计 Kernel，不恢复旧 `idea_runtime.py`，不降低 Premium 查新要求，不修改现有历史运行，也不替代 2026-09-10 已制定的科研质量优化计划。

## 改进方向

### 增加最终完成收敛检查

新增一个轻量的完成前检查入口，用来读取任务根、manifest、事件日志、meta-state、报告校验结果和关键依赖产物索引。它不重新实现状态机，也不替代语义 Verifier，只负责在交付前发现明显不一致：报告声明完成但状态未推进、Gate 缺失、review 轮次不足、依赖目录空、查新只有查询没有结果、校验参数与 manifest 不一致。

对普通用户的意义是：报告不只是“写好了”，而是“能拿出票据证明流程走完了”。

### 让自定义文件名自动带入校验上下文

将 `manifest.allow_custom_name` 与最终校验命令打通。文档示例应说明：用户指定文件名时，校验必须带 `--allow-custom-name`，或提供 `--task-root/--manifest` 形式让脚本自动读取该设置。交付 README 里也应记录实际执行的完整校验命令和结果。

对普通用户的意义是：用户指定 `v11.md` 这类友好文件名不会被默认命名规则误判，也不会让执行者误以为裸命令通过。

### 明确依赖 Skill 的最低可复核产物

把“调用了依赖 Skill”和“留下了可复核产物”分开。`research-literature-interpretation` 至少应有逐篇或逐组解读结果及失败/证据不足记录；`research-literature-review` 至少应有查新结果、近邻比较、覆盖边界和执行状态，而不只是查询计划；`parallel-vibe` 至少应按轮次保存独立审查者结果与汇总关系。

对普通用户的意义是：后续审阅者能看出结论从哪里来，而不是只能相信最终报告的叙述。

### 将报告声明与运行状态解耦表达

报告 frontmatter 中的 `exploration/novelty/review: complete` 只能代表业务内容自述，不能单独代表 Kernel 状态完成。交付规则应要求同时给出运行状态：`completed`、阶段性 `insufficient`、或“内容已交付但运行门禁未完成”。如果运行门禁缺失，报告可以作为草案或阶段性产物交付，但不能称为已完成的正式推荐。

对普通用户的意义是：读者不会把一份好报告误读成已经完成全套审计流程。

### 收拢测试入口，移除旧运行时残留

清理或迁移 `skills/research-idea/tests/test_runtime.py` 中对旧 `idea_runtime.py`、`phase_evidence.py` 的引用，让 Skill 包内测试与仓库级 `tests/research-idea` 指向同一套当前 Kernel 集成契约。变更日志和 README 中的“测试通过”应明确对应哪个测试入口，避免旧测试静默腐烂。

对普通用户的意义是：维护者运行最直观的测试目录时，不会碰到已经删除的旧接口。

## 实施范围与顺序

1. 先补一份完成收敛规则，明确 `recommended/no_qualified/insufficient` 与 Kernel 状态、Gate、依赖产物、审查轮次之间的关系。
2. 更新报告校验入口，让自定义文件名参数能从 manifest 自动传入，或在文档中强制展示完整命令。
3. 为依赖产物和三轮审查补最小可复核清单，缺失时只能交付阶段性结果或标记运行未完成。
4. 清理 Skill 包内旧测试，确保仓库级和 Skill 级测试都覆盖当前轻量 Kernel 流程。
5. 同步 `SKILL.md`、`README.md`、`runtime-guide.md`、`CHANGELOG.md` 和必要测试，版本号仍只在 `config.yaml` 中修改。

## 如何确认完成

- 自定义文件名报告在不手动猜参数的情况下可被正确校验；默认命名报告仍保持原有约束。
- 构造一个只有最终报告、没有 Gate 和后续状态转移的任务目录，完成收敛检查应失败，并提示恢复到哪个阶段。
- 构造只有 `research-literature-review/input/queries.json`、没有查新输出的任务目录，不能声明 `novelty: complete` 的运行完成。
- 构造只有一份 `parallel-vibe` 汇总的任务目录，不能通过默认三轮三人独立审查验收。
- `python -m pytest tests/research-idea -q` 与 `python -m pytest skills/research-idea/tests -q` 均能运行到当前契约，不再引用已移除模块。
- BAC 记录本次修复计划、关键验证命令、测试结果和未解决风险。

## 风险与待确认事项

- **避免重新造运行时：** 收敛检查只做一致性核对，不承担 Kernel 的状态、Gate、绑定和事件持久化职责。
- **避免把机械检查当科研判断：** 文件存在和轮次数量只能证明流程证据齐备，不能替代研究价值、新颖性和假设质量审查。
- **历史运行兼容：** 旧任务目录只能被标记为“按新收敛规则未完成/不可追认”，不得改写历史事件来补 completed。
- **成本控制：** 缺少依赖产物时，优先给出阶段性结果和恢复位置，不自动重跑昂贵查新或多 Agent 审查。

## 依据与阅读入口

- 当前 `research-idea` 规范：[skills/research-idea/SKILL.md](../../skills/research-idea/SKILL.md)
- 运行指南：[skills/research-idea/references/runtime-guide.md](../../skills/research-idea/references/runtime-guide.md)
- 报告校验脚本：[skills/research-idea/scripts/validate_report.py](../../skills/research-idea/scripts/validate_report.py)
- 既有质量计划：[docs/plans/2026-09-10-research-idea-quality-optimization.md](2026-09-10-research-idea-quality-optimization.md)
- 既有轻量状态计划：[docs/plans/2026-09-10-research-idea-lightweight-state-verifier.md](2026-09-10-research-idea-lightweight-state-verifier.md)

本计划不复制相邻仓库的完整报告或中间材料；复盘摘要保留在本轮任务工作区。
