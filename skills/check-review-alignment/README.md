# check-review-alignment — 用户使用指南

本 README 面向**使用者**：如何触发并正确使用 `check-review-alignment` skill。
执行指令与硬性规范在 `SKILL.md`；默认参数在 `config.yaml`。

## 快速开始

**在运行本技能之前，强烈建议为您的综述文件做好版本控制**：
- 本技能会**直接修改** `{主题}_review.tex` 文件
- AI 的改写基于语义判断，可能存在误判或风格偏差
- 一旦修改不满意，需要有恢复原始版本的能力

### 最推荐用法

```
请用 check-review-alignment 核查/优化 xxx 目录中的综述引用。p0-p1问题均须修复。
```

### 兼容旧版systematic-literature-review的结果

如果之前用了较旧版本的systematic-literature-review（bib文献里没有abstract字段），可以这么用：
```
对于 xxx 项目， 请：
- 基于systematic-literature-review的原则，先为 bib 文件里的参考文献条目补齐 abstract 字段
- 再跑 check-review-alignment：只修复 P0，P1 问题。
```
它会使用 systematic-literature-review 的本地历史记录进行提取，一般也不需要连网。

### 其他常见场景

#### 场景 1：指定 tex 文件名

```
请用 check-review-alignment 核查/优化 HER2_review.tex 的引用。
```

#### 场景 2：结合 systematic-literature-review 流程

```
我已经用 systematic-literature-review 生成了综述，现在想用 check-review-alignment 核核查引用是否正确。
```

#### 场景 3：修复特定引用问题

```
我怀疑综述里有"幻觉引用"（引用的论文没做过这件事），请用 check-review-alignment 全面检查并修复。
```

#### 场景 4：希望非常激进地修改tex

```
（不推荐）我希望你“顺便润色/大幅改写”综述正文。
```
说明：本 skill 的设计边界是“只修复致命性引用错误（P0）并最小化改动”，不适合用来做整段润色或结构性重写。

## 设计理念

check-review-alignment 是一个**AI 驱动的引用语义核查工具**，解决综述写作中的核心问题：

**核心问题**：综述正文中可能出现"错配引用"或"幻觉引用"——即引用的论文并未真正做过文中所声称的事情。

**解决方案**：
- **脚本做确定性工作**：解析 LaTeX、提取引用与文献元信息、渲染 PDF/Word
- **AI 做语义判断**：理解句子含义、核对文献内容、最小化改写错配句子

**设计哲学**：
- **不为了改而改**：只修复致命性错误（虚假/错误/矛盾引用），不触碰文体问题
- 保留 LaTeX 命令完整性（`\cite{}`、`\ref{}`、`\label{}` 等）
- 最小化改动原则：只改写必要的句子，不整段重写
- 不引入新 bibkey、不伪造论文内容
- 不动如山原则：无法确定是否为致命性错误时，保留原样并报告为警告

## 功能概述

| 特性 | 说明 |
|------|------|
| **语义一致性核查** | AI 逐条检查引用是否与文献内容吻合 |
| **最小化改写** | 仅改写错配/幻觉引用的句子，保留 LaTeX 结构 |
| **结构化上下文** | 自动提取 PDF 摘要、BibTeX 元信息（含 DOI/URL、缺失 bibkey 提示），供 AI 核查 |
| **自动渲染** | 复用 `systematic-literature-review` 渲染脚本生成 PDF/Word |
| **可追溯报告** | 生成 `ai_alignment_report.md` 记录每条改动 |

## 错误优先级

本技能将问题分为三个优先级：

| 优先级 | 类型 | 说明 | 处理方式 |
|--------|------|------|----------|
| **P0** | 致命性错误 | 虚假引用、错误引用、矛盾引用 | 必须改写 |
| **P1** | 次要问题 | 支撑弱、定位偏差 | 仅警告，不改写 |
| **P2** | 禁止修改 | 文体问题、未引用句子 | 跳过，不触碰 |

核心原则：只改 P0，报告 P1，跳过 P2。

## 提示词示例

### 示例 1：基础核查（最简单）

```
你：请用 check-review-alignment 核查我工作目录中的综述引用。

技能：将执行以下步骤：
1. （仅渲染时）检查 systematic-literature-review 依赖是否可用
2. 定位 `*_review.tex` 和对应 `.bib`
3. 生成结构化输入（`ai_alignment_input.json`）
4. AI 逐条核查引用并最小化改写
5. 渲染 PDF/Word
```

### 示例 2：指定 tex 文件

```
你：请用 check-review-alignment 核查 HER2_review.tex 的引用。

技能：将使用指定的 `HER2_review.tex` 而非默认的 `*_review.tex`。
```

### 示例 3：结合生成流程

```
你：我刚用 systematic-literature-review 生成了综述，现在想核查引用。

技能：将复用已生成的 tex 和 bib 文件，执行引用核查与优化。
```

## 配置选项

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `citation_commands` | `cite`, `citep`, `citet`, ... | 识别的 LaTeX 引用命令 |
| `pdf.enabled` | `true` | 是否抽取 PDF 文本提供额外上下文 |
| `pdf.max_pages` | `2` | PDF 抽取页数上限 |
| `render.use_skill` | `systematic-literature-review` | 渲染依赖的 skill 名称 |
| `render.overwrite` | `true` | 是否覆盖已生成的 PDF/Word |
| `ai.input_limits.max_abstract_chars` | `2000` | BibTeX abstract 截断上限 |
| `ai.input_limits.max_pdf_excerpt_chars` | `3000` | PDF 摘要段截断上限 |
| `ai.modification.auto_apply` | `false` | 是否自动应用修改（推荐 false，由 AI 决定） |
| `ai.modification.error_priority` | （见 config） | 错误分级：P0 必修 / P1 仅警告 / P2 跳过 |
| `ai.modification.non_fatal_handling` | `skip` | 非致命问题（P1/P2）的处理策略 |
| `ai.paragraph_optimization.enabled` | `false` | 是否启用段落优化（不推荐；容易变成文体改写） |

在 `check-review-alignment/config.yaml` 中修改这些参数。

## 输出文件

所有中间文件保存在 `{work_dir}/.check-review-alignment/` 隐藏文件夹中，避免污染综述项目根目录。

| 文件 | 说明 |
|------|------|
| `.check-review-alignment/ai_alignment_report.md` | 核查报告：包含 Summary / Critical Fixes (P0) / Warnings (P1) / Rendering Result |
| `.check-review-alignment/ai_alignment_input.json` | 结构化输入（含 DOI/URL、缺失 bibkey 标记与 warning），便于 AI 快速核查 |
| `{主题}_review.tex` | 已优化的 LaTeX 正文（保存在 work_dir 根目录，保留 LaTeX 结构） |
| `{主题}_review.pdf` | 渲染生成的 PDF（保存在 work_dir 根目录） |
| `{主题}_review.docx` | 渲染生成的 Word（保存在 work_dir 根目录） |

## 备选用法（脚本/硬编码流程）

### 步骤 1：生成结构化输入（推荐）

```bash
# 进入 skill 根目录（安装后通常是 ~/.codex/skills/check-review-alignment 或 ~/.claude/skills/check-review-alignment）
cd /path/to/check-review-alignment

# 生成结构化输入（供 AI 快速核查）
python3 scripts/run_ai_alignment.py --work-dir "/path/to/your_review_dir" --prepare
```

**说明**：此步骤在 `{work_dir}/.check-review-alignment/` 目录下生成 `ai_alignment_input.json`，包含每条引用的文献元信息和 PDF 摘要段，便于宿主 AI 快速、可追溯地逐条核查。
补充：若目录内存在多个 `*_review.tex`，脚本会给出 warning 并提示使用 `--tex` 指定目标文件名。

### 步骤 2：AI 语义核查与改写

在 Claude/Codex 中触发本 skill，AI 将：
1. 读取 `.check-review-alignment/ai_alignment_input.json`
2. 逐条核查引用是否与文献内容吻合
3. 最小化改写错配/幻觉引用的句子
4. 写入 `.check-review-alignment/ai_alignment_report.md` 并更新 tex 文件

### 步骤 3：渲染 PDF/Word

```bash
# 渲染生成的 PDF 和 Word
python3 scripts/run_ai_alignment.py --work-dir "/path/to/your_review_dir" --render
```

**说明**：此步骤复用 `systematic-literature-review` 的渲染脚本，不直接调用 LLM API。

## 常见问题

### Q：check-review-alignment 和 systematic-literature-review 有什么区别？

A：两者用途不同：
- **systematic-literature-review**：从零开始生成综述正文（检索、筛选、阅读、写作）
- **check-review-alignment**：核查已有综述的引用是否正确，并最小化改写错配句子

### Q：技能没有被触发怎么办？

A：尝试用更具体的描述，如：
- "核查/优化 `{主题}_review.tex` 的引用"
- "运行 check-review-alignment"
- "检查综述的引用是否与文献内容吻合"

### Q：AI 会改写我的整篇综述吗？

A：不会。AI 遵循**最小化改动原则**：
- **只修复致命性错误**（P0）：虚假引用、错误引用、矛盾引用
- **仅警告次要问题**（P1）：支撑弱、定位偏差
- **禁止触碰文体问题**（P2）：表达不够优雅、语序可调整
- **不动如山**：无法确定时保留原样
- **最小改动**：只改写必要句子，不改写相邻无关句或整个段落
- 保留 LaTeX 命令完整性（`\cite{}`、`\ref{}`、`\label{}` 等）

### Q：为什么需要 `systematic-literature-review` 依赖？

A：仅当你需要渲染 PDF/Word（`--render` 或工作流步骤 5）时，check-review-alignment 才会复用 `systematic-literature-review` 的渲染脚本并强制检查依赖。仅生成结构化输入（`--prepare`）不依赖该 skill。

### Q：如何理解 `.check-review-alignment/ai_alignment_report.md`？

A：报告包含三部分：
- **Summary**：段落数、引用数、P0 修改数、P1 警告数、P2 跳过数等统计
- **Critical Fixes (P0)**：必须修复的致命性错误（原句/原因/新句/行号/优先级）
- **Warnings (P1)**：仅警告的问题（原句/原因/建议/行号/优先级）
- **Rendering Result**：PDF/Word 路径或错误摘要

### Q：PDF 文件太多会影响性能吗？

A：会。如果工作目录有大量 PDF，建议：
- 移动不相关的 PDF 到其他目录
- 或在 `config.yaml` 中设置 `pdf.enabled: false` 禁用 PDF 抽取

### Q：修改策略可以自定义吗？

A：可以。在 `config.yaml` 的 `ai.modification` 部分：
- `auto_apply: false`：由 AI 决定是否应用修改（推荐）
- `preserve_citations: true`：保留 LaTeX 引用命令
- `max_edits_per_sentence: 3`：每句最多修改次数

### Q：如果修改不满意，如何恢复到之前的版本？

A：取决于您使用的版本控制方式：

**Git 用户（推荐）**：
```bash
# 查看修改历史
git diff {主题}_review.tex

# 恢复到上一个提交
git checkout HEAD -- {主题}_review.tex

# 或恢复到特定提交
git checkout <commit-hash> -- {主题}_review.tex
```

**手动备份用户**：
```bash
# 恢复备份文件
cp {主题}_review.tex.backup {主题}_review.tex
```

**最佳实践**：
- 每次运行本技能前都创建新的 Git commit
- 使用描述性的 commit 信息，如 "backup: 运行 check-review-alignment 前的版本"
- 保留多个历史版本，方便对比和回滚

## 更多文档

- `SKILL.md` — 技能执行指令与硬性规范
- `config.yaml` — 可配置参数与版本号
- `systematic-literature-review` — 依赖技能（用于渲染）

---

**版本信息**：见 `check-review-alignment/config.yaml:skill_info.version`（唯一来源）。
