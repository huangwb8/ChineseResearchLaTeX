# research-literature-radar

论文发现与归档 Skill：把多渠道候选转成可审计、可持续维护的“核心证据 + 辅助景观 + 待升级近邻”研究雷达。

## 何时使用

当需要按主题寻找经典、rising star、社区精选、热点或顶会/顶刊论文时使用。关键词/数据库召回可交给 `research-literature-search`，本 Skill 负责分层发现、价值判断、分类、去重、归档与跟踪。

## 主要约束

- Search canonical 候选逐条进入 `literature-landscape.jsonl`，核心、辅助、待跟踪和范围外数量严格对账。
- 相关性、证据深度、发表状态与身份可信度分开记录；预印本和单一可靠来源不自动降级。
- 外部编号写入 `raw/metadata.json` 与 `catalog.jsonl` 的 `identifiers`，目录 ID 使用 `<首位作者全名>-<年份>-<工作关键词>`。
- 论文实体只写入 `docs/papers/<friendly-id>/raw/` 和同名学习笔记；运行产物统一放 `.bensz-api/research-literature-radar/`。

详细执行契约见 [`SKILL.md`](SKILL.md)。版本以 [`config.yaml`](config.yaml) 为准。
