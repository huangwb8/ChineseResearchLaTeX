# Changelog

All notable changes to the nsfc-abstract skill will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.1] - 2026-02-03

### Added

- 输出写入工作目录 `NSFC-ABSTRACTS.md`（中文/英文各一个 `#` 标题）
- 新增写入脚本：`skills/nsfc-abstract/scripts/write_abstracts_md.py`
- 新增回归测试：`skills/nsfc-abstract/tests/test_validate_abstract.py`、`skills/nsfc-abstract/tests/test_write_abstracts_md.py`（stdlib unittest）
- 新增脚本文档：`skills/nsfc-abstract/scripts/README.md`

### Changed

- 收窄 `SKILL.md` 的 triggers，避免过宽的“摘要”导致误触发
- README 补充内置 demo 文件提示，便于验证输出格式与长度校验脚本

### Fixed

- `validate_abstract.py`：兼容 `config.yaml` 中字符串标量带引号/不带引号两种写法（避免 `#` 被误判为注释）
- `validate_abstract.py`：支持两种输入格式校验（`[ZH]/[EN]` 标记或 `# 中文摘要/# English Abstract` 标题）
- `validate_abstract.py`：缺失分段标记时给出可操作的最小修复示例，并在 `--help` 中明确退出码
- `validate_abstract.py`：长度计数前折叠连续空白，减少换行/多空格导致的意外超限；输出中显示 limits/markers/raw count 便于复现
- `validate_abstract.py`：避免使用 Python 3.10+ 专用类型注解语法（提高脚本可移植性）

## [0.1.0] - 2026-02-03

### Added

- 初始版本：生成 NSFC 中文摘要（≤400字，含标点）与对应英文摘要（≤4000字符，含标点；英文为中文的忠实翻译）
- 提供长度校验脚本：`skills/nsfc-abstract/scripts/validate_abstract.py`
