---
name: nsfc-justification-writer
version: 0.7.0
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
- **AI 依赖**：默认使用运行环境提供的 Claude Code / Codex 原生智能（无需配置任何外部 API Key，AI 不可用会自动回退到硬编码能力）

## 必需输入（最小信息表）

- 若用户未提供，请先收集/补全：[references/info_form.md](references/info_form.md)

> 推荐：用脚本快速生成信息表（并可交互填写），见 `skills/nsfc-justification-writer/scripts/run.py init`。

## 工作流（按顺序执行）

1. **定位项目与目标文件**：确认 `project_root`，读取并仅编辑 `extraTex/1.1.立项依据.tex`。
2. **抽取现有骨架**：若文件已有 `\subsubsection` 等小标题，优先保留骨架，仅替换正文段落（除非用户要求重构层级）。默认不强制标题精确匹配（`strict_title_match=false`），更关注“内容维度是否覆盖”。
3. **渐进式写作引导（主推）**：先骨架→再段落→再修订→再润色→再验收（避免一步到位压力）
   - 使用 `scripts/run.py coach --stage auto` 自动判断当前阶段并给出“本轮只做三件事 + 需要你补充的问题 + 可复制提示词”
   - 每轮只改一个 `\subsubsection` 的正文，配合 `apply-section` 安全写入并自动备份
4. **生成“立项依据”主叙事**（建议 4 段闭环，AI 会检查内容维度覆盖而非死盯标题）：
   - 价值与必要性：痛点→影响范围/成本→为何现在必须做。
   - 现状与不足：主流路线/代表性工作→2–4 个明确不足（尽量可量化/可验证）。
   - 科学问题/核心假说：一句假说 + 1–3 个关键科学问题（断点式），指向“可验证”。
   - 本项目切入点与贡献：本项目相对现有工作的“差异化切口”，并用 1 句过渡到研究内容。
5. **可核验性与引用守护**：
   - AI 语义识别“可能引起评审不适的表述”（绝对化/填补空白/无依据夸大/自我定性），并给出改写建议；硬编码高风险词仅作提示，不做机械阻断。
   - 不写“国际领先/国内首次”等不可证明表述；需要对外部工作举证时，先让用户提供 DOI/链接或调用 `nsfc-bib-manager` 核验后再写 `\cite{...}`。
6. **跨章节一致性检查**：检查术语/缩写/指标口径是否能与 `2.1 研究内容` 对齐；必要时列出需用户确认的 3–5 个关键名词与指标。
7. **目标字数解析**：优先解析用户意图/信息表中的“字数”/“±范围”/区间描述；无显式指示时再使用配置兜底。

## 配置校验与大文件支持（可选）

- 配置校验：`python skills/nsfc-justification-writer/scripts/run.py validate-config`
- 大文件 Tier2：`diagnose/review --tier2 --chunk-size 12000 --max-chunks 20`（支持 `.cache/ai` 缓存；超大文件会优先使用流式分块以降低峰值内存；用 `--fresh` 强制重算）
- 说明：本仓库脚本层不会“默认直连外部大模型”；AI 能力是否可用取决于运行环境是否注入 responder（不可用会自动回退到硬编码能力）

## Prompt 模板可配置化（可选）

`config.yaml` / `preset.yaml` / `override.yaml` 的 `prompts.*` 支持两种形式：

- **文件路径**：如 `prompts/tier2_diagnostic.txt`
- **直接写多行 Prompt**：在 YAML 中用 `|` 写入多行文本（适合不同领域改侧重点）

也支持按 preset 变体覆盖：例如当 `--preset medical` 时，可提供 `prompts.tier2_diagnostic_medical`。

## 推荐 `\\subsubsection` 标题与内容映射

说明：模板与 `config.yaml` 默认推荐 4 个 `\\subsubsection` 标题（`structure.recommended_subsubsections`），而“4 段闭环”是内容叙事逻辑。为避免用户困惑，推荐按下表映射写作：

| `\\subsubsection` 标题 | 对应叙事段落 | 核心写作要素 |
|---|---|---|
| 研究背景 | 价值与必要性 | 痛点→影响范围/成本→为何现在必须做 |
| 国内外研究现状 | 现状与不足 | 主流路线→代表性工作→2–4 条不足（可验证/可量化） |
| 现有研究的局限性 | 科学问题/核心假说 | 可证伪假说→关键科学问题→验证维度（数据/指标/对照） |
| 研究切入点 | 本项目切入点与贡献 | 差异化切口→可交付/指标→承上启下到 2.1 研究内容 |

如用户确需改小标题：建议仍保持 4 段结构，并先统一标题骨架（见 `templates/structure_template.tex`）；结构检查不再机械匹配标题，但仍要求至少 4 个小节。

## 关键能力

用于“先诊断→再生成→再安全写入→再验收”的闭环：

- **Tier1 硬编码诊断**：结构（≥4 个 `\subsubsection`）/引用键是否存在于 `.bib`/DOI 缺失与格式异常提示/字数统计/高风险表述提示与危险命令扫描
- **内容维度覆盖检查（AI）**：不依赖标题用词，检查“价值与必要性/现状与不足/科学问题/切入点”是否被覆盖
- **吹牛式表述识别（AI）**：识别绝对化/填补空白式/无依据夸大/自我定性，输出改写建议
- **跨章节一致性矩阵**：基于 `config.yaml` 的 `terminology.dimensions`（研究对象/指标/术语）做跨章节一致性提示
- **AI 术语一致性（可选）**：当 AI 可用且 `terminology.mode=auto/ai` 时，额外给出语义视角的“同义词/缩写混用”检查与修改建议（不可用则仅输出矩阵）
- **安全写入工具**：按 `\subsubsection{...}` 精确定位并替换正文，写入白名单文件 + 备份（产物放在 `skills/nsfc-justification-writer/runs/`）
- **写入前质量闸门（可选）**：`apply-section --strict-quality` 仅对“本次新增正文”做高风险词/危险命令扫描；若 AI 可用则叠加“吹牛式表述”语义阻断，避免被历史遗留内容卡死
- **评审建议生成器**：基于 DoD + 诊断结果输出“评审人会问什么 + 怎么改”（`scripts/run.py review`）
- **可视化 HTML 诊断报告**：快速定位问题（`scripts/run.py diagnose --html-report auto`）
- **版本 diff/回滚**：基于 runs 备份做差异查看与一键回滚（`scripts/run.py diff/rollback`）
- **示例推荐**：从 `examples/` 读取 `*.metadata.yaml` 关键词，辅助按主题匹配参考骨架（`scripts/run.py coach --topic ...` / `scripts/run.py examples`）
- **AI 示例推荐（可选）**：当 AI 可用时，优先进行语义匹配并给出“推荐理由”（不可用则回退到关键词/类别启发式）
- **AI 阶段判断（可选）**：coach 在 `--stage auto` 时，可用 AI 综合字数/结构/质量状态推断“skeleton/draft/revise/polish/final”，AI 不可用时回退到硬编码阈值
- **配置覆盖与预设**：支持 `--preset medical/engineering` 与 `~/.config/nsfc-justification-writer/override.yaml` 覆盖术语维度等参数（需要时可用 `--no-user-override` 关闭）

脚本入口：`skills/nsfc-justification-writer/scripts/run.py`（用法见 `skills/nsfc-justification-writer/scripts/README.md`）。

## 验收标准（Definition of Done）

- 见：[references/dod_checklist.md](references/dod_checklist.md)

## 变更记录

- 本技能不在本文档内维护变更历史；统一记录在根级 `CHANGELOG.md`。
