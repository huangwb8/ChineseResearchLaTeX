# Changelog

本文件遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)。

## [Unreleased]

### Changed（变更）

- `0.2.0`：新增覆盖全部 Search canonical 候选的 `literature-landscape.jsonl` 契约和 `build_landscape.py` 对账入口；正交记录核心/辅助/待跟踪/范围外角色、相关性、证据深度、发表状态与身份可信度，保留 Search record ID，并将额外来源核验限制在冲突、版本合并、疑似重复或决定性近邻。
- `0.1.1`：统一 Agent 展示名为 `Research Literature Radar`，与 Skill slug 和目录命名保持一致。
- 将正式论文库路径统一为 `docs/papers/`，同步更新目录契约、README 和脚本默认参数。
- 对齐 Agent Skills 开发规范：补齐作者/版本元数据、OpenAI UI 元数据、设计缺陷上报边界和用户文档。
- 重命名 skill：`research-paper-radar` → `research-literature-radar`，同步更新 SKILL.md 标识、交叉引用与 `.bensz-api/research-literature-radar/` 运行目录；该新名称不保留旧名兼容。

## [0.1.0] - 2026-09-04

### Added（新增）

- 建立分层论文发现、idea-level 评分、稳定 ID、去重和跨轮次归档工作流。
