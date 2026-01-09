---
name: nsfc-justification-writer
version: 0.2.0
description: 为 NSFC 2026 新模板正文“（一）立项依据”写作/重构 LaTeX 正文内容，基于最小信息表输出价值与必要性、现状不足、科学问题/假说与项目切入点，并保持模板结构不被破坏。适用于用户要写/改“立项依据、研究意义、国内外现状与不足、为什么要做、本项目切入点”等场景。
author: ChineseResearchLaTeX Project
metadata:
  short-description: NSFC 2026（立项依据）写作/重构
  keywords:
    - nsfc
    - 立项依据
    - 研究意义
    - 国内外现状
    - 科学问题
    - 假说
    - latex
  triggers:
    - 立项依据
    - 研究意义
    - 为什么要做
    - 国内外现状
    - 现有不足
    - 切入点
config: skills/nsfc-justification-writer/config.yaml
references: skills/nsfc-justification-writer/references/
---

# NSFC 2026（ 一）立项依据 写作器

## 目标输出（契约）

- **唯一写入落点**：`extraTex/1.1.立项依据.tex`
- **禁止改动**：`main.tex`、`extraTex/@config.tex`、任何 `.cls/.sty`
- **写作目标**：把“为什么要做”讲清楚，并为 `（二）研究内容` 铺垫“科学问题/假说与切入点”。

## 必需输入（最小信息表）

- 若用户未提供，请先收集/补全：[references/info_form.md](references/info_form.md)

## 工作流（按顺序执行）

1. **定位项目与目标文件**：确认 `project_root`，读取并仅编辑 `extraTex/1.1.立项依据.tex`。
2. **抽取现有骨架**：若文件已有 `\subsubsection` 等小标题，优先保留骨架，仅替换正文段落（除非用户要求重构层级）。
3. **生成“立项依据”主叙事**（建议 4 段闭环）：
   - 价值与必要性：痛点→影响范围/成本→为何现在必须做。
   - 现状与不足：主流路线/代表性工作→2–4 个明确不足（尽量可量化/可验证）。
   - 科学问题/核心假说：一句假说 + 1–3 个关键科学问题（断点式），指向“可验证”。
   - 本项目切入点与贡献：本项目相对现有工作的“差异化切口”，并用 1 句过渡到研究内容。
4. **可核验性与引用守护**：
   - 不写“国际领先/国内首次”等不可证明表述；需要对外部工作举证时，先让用户提供 DOI/链接或调用 `nsfc-bib-manager` 核验后再写 `\cite{...}`。
5. **跨章节一致性检查**：检查术语/缩写/指标口径是否能与 `2.1 研究内容` 对齐；必要时列出需用户确认的 3–5 个关键名词与指标。

## 新增：硬编码确定性能力（v0.2.0）

用于“先诊断→再生成→再安全写入→再验收”的闭环：

- **Tier1 硬编码诊断**：结构（4 个 `\subsubsection`）/引用键是否存在于 `.bib`/字数统计/不可核验表述与危险命令扫描
- **术语一致性矩阵**：基于 `config.yaml` 的 `terminology.alias_groups` 做跨章节一致性提示
- **安全写入工具**：按 `\subsubsection{...}` 精确定位并替换正文，写入白名单文件 + 备份（产物放在 `skills/nsfc-justification-writer/runs/`）

脚本入口：`skills/nsfc-justification-writer/scripts/run.py`（用法见 `skills/nsfc-justification-writer/scripts/README.md`）。

## 验收标准（Definition of Done）

- 见：[references/dod_checklist.md](references/dod_checklist.md)

## 变更记录

- 本技能不在本文档内维护变更历史；统一记录在根级 `CHANGELOG.md`。
