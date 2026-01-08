---
name: nsfc-research-foundation-writer
version: 0.1.0
description: 为 NSFC 2026 新模板正文“（三）研究基础”写作/重构，并同步编排“工作条件”和“研究风险应对”，用证据链证明项目可行、资源条件对位研究内容、风险预案可执行。适用于用户要写/改“研究基础、前期工作、可行性分析、工作条件、平台团队、风险应对”等场景。
author: ChineseResearchLaTeX Project
metadata:
  short-description: NSFC 2026（研究基础+工作条件+风险应对）编排写作
  keywords:
    - nsfc
    - 研究基础
    - 可行性分析
    - 工作条件
    - 平台团队
    - 风险应对
    - latex
  triggers:
    - 研究基础
    - 前期基础
    - 可行性
    - 工作条件
    - 平台
    - 风险应对
config: skills/nsfc-research-foundation-writer/config.yaml
references: skills/nsfc-research-foundation-writer/references/
---

# NSFC 2026（ 三）研究基础 编排写作器

## 目标输出（契约）

- **写入落点（2 个文件）**：
  - `extraTex/3.1.研究基础.tex`（包含“研究风险的应对措施”）
  - `extraTex/3.2.工作条件.tex`
- **禁止改动**：`main.tex`、`extraTex/@config.tex`、任何 `.cls/.sty`
- **核心目标**：用“证据链 + 条件对位 + 风险预案”回答评审的三个问题：你做过吗？你做得成吗？出问题你怎么兜底？

## 必需输入（最小信息表）

- 若用户未提供，请先收集/补全：[references/info_form.md](references/info_form.md)

## 工作流（按顺序执行）

1. **定位项目与目标文件**：确认 `project_root`，读取并仅编辑 `extraTex/3.1.研究基础.tex` 与 `extraTex/3.2.工作条件.tex`。
2. **生成 `3.1 研究基础`（证据链优先）**：
   - 研究积累：围绕 `2.1` 的关键任务，列出“做过什么/掌握什么/已有平台什么”。
   - 阶段性成果：只写可核验内容（论文/专利/数据/原型/预实验现象）；不确定的细节用占位符要求用户补齐。
   - 可行性四维：理论/技术/团队/条件各给 1–3 个支撑点，并与研究内容逐条对齐。
3. **在 `3.1` 中显式写“研究风险的应对措施”**：
   - 至少 3 条风险（技术/进度/资源各至少 1 条）
   - 每条：风险描述 → 早期信号（触发阈值/现象）→ 预案/替代路线（含降级目标与可交付）
4. **生成 `3.2 工作条件`（条件对位研究内容）**：
   - 已具备条件：平台/数据/样本/算力/设备/团队分工/合规路径
   - 尚缺条件与解决途径：采购/合作/替代数据源/实验降级方案/时间表与责任人（如用户提供）
5. **一致性校验**：
   - 检查 `3.2` 是否能逐条支撑 `2.1` 的关键任务；
   - 检查风险预案是否与年度计划可兼容（比如：第一年样本获取风险 → 有替代数据源与降级验证方案）。

## 验收标准（Definition of Done）

- 见：[references/dod_checklist.md](references/dod_checklist.md)

## 变更记录

- 本技能不在本文档内维护变更历史；统一记录在根级 `CHANGELOG.md`。

