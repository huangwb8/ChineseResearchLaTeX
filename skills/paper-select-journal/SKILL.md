---
name: paper-select-journal
description: 当用户明确要求“推荐投稿期刊”“帮我的论文选 SCI 杂志”“这篇 manuscript 适合投哪些 journal”“期刊匹配/选刊/投稿建议”时必须使用。适用于用户提供全文、摘要、Markdown、LaTeX、PDF、Word 或混合材料的场景；本 skill 会基于 manuscript 与用户偏好，先用内置 `2023IF.xlsx` 做最小硬过滤生成候选池，再由宿主模型自主规划 Set1/Set2/Set3，并联网核验 scope / 质量 / 近 3 个月 PubMed 论文，最后输出 1 份按推荐度排序的 Markdown 选刊报告。⚠️ 不适用：用户只是想润色论文、只想翻译摘要、或只问某个单一期刊的官网信息而不需要系统选刊。
metadata:
  author: Bensz Conan
  short-description: 基于 manuscript + 2023IF + 实时联网核验的 SCI 选刊 skill
  keywords:
    - paper-select-journal
    - 选刊
    - 投稿期刊推荐
    - SCI journal selection
    - manuscript matching
---

# Paper Select Journal

## 核心原则

- 当前信息必须实时核验：scope、官网、业内认可度、中科院分区、近 3 个月论文都属于时效性信息，不能靠旧记忆。
- 中间文件只允许落在当前工作目录下的 `.bensz-api/skills/paper-select-journal/` 隐藏目录；用户若明确指定其他目录，才可覆盖默认值。
- Set1 不再依赖固定语义权重。脚本只负责最小硬过滤与候选池整理，真正的语义规划由当前宿主模型完成。
- Set1 不是最终答案。最终报告只保留证据充分的 Set3，最多 10 个期刊。
- 不能推荐明显预警、垃圾期刊或影响因子低于 `3` 的期刊；若确实保留低于 `3` 的例外，必须写明“为何它仍是领域内人类专家认可的稳妥选择”。
- 宁可少报，也不要为了凑满 10 个而硬凑。

## 输入与工作区

- 用户需求可选，manuscript 必选。
- manuscript 可来自粘贴的标题 / 摘要 / 全文片段，或本地 `.md`、`.txt`、`.tex`、`.pdf`、`.docx`，也可混合提供。
- 一旦进入隐藏工作区流程，后续供脚本读取的 `analysis/*.json` 必须保留在当前 run 目录内；不要把 `manuscript_profile.json`、`set2_scope_review.json`、`final_recommendations.json` 指到 run 目录外。

先初始化隐藏工作区：

```bash
python3 <skill_root>/scripts/init_workspace.py --project-root .
```

脚本会创建 `.bensz-api/skills/paper-select-journal/{yyyy-mm-dd-hh-mm}/`，其中至少包含：

- `inputs/`
- `analysis/`
- `candidates/`
- `pubmed/`
- `reports/`

后续所有中间文件都必须留在该 run 目录内。

## 工作流

### 1. 先写 manuscript 画像

完整理解论文后，把结果写入 `analysis/manuscript_profile.json`。

- 模板：`templates/manuscript_profile.template.json`
- 写法：`references/manuscript-profile.md`
最低字段：
- `title`
- `abstract`
- `keywords`
- `manuscript_summary`

画像的作用是帮助 AI 理解稿件，而不是喂给固定打分公式。
如果用户偏好复杂，优先把偏好写成自然语言放进 `target_journal_brief` 或 `notes`，不要为了脚本凑很多硬编码线索。
如果确实需要保留低 IF 的人工例外期刊，只能作为后续人工补录候选，并且必须在最终报告里解释“为什么它虽然低于阈值，仍是领域内稳妥选择”。

### 2. 用内置 `2023IF.xlsx` 做 Set1 候选池

内置目录：`assets/journal_catalog/2023IF.xlsx`

运行：

```bash
python3 <skill_root>/scripts/shortlist_journals.py \
  --workspace .bensz-api/skills/paper-select-journal/{yyyy-mm-dd-hh-mm} \
  --profile .bensz-api/skills/paper-select-journal/{yyyy-mm-dd-hh-mm}/analysis/manuscript_profile.json
```

产物：

- `candidates/set1_candidates.json`
- `candidates/set1_candidates.md`

这里的脚本只做最小硬过滤：

- 影响因子下限
- 用户明确排除的期刊
- 基础元数据整理（JIF、分区、OA 比例、引用量）

不要把这一步输出误解为“已经按语义排好序的最终 shortlist”。
你必须读取该候选池，再结合 manuscript 自主规划真正值得进入 Set2 的期刊。

### 3. 联网核验 scope、官网、分区与质量，得到 Set2

根据 `candidates/set1_candidates.json` 与 manuscript 画像，自主决定先核验哪些候选，并逐个联网核验：

- 官方网站
- Aims & Scope
- 中科院小类及其分区
- 业内认可度
- 是否存在预警 / 垃圾期刊信号

优先使用：

- 期刊官网
- PubMed / NLM
- 主流出版社页面
- 可信的分区信息来源

把通过核验的期刊写入：

- `analysis/set2_scope_review.json`

模板：`templates/scope_review.template.json`
核验口径：`references/journal-quality-checklist.md`

### 4a. 抓取 Set2 最近 3 个月 PubMed 原始论文证据

运行：

```bash
python3 <skill_root>/scripts/fetch_pubmed_recent.py \
  --workspace .bensz-api/skills/paper-select-journal/{yyyy-mm-dd-hh-mm} \
  --profile .bensz-api/skills/paper-select-journal/{yyyy-mm-dd-hh-mm}/analysis/manuscript_profile.json \
  --scope-review .bensz-api/skills/paper-select-journal/{yyyy-mm-dd-hh-mm}/analysis/set2_scope_review.json
```

产物：

- `pubmed/recent_articles.json`
- `pubmed/recent_articles.md`

这里只提供原始证据，不负责打分或排序。脚本只做 API 调用、XML 解析和按日期整理。

### 4b. AI 评定主题相似性，决定哪些期刊进入 Set3

你必须同时阅读：

- `analysis/manuscript_profile.json`
- `pubmed/recent_articles.json`

这里的“AI”指当前执行本 skill 的宿主模型本身：

- Claude Code 中由当前 Claude 会话完成
- Codex 中由当前 Codex 会话完成
- 不要为 Step 4b 额外调用外部 AI API、独立模型服务或单独打分脚本

也就是说，Step 4b 的规划、语义判断、Set3 去留决策和 `set3_similarity_review.json` 写入，都必须用当前工作环境已提供的 AI 算力原生完成。

逐个判断 Set2 期刊最近 3 个月论文与稿件在以下维度上的语义相关性：

- 主题是否真的对口，而不只是 token 碰撞
- 研究问题是否接近
- 方法学是否接近
- 相关论文数量与密度是否足以支持进入最终推荐

执行时先快速浏览全部 Set2 近期论文形成比较框架，再逐刊做语义判断，最后统一决定 Set3 去留并写出可复核理由。
不要再把这一步退化成机械 token 打分或硬编码加权公式。

把结论写入：

- `analysis/set3_similarity_review.json`

模板：`templates/set3_similarity_review.template.json`

每个期刊至少要写：

- `journal_name`
- `include_in_set3`
- `similarity_assessment`
- `relevant_articles`
- `irrelevant_articles_count`
- `overall_relevance_level`

`overall_relevance_level` 只允许：

- `high`
- `medium`
- `low`
- `none`

### 5. 形成最终推荐 JSON

基于 `analysis/set3_similarity_review.json`，把最终最多 `10` 个期刊写入 `analysis/final_recommendations.json`。

- 模板：`templates/final_recommendations.template.json`
- 字段说明：`references/report-schema.md`

必须保留：
- 影响因子
- 中科院小类及其分区
- 业内认可度
- 官方网站
- 为什么推荐
- 最近 3 个月类似主题论文
- 每篇证据论文的 AI `relevance`

### 6. 渲染最终 Markdown 报告

运行：

```bash
python3 <skill_root>/scripts/render_report.py \
  --workspace .bensz-api/skills/paper-select-journal/{yyyy-mm-dd-hh-mm} \
  --final-json .bensz-api/skills/paper-select-journal/{yyyy-mm-dd-hh-mm}/analysis/final_recommendations.json
```

最终输出：

- `reports/paper-select-journal-report.md`

如需 `--output` 覆盖默认文件名，也只能写到当前 run 目录内部，不能把最终 Markdown 报告写到隐藏工作区之外。

## 最终报告要求

- 所有期刊写在同一个 Markdown 文件里
- 每个期刊使用 `#` 层级，下面按需用 `##`、`###`
- 每个期刊都要写明：影响因子、中科院小类及分区、业内认可度、官方网站、推荐理由，以及最近 3 个月类似主题论文表格和 AI 相关性说明

## 决策规则

- scope 不匹配，再高 IF 也不要强推
- 有明显预警 / 垃圾期刊风险，直接淘汰
- 近 3 个月没有相似主题论文，不一定淘汰，但推荐度要下调
- `include_in_set3` 为 `false` 的期刊，不要进入最终推荐
- 中科院分区无法可靠核验时，优先换成信息更透明的候选
- 用户未明确偏好时，自主选择最稳妥方案，不要把提问变成阻塞

## 命令路径说明

- ` <skill_root> ` 表示当前 skill 的真实安装目录。
- 不要假设用户当前工作目录里一定有 `paper-select-journal/` 源码副本。
- 如果你已经处在 skill 根目录，也可以直接运行 `python3 scripts/...`。

## 参考文件

- `references/manuscript-profile.md`
- `references/journal-quality-checklist.md`
- `references/report-schema.md`
