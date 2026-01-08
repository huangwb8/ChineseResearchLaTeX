# 人类寿命与生活方式（Premium 级）工作条件

## Meta

- 主题：人类寿命与生活方式（Lifestyle factors and human longevity）
- 证据偏好：循证医学研究为主，优先大型前瞻性队列研究，其次系统综述/Meta 分析、随机对照试验（如有），并在讨论中强调因果推断与偏倚来源。
- 时间范围：以 2015–2025 年为主；允许极少数更早但具有“奠基性/方法学关键性”的证据（在正文引用中严格控制数量）。
- 档位：Premium（目标正文字数 10000–15000；目标引用 key 数 80–150）。
- 工作目录：`longevity-lifestyle-01/`

## Search Plan

本项目使用多查询并行检索（OpenAlex），围绕“寿命/死亡结局 + 生活方式暴露 + 队列/循证研究”构建查询变体，以提升覆盖与降低无关主题比例。

查询文件：
- `longevity-lifestyle-01/.systematic-literature-review/artifacts/queries_longevity_lifestyle_01.json`

查询要点（示例）：
- 综合生活方式评分（healthy lifestyle score）与寿命/全因死亡
- 运动/体能/久坐与全因死亡（含加速度计研究、剂量-反应）
- 饮食模式（地中海/植物性/超加工食品等）与死亡风险
- 睡眠与昼夜节律与死亡/健康老龄化
- 烟草与酒精（含方法学争议的更新证据）
- 心理社会因素（孤独/社会隔离等）与死亡
- 衰老标志物（表观遗传钟等）与生活方式（机制与中间表型）

## Search Log

检索输出：
- 候选文献库：`longevity-lifestyle-01/.systematic-literature-review/artifacts/papers_longevity_lifestyle_01.jsonl`
- 检索日志：`longevity-lifestyle-01/.systematic-literature-review/artifacts/search_log_longevity_lifestyle_01.json`

本次检索（多查询）合并后上限为 500 条候选记录；随后进入去重与评分阶段。

## Dedup

去重输出：
- 去重后候选库：`longevity-lifestyle-01/.systematic-literature-review/artifacts/papers_deduped_longevity_lifestyle_01.jsonl`
- 去重映射：`longevity-lifestyle-01/.systematic-literature-review/artifacts/dedupe_map_longevity_lifestyle_01.json`

去重策略：
- 以 DOI 及标题相似度为核心，辅以 token Jaccard 与年份窗口进行合并，尽量减少同一研究的多来源重复记录。

## Relevance Scoring & Selection

评分文件：
- `longevity-lifestyle-01/.systematic-literature-review/artifacts/scored_papers_longevity_lifestyle_01.jsonl`

评分与标注原则（面向本综述主题的定制）：
- 以“寿命/全因死亡/健康寿命/衰弱”等结局信号 + “生活方式暴露（饮食、运动/久坐、睡眠、烟酒、心理社会因素等）”为核心相关性依据。
- 对“明确的前瞻性队列/系统综述/Meta 分析/随机试验/孟德尔随机化/指南”给予加权；对非人群研究、与生活方式无关的疾病管理型指南给予惩罚。
- 时间偏好：2015–2025 年为主；2015 年以前文献在评分上被系统性降权（除非同时具备强结局 + 强暴露 + 高证据等级特征）。
- 子主题标签用于写作结构归纳，控制在 3–7 个主子主题范围内。

选文输出（按评分高优先 + 数量上限控制）：
- 选中文献：`longevity-lifestyle-01/.systematic-literature-review/artifacts/selected_papers_longevity_lifestyle_01.jsonl`
- 选文理由：`longevity-lifestyle-01/.systematic-literature-review/artifacts/selection_rationale_longevity_lifestyle_01.yaml`
- BibTeX：`longevity-lifestyle-01/longevity_lifestyle_01_参考文献.bib`

说明：
- BibTeX 由流水线自动生成，个别条目可能缺失 DOI/作者信息（已保留并在生成日志中提示）。正文写作时优先使用元数据更完整、且符合 2015–2025 时间窗口的研究作为关键证据。

## Review Structure

正文（LaTeX）结构规划：
- 摘要
- 引言：寿命/健康寿命概念、生活方式与寿命关联的证据谱系、方法学关键点（混杂/反向因果/测量误差）
- 子主题（控制 3–7 个）：
  1) 综合生活方式评分与寿命差异
  2) 饮食与营养模式（含超加工食品、植物性饮食、膳食质量）
  3) 运动、体能与久坐（含剂量-反应与年龄差异）
  4) 睡眠与昼夜节律
  5) 烟草与酒精
  6) 心理社会因素与环境（孤独/社会隔离等）
  7) 面向不同年龄段的人群达成长寿的最佳实践（周计划、可操作指标；结合指南/共识）
- 讨论：证据等级与因果推断、跨人群外推性、组合干预与“可行性边界”
- 展望：精细化暴露测量（可穿戴/多组学）、个体化处方与真实世界评估
- 结论：可行动要点与研究空白

## Data Extraction Table（数据抽取表）

数据抽取表路径（含 score/subtopic 及简单字段抽取）：
- `longevity-lifestyle-01/.systematic-literature-review/reference/data_extraction_table.md`

## Validation

字数预算与验证：
- 字数预算：`longevity-lifestyle-01/.systematic-literature-review/artifacts/word_budget_final.csv`（目标总字数约 12500）
- 最终硬校验由流水线阶段 6 触发，包含：
  - 正文字数（10000–15000）
  - 唯一引用 key 数（80–150）
  - 必需章节存在
  - `\cite{key}` 与 `.bib` 的 key 一致性

