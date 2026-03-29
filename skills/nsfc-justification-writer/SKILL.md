---
name: nsfc-justification-writer
description: 当用户明确要求"写/改 NSFC 立项依据""立项依据写作/重构"时使用。基于最小信息表输出价值与必要性、现状不足、科学问题/假说与项目切入点，并保持模板结构不被破坏。适用于 NSFC 及各类科研基金申请书的立项依据写作场景。
author: Bensz Conan
metadata:
  author: Bensz Conan
  short-description: 科研立项依据写作/重构
  keywords:
    - nsfc-justification-writer
    - 立项依据
    - 科学问题
    - 假说
    - 国内外现状
    - LaTeX
  triggers:
    - nsfc-justification-writer
    - 立项依据
    - 研究意义
    - 为什么要做
    - 国内外现状
    - 现有不足
    - 切入点
references: references/
config: config.yaml
---

# 科研立项依据写作器

## 与 bensz-collect-bugs 的协作约定

- 当用户环境中出现因本 skill 设计缺陷导致的 bug 时，优先使用 `bensz-collect-bugs` 按规范记录到 `~/.bensz-skills/bugs/`，严禁直接修改用户本地 Claude Code / Codex 中已安装的 skill 源码。
- 若 AI 仍可通过 workaround 继续完成用户任务，应先记录 bug，再继续完成当前任务。
- 当用户明确要求“report bensz skills bugs”等公开上报动作时，调用本地 `gh` 与 `bensz-collect-bugs`，仅上传新增 bug 到 `huangwb8/bensz-bugs`；不要 pull / clone 整个 bug 仓库。

## 输出契约

- 唯一默认写入落点：`extraTex/1.1.立项依据.tex`
- 禁止改动：`main.tex`、`extraTex/@config.tex`、任何 `.cls/.sty`
- 目标：把“为什么要做、现状为什么不够、科学问题是什么、项目如何切入”写清楚
- 默认写作导向是 `theoretical`，可在 `config.yaml:style.mode` 切为 `mixed` 或 `engineering`

## 输入

- 最小信息表优先使用 `references/info_form.md`
- 科学问题与假说口径统一看：
  - `references/scientific_question_guidelines.md`
  - `references/scientific_hypothesis_guidelines.md`
- 推荐用 `scripts/run.py init` 帮用户快速生成和补全信息表

## 硬规则

- 只编辑 `extraTex/1.1.立项依据.tex`
- 优先保留现有 `\subsubsection` 骨架，只替换正文
- 不写无法核验的“国际领先/国内首次”等表述
- 引用外部工作前先要求用户提供 DOI/链接或可核验题录信息
- 若 AI 不可用，必须回退到硬编码能力，不得直接停工

## 推荐工作流

1. 定位项目与目标文件。
2. 抽取现有小标题骨架与正文范围。
3. 用 `scripts/run.py coach --stage auto` 判断当前处于 skeleton / draft / revise / polish 哪一阶段。
4. 围绕 4 段闭环组织内容：
   - 价值与必要性
   - 现状与不足
   - 科学问题 / 科学假设
   - 本项目切入点与贡献
5. 做可核验性与引用守护，避免吹牛式表述。
6. 检查与 `2.1 研究内容` 的术语、缩写、指标一致性。
7. 解析目标字数；无显式要求时再用配置兜底。
8. 输出诊断、评审建议或安全写回结果。

## 关键能力

- Tier1 硬编码诊断：结构、字数、引用键、危险命令、高风险表述提示
- AI 语义能力：内容维度覆盖、吹牛式表述识别、术语一致性、阶段判断、示例推荐
- 安全写入：按 `\subsubsection{...}` 精确替换正文并自动备份
- 可视化报告、diff、rollback、review 建议

## 常用脚本

- `scripts/run.py init`
- `scripts/run.py coach --stage auto`
- `scripts/run.py diagnose`
- `scripts/run.py review`
- `scripts/run.py apply-section`
- `scripts/run.py diff`
- `scripts/run.py rollback`

## 只读集成

- 支持只读访问 `systematic-literature-review` 的结果目录，用于提取研究现状和验证引用一致性
- 集成逻辑见 `scripts/core/review_integration.py`
- 该集成是只读的，不得修改综述目录内容

## 重点参考

- `references/theoretical_innovation_guidelines.md`
- `references/methodology_term_examples.md`
- `references/boastful_expression_guidelines.md`
- `references/dimension_coverage_design.md`
- `references/dod_checklist.md`
- `scripts/README.md`
