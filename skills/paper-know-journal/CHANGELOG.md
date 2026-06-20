# 变更日志

本文件记录 paper-know-journal 技能的重要变更。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

## [Unreleased]

## [0.3.0] - 2026-06-01

### Added（新增）
- 新增“目标文体/文章类型具体要求”报告小节，要求按用户指定或默认选择的 Article、Review、Brief Communication 等文体展开官方章节标题/顺序、字数/页数、摘要、关键词、图表、补充材料、参考文献和特殊文件要求。
- 验证脚本新增目标文体小节与具体要点覆盖检查，避免报告只停留在通用投稿格式清单。

### Changed（变更）
- 强化 `SKILL.md`、README、来源策略和报告模板：未指定文体时需先说明选择展开的官方文章类型；官方未披露具体限制时逐项标注“未在官方页面确认”。
- 将技能版本号从 `0.2.0` 升级到 `0.3.0`。

## [0.2.0] - 2026-06-01

### Added（新增）
- 新增“投稿形式要求与格式清单”作为报告必填章节，要求独立整理标题页、摘要/关键词、正文结构、图表、补充材料、参考文献、声明、投稿文件和 cover letter 等投稿前可执行格式要求。
- 新增轻量测试记录 `tests/v202606012048/`，覆盖旧实例拦截与新格式清单正向通过。

### Changed（变更）
- 强化 `SKILL.md`、README、来源策略和报告模板：明确近期文章样本不能替代官方投稿格式要求，官方未披露的格式项需逐项标注待确认。
- 将技能版本号从 `0.1.3` 升级到 `0.2.0`。

### Fixed（修复）
- 修复报告容易停留在期刊概览和社区评价、缺少实际投稿格式准备信息的问题。

## [0.1.3] - 2026-06-01

### Changed（变更）
- 使用 `compact-bensz-skills` 压缩工作型 Markdown，仅精简 `SKILL.md` 与 `references/source-policy.md` 的重复表达，保留触发语义、路径约束、来源策略、验证命令和失败处理。

## [0.1.2] - 2026-06-01

### Changed（变更）
- `scripts/init_workspace.py` 增加 `output_exists` 记录与覆盖提醒，并把 `sources.json` 的 schema 提示改为中文结构。
- `scripts/validate_report.py` 支持从配置读取官方/社区来源表类型，并允许在“未找到足够社区评价”时通过显式缺口说明替代社区来源行。
- `SKILL.md` 补充最终报告覆盖前确认要求。
- README 与报告模板补充来源索引和来源表类型示例。

### Fixed（修复）
- 修复配置加载使用浅拷贝导致默认嵌套配置可能被意外污染的问题。
- 修复社区评价稀少场景下验证器可能迫使执行者编造社区来源的问题。

## [0.1.1] - 2026-06-01

### Changed（变更）
- `scripts/init_workspace.py` 改为读取 `config.yaml` 中的隐藏工作区、测试区、输出文件名、运行 ID 和子目录配置，降低配置漂移风险。
- `scripts/validate_report.py` 改为读取 `config.yaml` 中的必需章节与验证阈值，并增强来源分离、访问日期、来源可信度表和中间路径泄露检查。
- `SKILL.md` 明确要求维护 `sources.json`，记录官方来源、社区来源和近期文章样本。
- README 与报告模板补充官方/社区来源分离和待确认信息位置。

### Fixed（修复）
- 修复报告验证器过宽的问题：缺少社区/官方来源标记、访问日期或来源可信度表时会失败。
- 修复最终报告中 `.paper-know-journal` 裸目录名或反斜杠路径可能漏检的问题。
- 修复初始化脚本中路径、子目录和输出模板硬编码的问题。

## [0.1.0] - 2026-06-01

### Added（新增）
- 初始化 `paper-know-journal` skill：支持按期刊名联网调研官方投稿要求、社区评价和近期文章格式。
- 新增默认隐藏工作区 `.paper-know-journal/run-<timestamp>/`，要求所有中间文件隔离保存。
- 新增最终输出约定：`KnowJournal-{杂志名}.md`，默认保存在用户工作目录根目录。
- 新增 `scripts/init_workspace.py`，用于创建运行目录、测试区、manifest 和安全输出路径。
- 新增 `scripts/validate_report.py`，用于检查最终报告结构、来源链接数量和中间路径泄露。
- 新增 `references/source-policy.md` 与 `references/report-template.md`，沉淀来源分级和报告模板。
