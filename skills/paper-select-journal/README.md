# paper-select-journal — 用户使用指南

本 README 面向使用者：如何触发并正确使用 `paper-select-journal` skill。
执行规范看 `SKILL.md`，默认参数看 `config.yaml`。

## 快速开始

推荐 Prompt：

```text
请使用 paper-select-journal skill 帮我的论文筛选合适投稿的 SCI 期刊。
输入：论文全文/摘要/稿件文件 + 我的投稿偏好（如果有）
输出：1 份 Markdown 选刊报告，按推荐度排序，最多 10 个期刊。
```

进阶 Prompt：

```text
请使用 paper-select-journal skill 帮我的论文筛选合适投稿的 SCI 期刊。
输入：论文全文/摘要/稿件文件 + 我的投稿偏好
输出：1 份 Markdown 选刊报告，按推荐度排序，最多 10 个期刊。
另外，还有下列参数约束：
- 优先考虑审稿较快的期刊
- 不要推荐预警或垃圾期刊
- 优先保留最近 3 个月发表过相似主题研究的期刊
```

## 这个 skill 会做什么

它不是只给一个“拍脑袋期刊名”。

它会按 5 步证据推进：

1. 先理解 manuscript，写出简洁但足够表达意图的稿件画像。
2. 用内置的 `2023IF.xlsx` 做最小硬过滤，生成 Set1 候选池。
3. 再由 AI 基于稿件画像自主规划，决定真正优先核验哪些候选。
4. 联网核验期刊官网、scope、业内认可度、中科院分区与风险信号，收敛到 Set2。
5. 抓取 Set2 最近 3 个月 PubMed 原始论文，并由 AI 做语义相关性判断，筛出真正值得进入最终报告的期刊。

## 输出文件

默认会在你的当前工作目录下创建隐藏工作区：

- `.bensz-api/skills/paper-select-journal/{yyyy-mm-dd-hh-mm}/`

最终报告默认在：

- `.bensz-api/skills/paper-select-journal/{yyyy-mm-dd-hh-mm}/reports/paper-select-journal-report.md`

中间文件也都留在隐藏目录里，不会散落到外面。
一旦你开始用这些脚本串流程，`manuscript_profile.json`、`set2_scope_review.json`、`final_recommendations.json` 也应继续放在当前 run 目录里，不要挪到隐藏工作区外。

## 常见使用场景

### 场景 1：我只有摘要

```text
请使用 paper-select-journal skill。
输入：下面这段摘要 + 我希望优先考虑肿瘤学相关 SCI 期刊
输出：Markdown 选刊报告
```

### 场景 2：我有完整 manuscript 文件

```text
请使用 paper-select-journal skill 帮我选刊。
输入：`/path/to/manuscript.tex`
输出：Markdown 选刊报告，最多 10 个期刊。
```

### 场景 3：我还想加主观偏好

```text
请使用 paper-select-journal skill 帮我选刊。
输入：论文全文 + 下列偏好
- 不要版面费特别高的期刊
- 优先 scope 比较聚焦的期刊
- 如果近期没发过类似主题论文，排名就往后放
输出：Markdown 选刊报告
```

## 输出里会包含什么

每个期刊至少会写：

- 影响因子
- 中科院小类及其分区
- 业内认可度
- 官方网站
- 为什么推荐
- 最近 3 个月类似主题论文表格
- 每篇证据论文与稿件的 AI 相关性说明

## 备选用法

如果你想手动跑脚本，常用入口是：

```bash
python3 <skill_root>/scripts/init_workspace.py --project-root .
python3 <skill_root>/scripts/shortlist_journals.py --workspace <run_dir> --profile <profile_json>
python3 <skill_root>/scripts/fetch_pubmed_recent.py --workspace <run_dir> --profile <profile_json> --scope-review <set2_json>
python3 <skill_root>/scripts/render_report.py --workspace <run_dir> --final-json <final_json>
```

这里的 `<skill_root>` 指 `paper-select-journal` 的真实安装目录，不要默认它就在你当前工作目录里。
如果你给 `render_report.py` 传 `--output`，输出路径也必须仍在 `<run_dir>` 里面。

其中 `shortlist_journals.py` 现在只负责最小硬过滤和候选池整理，不再用固定权重做语义打分。最终先看哪些候选、哪些进入推荐，由 AI 在后续步骤中自主规划。

`fetch_pubmed_recent.py` 只负责抓取并整理原始 PubMed 论文，不再用硬编码公式给论文打“相似度分”。最终是否进入推荐，由 AI 在后续步骤中做语义判断。

这里的 AI 不是额外接一个新的模型服务，而是直接使用当前运行 skill 的宿主环境算力：

- 如果你在 Claude Code 里运行，就由当前 Claude 会话完成判断
- 如果你在 Codex 里运行，就由当前 Codex 会话完成判断
- 默认不需要再接外部 AI API 来做 Set3 评定

## WHICHMODEL

截至 2026-04-05，建议优先使用“推理稳定、联网能力可靠、长上下文够用”的模型来跑这个 skill，因为它同时包含：

- 长文理解
- 期刊匹配判断
- 联网核验
- 证据整合与排序

推荐口径：

- 默认首选：`Claude Sonnet 4.5` 或 `gpt-5.4`
  - 适合完整跑一轮选刊：读 manuscript、生成画像、联网核验、整合证据、排序出最终报告。
- 预算更紧但仍需可靠推理：`Claude Haiku 4.5` 或 `gpt-5.4-mini`
  - 更适合已经有较完整 `manuscript_profile.json` 之后的复跑、补跑或报告微调。
- 不建议用于完整主流程：更轻量的 nano 级模型
  - 它们适合高吞吐简单任务，但不适合“选刊 + 联网核验 + 证据整合”这种高判断密度流程。

简单理解：

- 你要的是“第一次认真选刊”时，用 `Claude Sonnet 4.5` 或 `gpt-5.4`
- 你要的是“同一篇稿子改几个偏好后再重跑”，可以考虑 `Claude Haiku 4.5` 或 `gpt-5.4-mini`

## FAQ

### 为什么不是直接从 IF 最高开始推荐？

因为高 IF 不等于 scope 合适。这个 skill 默认把“AI 主导的 topic fit 判断 + 期刊质量 + 近期发文证据”放在更高优先级，而不是依赖一套固定关键词权重。

### 如果只找到 4-5 个很稳的候选怎么办？

那就只输出 4-5 个。这个 skill 默认宁缺毋滥。

### 为什么还要查最近 3 个月 PubMed？

因为这能更直接验证“这个期刊最近是否真的在发类似主题”，比单看 scope 更贴近真实投稿环境。现在脚本只负责把最近论文抓回来，是否真正“相似”交给 AI 做语义判断，能减少硬编码误判。

### Step 4b 的 AI 算力来自哪里？

默认就来自当前承载这个 skill 的工作环境，也就是 Claude Code 或 Codex 自己的模型能力。这个 skill 的设计前提不是“再起一个外部 AI 服务”，而是让宿主模型在拿到 `manuscript_profile.json` 和 `pubmed/recent_articles.json` 后，自主规划并完成 Set3 判断。
