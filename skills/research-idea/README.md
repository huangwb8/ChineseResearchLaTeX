# research-idea - 用户使用指南

本 README 面向**使用者**：如何触发并正确使用 `research-idea` skill。
执行规范和硬性流程在 `SKILL.md`；默认参数在 `config.yaml`。

## 快速开始

推荐 Prompt：

```text
请使用 research-idea skill 根据我提供的资料提出关键科学问题和可证伪科学假设。
输入：下面这段项目背景/实验现象/论文草稿/文件路径/URL。
输出：一个 Research-Idea_{github仓库名}_{pr名}_{时间戳}.md 报告，放在当前项目根目录。
```

进阶 Prompt：

```text
请使用 research-idea skill 根据 ./notes 和 ./draft.md 提出关键科学问题和可证伪科学假设。
输入：./notes 文件夹 + ./draft.md。
输出：/path/to/output/ 目录下的 Research-Idea_{github仓库名}_{pr名}_{时间戳}.md。
另外，还有下列参数约束：
- 轮次：5 轮独立审查
- 研究边界：只考虑可在 6 个月内验证的假设
```

## 功能概述

`research-idea` 用于把零散资料变成可推进的研究想法。它会先生成多个“科学问题-可证伪假设”候选，再用 `research-topic-extractor` 和 `research-literature-review` 做 Premium 查新，最后通过 `parallel-vibe` 默认 3 轮串行独立审查打磨候选并选出最佳方案。

它不替代完整实验设计。你已经确定科学问题后，再用 `research-plan` 制定实验或分析计划。
如果你只需要写文献综述正文、related work 或系统综述，请直接使用 `research-literature-review`。

## 依赖兼容

`research-idea` 当前优先发现 `research-topic-extractor` 与 `research-literature-review`。过渡期如果用户环境里只安装了旧名 `get-review-theme` 或 `systematic-literature-review`，依赖检查会把它们作为 fallback 使用。

## 使用示例

### 示例 1：从实验现象找假设

```text
请使用 research-idea skill。
输入：我们发现处理 A 后细胞迁移增强，但增殖没有变化；已有 RNA-seq 显示通路 B 上调。
输出：当前目录下的 Markdown 报告。
```

### 示例 2：从项目资料夹找创新点

```text
请使用 research-idea skill。
输入：./project-background/，里面有 preliminary data、读书笔记和一份 grant 草稿。
输出：./outputs/ 目录下的 Research-Idea_{github仓库名}_{pr名}_{时间戳}.md。
```

## 输出文件

| 文件 | 说明 |
|------|------|
| `Research-Idea_{repo}_{pr}_{timestamp}.md` | 最终研究想法报告 |
| `.bensz-api/skills/research-idea/{yyyy-mm-dd-hh-mm}/` | 隐藏工作区，保存中间资料、查新记录和审查草稿 |
| `tests/research-idea/` | 技能开发测试区；普通用户运行不会默认创建 |

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
