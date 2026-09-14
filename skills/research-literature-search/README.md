# Research Literature Search

`research-literature-search` 将“查询输入 → 多源召回 → 规范化 → canonical 去重 → 来源审计”做成可独立复用的证据生产环节。它适合只想先拿候选文献池、为研究选题准备查新材料，或被综述/标书等下游流程消费的场景。

当前版本：`v1.0.3`。

manifest 校验使用独立命名的 `rls_contract` 模块，避免与 `research-literature-review` 的同名 `query_contract` 在同一 Python 进程中互相遮蔽。

## 快速开始

准备至少 5 条查询：

```json
{"queries": [
  {"query": "HER2 antibody-drug conjugate breast cancer clinical trial", "rationale": "核心临床证据"},
  {"query": "HER2 ADC resistance mechanism breast cancer", "rationale": "耐药机制"},
  {"query": "HER2 targeted drug delivery review", "rationale": "递送与综述"},
  {"query": "trastuzumab deruxtecan safety efficacy", "rationale": "代表性药物"},
  {"query": "breast cancer antibody drug conjugate biomarker", "rationale": "生物标志物"}
]}
```

运行并校验：

```bash
python3 skills/research-literature-search/scripts/search_runner.py run \
  --topic "HER2 ADC in breast cancer" --query-file queries.json \
  --output-dir ./.bensz-api/search-bundle
python3 skills/research-literature-search/scripts/search_runner.py validate \
  --bundle ./.bensz-api/search-bundle
```

可用 `--provider-order openalex,semantic_scholar,crossref` 固定来源顺序，
并用 `--min-year/--max-year`、`--publication-type`、`--language`、`--open-access`
设置过滤条件；指定 `--scope-root` 可强制 bundle 留在任务工作区内。

校验通过后，下游默认读取 `candidates_deduped.jsonl`，并使用 `provenance.jsonl` 与 `dedupe_map.json` 追溯来源和合并理由。

## 与综述 Skill 的关系

`research-literature-review` 保留原名、旧 CLI 和完整写作/导出功能，但阶段 1/2 必须消费本 Skill 产生的 manifest bundle。检索 Skill 不做 AI 相关性评分、最终选文、BibTeX、正文或 PDF/Word。

## 失败与部分成功

输入数量不合法、路径越界、所有 provider 不可用或没有候选时返回 `failed` 和具体 `failure_code`。仍有候选但 provider 失败、宿主 provider 被跳过、字段缺失或总量截断时返回 `partial_success`；所有问题都写入 manifest，不会静默假装完整成功。

provider 返回 `null` 记录或其它非对象条目时，检索器会跳过坏条目、继续处理合法候选，并在 `manifest.json` / `search_log.json` 中记录 `empty_records`、`invalid_records` 和对应 warning。若所有返回条目均无法规范化，则返回 `failed`，`failure_code` 为 `no_valid_candidates`。

OpenAlex 候选缺少嵌套来源元数据（例如 `primary_location.source` 为 `null`）时，检索器保留候选并将 `venue` 规范化为 `null`；候选的 `quality_warnings` 会记录 `missing_venue`，不会因此中断整个 bundle。

## 依赖

Python 3.10+；联网 provider 使用 `requests`。MCP/duckduckgo 需要宿主工具，纯 Python runner 会显式记录 skipped。详见 [paper-schema.md](references/paper-schema.md)、[bundle-schema.md](references/bundle-schema.md) 和 [provider-guide.md](references/provider-guide.md)。
