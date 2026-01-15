---
name: nsfc-research-content-writer
version: 0.2.1
description: 为 NSFC 正文"（二）研究内容"写作/重构，并同步编排"特色与创新"和"三年年度研究计划"，输出可直接落到 LaTeX 模板的三个 extraTex 文件。适用于用户要写/改"研究内容、研究目标、关键科学问题、技术路线、创新点、三年计划/里程碑"等场景。
author: ChineseResearchLaTeX Project
metadata:
  short-description: NSFC（研究内容+创新+年度计划）编排写作
  keywords:
    - nsfc
    - 研究内容
    - 研究目标
    - 技术路线
    - 特色与创新
    - 年度研究计划
    - 里程碑
    - latex
  triggers:
    - 研究内容
    - 研究目标
    - 关键科学问题
    - 技术路线
    - 特色与创新
    - 创新点
    - 年度计划
    - 年度研究计划
config: skills/nsfc-research-content-writer/config.yaml
references: skills/nsfc-research-content-writer/references/
---

# NSFC（二）研究内容编排写作器

## 目标输出（契约）

- **写入落点（3 个文件）**：
  - `extraTex/2.1.研究内容.tex`
  - `extraTex/2.2.特色与创新.tex`
  - `extraTex/2.3.年度研究计划.tex`
- **禁止改动**：`main.tex`、`extraTex/@config.tex`、任何 `.cls/.sty`
- **编排原则**：先把 `2.1` 写成“可验证闭环”，再从 `2.1` 抽取创新点生成 `2.2`，最后把 `2.1` 的任务拆分成三年里程碑生成 `2.3`。

## 参数与输出模式（建议显式提供）

- `project_root`：标书项目根目录（如 `projects/NSFC_Young`）
- `output_mode`（默认 `apply`）：
  - `preview`：不直接写入文件；输出三段可复制粘贴的 LaTeX 正文草稿，并标注应写入的目标文件路径
  - `apply`：仅写入三份目标文件（见“目标输出”），不触碰其他文件

## 必需输入（最小信息表）

- 若用户未提供，请先收集/补全：[references/info_form.md](references/info_form.md)

## 写入安全约束（必须遵守）

1. 仅编辑三份 `extraTex/2.*.tex` 文件；不得修改 `main.tex`、`extraTex/@config.tex`、任何 `.cls/.sty`
2. 目标文件若已包含标题命令（如 `\\subsection{...}` / `\\subsubsection{...}`），**只替换正文内容**，不改标题与结构层级
3. 信息不全时先提问补齐，不要用“看起来像真的”的细节硬写

## 工作流（按顺序执行）

1. **定位项目与目标文件**：确认 `project_root`，读取并仅编辑三份 `extraTex/2.*.tex` 文件；如目标文件不存在，提示用户先初始化/拷贝模板项目。
2. **固定“子目标三件套”**：把目标拆成 3–4 个子目标（建议编号 `S1–S4` 便于后续回溯），并对每个子目标强制写清：
   - 指标（可判定/可验收）
   - 对照/基线（与谁比、怎么比）
   - 数据来源/验证方案（样本/实验体系/评估方法）
3. **生成 `2.1 研究内容`**（以“问题→目标→内容→路线→验证”为主线）：
   - 研究问题与总体目标（不超过 2 段）
   - 子目标列表（3–4 个，逐条带三件套）
   - 研究内容与任务分解（对齐子目标，避免“写一堆方法但看不出解决什么”）
   - 技术路线与验证口径（对照/消融/外部验证/泄漏防控/统计方法）
4. **从 `2.1` 抽取 `2.2 特色与创新`**：
   - 1–3 条即可；每条用“相对坐标系”表达：与主流路线 A/B 相比，本项目在 X 上不同，预计带来 Y，可用 Z 验证。
   - 避免绝对化措辞（如“首次”“领先”）；如确需使用，必须给出可核验证据或改写为可审稿的相对表述。
5. **从 `2.1` 推导 `2.3 年度研究计划`**（三年不跨年）：
   - 每年：年度目标 → 关键任务 → 里程碑（可验收）→ 可交付成果（论文/数据/原型/规范/软件等）
   - 里程碑必须与子目标挂钩（否则评审会认为“计划与研究内容脱节”）
6. **一致性校验**：
   - 检查 `2.2` 创新点是否能回溯到 `2.1` 的具体任务与验证；
   - 检查 `2.3` 里程碑是否覆盖全部子目标，且每年都有可交付物。
   - 术语口径对齐：研究对象/缩写/指标命名尽量与 `（一）立项依据`、`（三）研究基础` 保持一致（如项目中已存在）

## 验收标准（Definition of Done）

- 见：[references/dod_checklist.md](references/dod_checklist.md)

## 写作小抄（可选）

- 子目标“三件套”示例：[references/subgoal_triplet_examples.md](references/subgoal_triplet_examples.md)
- 创新点“相对坐标系”示例：[references/relative_coordinate_examples.md](references/relative_coordinate_examples.md)
- 年度计划模板（确保里程碑可验收）：[references/yearly_plan_template.md](references/yearly_plan_template.md)
- 三个输出文件的最小结构骨架（可复制粘贴）：[references/output_skeletons.md](references/output_skeletons.md)
- 常见写作反模式与改写：[references/anti_patterns.md](references/anti_patterns.md)
- 验证口径菜单（对照/消融/外部验证/统计/泄漏防控）：[references/validation_menu.md](references/validation_menu.md)
- 术语口径对齐表（跨章节一致）：[references/terminology_sheet.md](references/terminology_sheet.md)

## 变更记录

- 本技能不在本文档内维护变更历史；统一记录在根级 `CHANGELOG.md`。
