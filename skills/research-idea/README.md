<div align="center">
  <h1>Research Idea</h1>
  <p><strong>从研究资料和可审计文献证据中提出科学问题、可证伪假设与有边界的研究方向。</strong></p>
  <p><a href="README_EN.md">English</a> · <a href="#快速开始">快速开始</a> · <a href="SKILL.md">执行规范</a> · <a href="references/runtime-guide.md">运行说明</a></p>
</div>

<!-- README README_EN -->

`research-idea` 先建立文献 landscape、逐篇解读和研究脉络 map，再生成、查新并独立审查候选。它把科学价值、判断可信度和近期投入分开呈现，并明确区分“可推荐”“当前范围内无合格候选”和“证据不足”。

## 快速开始

向支持 Agent Skills 的宿主提供研究资料，并明确调用本 Skill：

```text
请使用 research-idea skill，根据 ./notes 和 ./draft.md 提出关键科学问题与可证伪假设。
请先调查文献，再比较最近工作；最终报告保存到 ./docs/ideas/。
```

预期结果是一个 Markdown 研究想法报告；默认文件名为 `Research-Idea_{repo}_{pr}_{timestamp}.md`。中间证据、查新记录和审查回执留在同一 `.bensz-api/task-*` 任务区。

## 它做什么

1. 用 `research-topic-extractor` 把输入转成可检索主题。
2. 用 `research-literature-search` 和 `research-literature-radar` 建立 canonical 候选池与完整 landscape。
3. 用 `research-literature-interpretation` 按论文隔离解读，建立带 O/R 锚点的研究 map。
4. 用 `parallel-vibe` 生成候选并进行多轮独立审查。
5. 对拟保留候选执行多查询查新，比较直接近邻、等价假设、反方证据和适用边界。
6. 输出推荐、无合格候选或证据不足结论，并用 BSK State、Verifier、Gate 和完成检查保存可复核证据。

## 输入与输出

| 类型 | 内容 |
| --- | --- |
| 最小输入 | 研究背景、实验现象、论文草稿、文件/目录、URL、仓库或 PR 线索中的至少一种 |
| 可选约束 | 研究目标、时间/资源边界、输出位置、审查轮数与人数 |
| 正式输出 | `./docs/ideas/Research-Idea_{repo}_{pr}_{timestamp}.md`，或用户指定的 Markdown 路径 |
| 中间产物 | `.bensz-api/task-{yyyymmdd-hhmm}-{描述}/{skill名}/input\|output\|log/` |

报告会给出文献证据深度、研究 map、候选或零候选依据、科学价值/可信度/投入判断、最近工作与查新、反证路径、风险和最小下一步。它不会把隐藏工作区路径、测试路径或 agent 内部指令写入正式报告。

## 使用示例

### 从实验现象形成候选

```text
请使用 research-idea skill。
输入：处理 A 后细胞迁移增强，但增殖没有变化；RNA-seq 显示通路 B 上调。
约束：只保留 6 个月内可形成关键辨别证据的方向；高可行性不能抵消低科学价值。
输出：默认 docs/ideas 目录下的研究想法报告。
```

### 从项目资料寻找创新点

```text
请使用 research-idea skill 分析 ./project-background/ 和 ./grant-draft.md。
先建立文献 landscape 与研究 map，再提出候选；对拟推荐候选检查直接近邻、等价假设和反方证据。
执行 5 轮独立审查，并分别报告科学价值、判断可信度与近期投入建议。
```

## 适用范围

适合需要文献依据的科学问题发现、可证伪假设凝练、创新点判断和研究方向比较。

以下任务应使用相邻 Skill：

- 已确定问题，只需要实验或分析方案：`research-plan`。
- 需要系统综述、related work 或完整综述正文：`research-literature-review`。
- 只需检索候选论文池：`research-literature-search`。
- 不需要文献依据的普通创意发散：使用通用 brainstorming 流程。

## 配置与脚本

`config.yaml` 是版本、默认轮次、依赖、输出和 BSK runtime 声明的事实来源。常用入口如下：

| 入口 | 用途 |
| --- | --- |
| `scripts/start_workflow.py` | 原子初始化任务区与 BSK run/visit/attempt 身份 |
| `scripts/phase_entry.py` | 阶段授权、Verifier handoff、Gate、transition 与 retry |
| `scripts/validate_report.py` | 检查报告结构、字段、命名和路径泄露 |
| `scripts/check_completion.py` | 核对依赖证据、回执、Gate/transition 绑定和 completed 状态 |
| `scripts/edge_rules.py` | 供阶段入口、完成检查和确定性 Verifier 共享的领域规则 |

完整命令与恢复路径见 [运行说明](references/runtime-guide.md)。报告格式见 [报告模板](references/report-template.md)，研究 map 与价值筛选见 [研究综合指南](references/research-synthesis.md)。

## 完成语义与限制

报告文件存在不等于流程完成。`artifact_ready`、`execution_recorded`、`evidence_sufficient`、`claim_eligible` 四层必须分别核验；正式 `completed` 还要求 required Verifier、BSK Gate、绑定的 transition 与 `check_completion.py` 全部通过。

`bounded_recommendation`、`degraded` 和 `insufficient` 可以作为诚实的阶段性交付，但不能伪装成完成结论。旧 completion v2–v5 或没有 evidence binding 的历史运行只读保留，不回填为新完成记录。

## 常见问题（FAQ）与更多文档

**为什么没有推荐方向？** 当前证据可能足以淘汰候选，也可能不足以判断。报告会区分 `no_qualified` 与 `insufficient`，并给出重启条件或恢复位置。

**为什么不能直接写实验方案？** 本 Skill 负责先确认问题和假设是否值得研究；确定方向后再交给 `research-plan` 展开设计。

**摘要够不够？** 摘要可用于相关性和明显不等价排除；决定机制、结果或新颖性的近邻通常需要全文。无法取得时必须收缩 claim。

- [Skill 执行规范](SKILL.md)
- [运行说明](references/runtime-guide.md)
- [查新判定指南](references/novelty-check.md)
- [独立审查参考](references/agent-review-prompt.md)
- [变更日志](CHANGELOG.md)
