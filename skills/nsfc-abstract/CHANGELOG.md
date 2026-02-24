# Changelog

All notable changes to the nsfc-abstract skill will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.3.1] - 2026-02-24

### Changed

- `SKILL.md`：标题建议输出格式新增英文版；推荐标题下方增加 `Recommended Title: ...` 行，每个候选条目末尾附 `/ EN: ...` 英文翻译
- `examples/demo_output.txt`：更新示例以对应新格式（含英文推荐标题与候选英文翻译）

## [0.3.0] - 2026-02-11

### Added

- 标题建议输出：默认 1 个推荐标题 + 5 个候选标题及理由（以 `config.yaml:title.*` 为准）
- 标题写作规则沉淀：新增 `references/title-rules.md`（基于 2016–2023 立项题目统计总结）
- `validate_abstract.py`：新增标题建议分段校验（可用 `--no-title` 向后兼容旧输出）
- `write_abstracts_md.py`：支持写入 `# 标题建议` 分段，并在标题不合格时拒绝写入

### Changed

- `config.yaml`：版本号升至 `0.3.0`，新增 `title.*` 配置项并默认要求标题建议分段
- `SKILL.md` / `README.md` / `scripts/README.md`：输出格式与脚本用法同步更新（加入标题建议）
- 回归测试：更新 stdlib unittest 用例以覆盖“标题建议必需 + 候选数量检查”

## [0.2.0] - 2026-02-03

### Added

- `validate_abstract.py`：新增 `--json`（机器可读输出）与 `--diff`（exceeded 差值）参数
- `write_abstracts_md.py`：新增 `--json` 输出与 `--auto-compress` 占位参数（当前仅提示，不执行自动压缩）
- `SKILL.md`：新增“字数超限处理（闭环，最多 3 轮）”章节，明确检测→压缩→再检测流程
- 新增 repo 级回归脚本与 fixtures：`tests/字数压缩/test_workflow.sh`、`tests/字数压缩/fixtures/*`

### Changed

- `write_abstracts_md.py`：`--strict` 模式下若超限则**不写入**输出文件（与 README 约定一致）

### Fixed

- `validate_abstract.py`：当缺失 `config.yaml` 时，默认返回完整的 limits/markers/headings/output 配置（避免返回值数量不一致）

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
