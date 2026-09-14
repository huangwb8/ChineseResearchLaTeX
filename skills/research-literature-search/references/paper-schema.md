# `rls.paper.v1`

必需语义字段：`record_type=paper`、`schema_version`、稳定 `record_id`、非空 `title`、`authors: string[]`、`identifiers`（doi/pmid/arxiv/openalex/semantic_scholar 可空）、`venue`、`year`、`url`、`abstract`、`abstract_status`、`publication`、非空 `sources`、`query_matches` 和 `quality_warnings`。`venue`、`year`、`url` 与 `abstract` 可为 null，不能用虚构占位文本；`venue` 缺失时使用 `missing_venue` warning。

`doi` 必须规范为小写 `10.xxxx/...`，年份只能是 1000–3000 的整数或 null。缺失值使用 null/空数组。`sources` 至少记录 provider、provider record id、query id、rank 与来源 URL。新代码读取嵌套规范字段；`doi/venue/year/url/source` 等扁平字段只为旧 review wrapper 保留。

legacy 记录（只有 `title/year/id` 等最小字段）必须通过 `adapt_legacy_record`，并在 `quality_warnings` 加入 `legacy_adapted`。
