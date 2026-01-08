# MCP 多引擎文献检索：各引擎参数与节奏（可选附录）

> 本文件是 `references/mcp-literature-search.md` 的可选附录：当你需要更细的“各引擎怎么跑”的参数建议/节奏控制/失败退避时再看。
>
> Source of truth：
> - 通用检索策略与可复现留痕：`references/mcp-literature-search.md`
> - 跨领域差异点：`references/cross-domain-search-and-screening.md`

## 各引擎执行建议（参数与节奏）

### 引擎 0：Tavily（主力引擎，优先使用）

**优势**：
- 深度检索能力（`search_depth: advanced`）
- 对生物医学/学术内容覆盖好
- 支持时间范围过滤

**建议参数**（`max_results` 等数量口径应与 `config.yaml` 的 `pipeline_runner.search_max_results` / `profiles.*.pipeline_runner.search_max_results` 保持一致，需调整请改配置）：
```json
{
  "query": "...",
  "search_depth": "advanced",
  "max_results": 20,
  "time_range": "year",
  "topic": "general"
}
```

**检索策略**：
- 查询数量：10–20 个不同查询（同义词替换 + 子主题切片）
- 分页策略：不直接支持分页，用“不同查询式”模拟
- 间隔时间：2.0–6.0s（带随机抖动）
- 失败处理：连续失败 3 次 → 切换引擎

**典型查询模板**：
```
"{概念块1} {概念块2} {概念块3}"
"{概念块1} {概念块2} systematic review"
"{概念块1} {概念块2} meta-analysis"
"{子主题关键词} {概念块2} {概念块3}"
```

---

### 引擎 1：SearXNG（广覆盖引擎）

**优势**：
- 聚合多个搜索引擎
- 支持分页（`pageno`）
- 支持 `site:` 切片

**建议参数**：
```json
{
  "query": "...",
  "pageno": 1,
  "language": "en",
  "time_range": "year",
  "safesearch": "0"
}
```

**检索策略**：
- 查询数量：15–30 个不同查询
- 分页数量：每个查询 3–5 页（`pageno: 1..5`）
- 间隔时间：1.0–3.0s（每页），跨查询 2.0–6.0s
- 站点切片：优先学术数据库站点

**典型查询模板**：
```
{概念块1} {概念块2} {概念块3}
{概念块1} {概念块2} site:pubmed.ncbi.nlm.nih.gov
{概念块1} {概念块2} site:semanticscholar.org
{概念块1} {概念块2} 2023..2025
```

---

### 引擎 2：Paper Search（语义检索，做种子集）

**优势**：
- 语义理解能力强
- 适合找到“概念相似但术语不同”的文献
- 对 ML/CS 覆盖较好

**局限**：
- 对生物医学覆盖可能不足
- 不支持复杂查询语法

**建议参数**：
```json
{
  "query": "...",
  "limit": 25
}
```

**检索策略**：
- 查询数量：6–12 个不同查询（优先自然语言描述）
- 用途：作为种子集，快速定位高相关文献
- 间隔时间：0.8–2.5s
- 失败处理：连续返回为空/偏题 → 记录到日志并切换引擎（不要死磕）

---

### 引擎 3：DuckDuckGo（补充长尾）

**优势**：
- 覆盖面广
- 隐私友好

**局限**：
- 可能在某些环境下返回为空（反爬）
- 不支持高级语法

**建议参数**（数量口径同样应参考 `config.yaml` 的 `pipeline_runner.search_max_results` 系列配置）：
```json
{
  "query": "...",
  "max_results": 20
}
```

**检索策略**：
- 查询数量：10–20 个
- 重点：站点切片 + 子主题切片
- 间隔时间：2.0–6.0s（保守）
- 失败处理：连续返回为空 → 增加随机延迟/切换引擎

---

### 辅助工具：Crossref（DOI 核验）

**用途**：
- 反查 DOI 与元数据
- 验证文献存在性
- 按年份/类型过滤

**建议参数**：
```json
{
  "query": "...",
  "filters": "has-doi,from-pub-date:2020"
}
```

**检索策略**：
- 不作为主要检索引擎
- 用于补充核验已有候选文献的 DOI（并把核验结果写入 Search Log）
