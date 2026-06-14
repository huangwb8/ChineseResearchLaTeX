# Research Idea 变更日志

本文档记录 research-idea skill 的所有重要变更。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)。

## [Unreleased]

### Changed

- 依赖口径迁移为 `research-topic-extractor` 与 `research-literature-review`。
- 依赖检查脚本增加旧名 fallback：`get-review-theme`、`systematic-literature-review`。
- README 与 SKILL 文档同步更新相邻 skill 边界说明。

## [0.1.0] - 2026-06-14

### Added

- 初始化 `research-idea` skill：根据用户资料提出多个关键科学问题与可证伪科学假设。
- 新增隐藏工作区规范：默认 `.research-idea/run-{timestamp}/` 保存全部中间文件，最终报告不泄露中间路径。
- 新增依赖协作流程：使用 `get-review-theme` 提取查新主题，使用 `systematic-literature-review` Premium 档查新，使用 `parallel-vibe` 默认 3 轮串行独立审查。
- 新增 `scripts/init_workspace.py`：初始化隐藏工作区、测试区、运行清单和默认输出路径。
- 新增 `scripts/validate_report.py`：验证最终 Markdown 文件名、必需章节、问题-假设对数量、可证伪表述和中间路径泄露。
- 新增 `scripts/check_dependencies.py`：检查 `get-review-theme`、`systematic-literature-review` 与 `parallel-vibe` 是否可发现，依赖缺失时早失败。
- 新增 `references/report-template.md`、`references/novelty-check.md` 与 `references/agent-review-prompt.md`，分别规范最终报告、查新判定和独立审查输入。
- 新增 `README.md` 与 `config.yaml`：提供用户使用指南、WHICHMODEL 初始建议、默认目录、依赖、轮次、输出和校验规则。

### Changed

- 强化默认 3 轮口径：明确 `rounds=3` 为外层迭代轮数，每轮使用 `parallel-vibe --n 3` 进行独立审查。
- 强化最终报告校验：要求至少 3 个候选、每个候选包含关键预测/反证路径/查新结论，查新摘要必须说明 Premium 档，最佳方案必须包含多维选择理由。
- 收紧中间文件隔离：`parallel-vibe`、查新产物、manifest、agent review 和草稿均限定在隐藏工作区内，最终报告不得泄露内部路径。
- 使用 `compact-bensz-skills` 压缩工作型 Markdown：`SKILL.md` 从 188 行降至 165 行，工作型 Markdown 总词数减少 302，压缩校验 0 error / 0 warning。
