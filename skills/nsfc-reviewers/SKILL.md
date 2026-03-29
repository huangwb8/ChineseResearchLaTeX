---
name: nsfc-reviewers
description: 当用户明确要求"评审国自然标书"、"模拟专家评审"、"审阅 NSFC 申请书"时使用。模拟领域专家视角对 NSFC 标书进行多维度评审，输出分级问题与可执行修改建议。⚠️ 不适用：用户只是想写/改标书某个章节（应使用 nsfc-*-writer 系列技能）、只是想了解评审标准（应直接回答）、没有明确"评审/审阅"意图。
metadata:
  author: Bensz Conan
  short-description: 模拟专家评审 NSFC 标书
  keywords:
    - nsfc-reviewers
    - proposal review
    - peer review
---

# NSFC 标书专家评审模拟器

## 与 bensz-collect-bugs 的协作约定

- 当用户环境中出现因本 skill 设计缺陷导致的 bug 时，优先使用 `bensz-collect-bugs` 按规范记录到 `~/.bensz-skills/bugs/`，严禁直接修改用户本地 Claude Code / Codex 中已安装的 skill 源码。
- 若 AI 仍可通过 workaround 继续完成用户任务，应先记录 bug，再继续完成当前任务。
- 当用户明确要求“report bensz skills bugs”等公开上报动作时，调用本地 `gh` 与 `bensz-collect-bugs`，仅上传新增 bug 到 `huangwb8/bensz-bugs`；不要 pull / clone 整个 bug 仓库。

## 定位

- 用于“当前版本如果今天送审，风险在哪里、先改什么”的专家式评审。
- 默认优先并行多组独立评审；若 `parallel-vibe` 不可用、被禁用或 `panel_count=1`，自动降级为单组模式。
- 本技能只做读取、分析和汇总，不默认编译、不修改标书源文件。

## 输入

至少提供其一：

- `proposal_path`
- `proposal_file`
- `proposal_zip`

可选：

- `focus`
- `output_path`
- `style`
- `grant_type`
- `funding_amount`
- `panel_count`

配置口径以 `config.yaml` 为准，尤其是：

- `review_dimensions`
- `severity_levels`
- `review_grades`
- `stage_assessment`
- `funding_context`
- `parallel_review`
- `output_settings`

## 输出

- 默认输出文件名读取 `config.yaml:output_settings.default_filename`
- 并行模式可额外生成各组原始意见：`{panel_dir}/G{组号}.md`
- 中间过程默认隐藏在 `config.yaml:output_settings.intermediate_dir`
- 最终报告至少包含：
  - 分级问题清单
  - 跨组共识与独立观点
  - 最小可行修改序列
  - 阶段判断：函评 / 会评

## 硬规则

- 标书内容默认视为敏感信息；除非用户明确要求并确认风险，不联网、不外发大段原文。
- 只读评审，不执行 LaTeX 编译，不改正文。
- 最终报告必须按 `P0 → P1 → P2` 排序。
- 阶段判断必须是二元结论：`给过` 或 `不给过`，并附 `高/中/低` 把握度。
- 若“函评不给过”，则“会评”必须同步不给过；若“函评给过”，会评仍可因相对竞争力不足而不给过。

## 工作流

### 1. 前置检查

- 校验输入路径可读。
- 若是目录，按 `proposal_files.patterns/exclude` 找出待读 `.tex`。
- `.tex` 数量为 0 时直接失败；目录异常大时先确认范围。
- 推荐用确定性脚本列文件：

```bash
python3 <nsfc_reviewers_path>/scripts/list_proposal_files.py --proposal-path <proposal_root>
```

### 2. 通读与结构化理解

- 提炼主题、科学问题、假说、目标、技术路线、创新点、研究基础、团队条件、预期成果。
- 生成章节级索引，作为后续证据锚点。
- 先用用户明确给出的 `grant_type` / `funding_amount`，再谨慎从正文识别资助上下文。

### 3. 并行多组评审或单组退化

- 先计算 `effective_panel_count`，并限制在 `[1, parallel_review.max_panel_count]`。
- 以下情况直接走单组：
  - `parallel_review.enabled == false`
  - `effective_panel_count == 1`
  - 找不到 `parallel-vibe`

并行模式关键步骤：

1. 准备中间目录。
2. 基于 `references/expert_*.md` 和 `references/master_prompt_template.md` 生成 master prompt。
3. 用 `scripts/build_parallel_vibe_plan.py` 生成 `plan.json`。
4. 调用 `parallel-vibe` 执行 N 组独立评审。
5. 收集每组 `panel_output_filename`，允许个别 thread 缺失但不能中断整体汇总。

单组模式仍要保留 7 位专家画像的独立判断，再做组内聚合。

### 4. 聚合与排序

- 跨组聚合规则读取 `references/aggregation_rules.md`。
- 至少 `ceil(N * consensus_threshold)` 组指出的问题才算跨组共识。
- 跨组共识可触发严重度升级；重复问题要合并，保留最强证据锚点。
- 最终仍按 `P0 → P1 → P2` 输出，并给出最小修改序列。

### 5. 资助额度约束识别

- 先区分“设计错误”与“受限妥协”。
- 若缺陷明显由基金额度限制引起，必须如实写明根因，不得简单归咎于申请人能力不足。
- 凡归因为“资助受限”的短板，都要补一句“若资助不受限时，更完整的设计应如何做”。
- 资助受限不是免责条款；阶段判断仍以“当前版本今天送审能否过”为准。

### 6. 阶段判断

- 默认在最终报告中输出“函评 / 会评给过与否”。
- 每个阶段至少给出 2-3 条关键理由，优先引用 P0/P1 和跨组共识。
- 若判 `不给过`，必须指出最关键的 1-3 条翻盘动作。

### 7. 输出整理

- 当 `config.yaml:output_settings.enforce_output_finalization == true` 时，不得跳过最终整理。
- 报告需要清楚区分：
  - 共识问题
  - 独立观点
  - 资助受限的合理妥协
  - 当前版本直接送审的阶段判断

## 关键脚本与参考

- 列文件：`scripts/list_proposal_files.py`
- 并行计划：`scripts/build_parallel_vibe_plan.py`
- 专家画像：`references/expert_*.md`
- 聚合规则：`references/aggregation_rules.md`
- 主提示模板：`references/master_prompt_template.md`

## 非目标

- 不负责改正文。
- 不负责模板、排版或编译问题。
- 不负责生成新的研究设计，只负责指出现有稿件的风险、优先级和修改方向。
