# Changelog

## [Unreleased]

- 明确恢复拆分前 review 的 priority-fallback-topup 检索语义，并在 manifest/Search Log 固化策略与补召阈值，避免将 fallback 误读为全 provider union 召回。

## [1.0.3] - 2026-09-14

### Fixed

- OpenAlex 合法候选的 `primary_location.source` 为 `null` 时不再中断规范化；缺失 venue 保留为 `null` 并附加质量 warning。
- 增加嵌套 source 空值的回归覆盖，确保其余合法候选仍可生成并通过校验的 manifest bundle。

## [1.0.2] - 2026-09-02

### Fixed

- 将 manifest contract 常量移至唯一命名的 `rls_contract.py`，修复 review runner 进程内导入同名 `query_contract` 导致合法 bundle 无法验证的问题。

## [1.0.1] - 2026-09-02

### Fixed

- provider 返回 `null` 或混入非对象候选时，统一在输入边界跳过无效条目，避免规范化阶段因 `.get()` 崩溃。
- manifest、Search Log 和 dedupe map 记录跳过的空/非法条目数量；全部候选无效时返回 `no_valid_candidates`。
- 增加空记录、混合非法记录和全空 provider 结果的回归测试。

## [1.0.0] - 2026-09-02

### Added

- 新增独立 `research-literature-search` Skill 与 `rls.v1` manifest/candidate 契约。
- 提供 `run`、`enrich-abstracts`、`validate` 稳定命令。
- 支持 OpenAlex 主力、Semantic Scholar/Crossref 补充，以及 MCP/duckduckgo 显式 skipped 审计。
- 输出 raw、normalized、deduped、provenance、dedupe map 和兼容 Search Log。

### Fixed

- 对输出 scope 越界、非法 provider 返回值和不安全错误文本执行 fail-closed 处理，并补充 provider policy 指纹与语言/开放获取过滤。
- 去重合并保留两侧 identifiers；摘要补全成功时不再错误追加 `missing_abstract` 警告；bundle validator 严格校验 artifact hash、字节数和查询计数。
