# MCP 多引擎检索速记

> 只有需要细调节奏和参数时再看；通用策略仍以主检索文档和 `config.yaml` 为准。

## 使用顺序

- `Tavily`：主力引擎
- `SearXNG`：广覆盖补充
- `Paper Search`：语义找种子集
- `DuckDuckGo`：补长尾
- `Crossref`：做 DOI 核验，不做主检索

## 各引擎最小建议

### Tavily

- 适合：主力检索
- 建议：较少但高质量查询，失败连续 3 次就切引擎

### SearXNG

- 适合：多页扩展和站点切片
- 建议：多查询 + 分页，不要无节制翻页

### Paper Search

- 适合：找到语义相近的种子论文
- 建议：查询数少一些，返回明显偏题就切走

### DuckDuckGo

- 适合：补长尾与站点切片
- 建议：保守速率，空结果连续出现就停止

### Crossref

- 适合：核验 DOI、年份、题名

## 总规则

- 结果数量、页数和节奏以 `config.yaml` 为准
- 缺口优先通过“扩 Query / citation chase / metadata 补齐”解决
- 不要把某一个引擎的失败当作整体检索失败
