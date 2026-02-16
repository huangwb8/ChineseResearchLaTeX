# 变更记录

## [0.1.1] - 2026-02-16

### Added
- 新增只读自检脚本：`scripts/validate_skill.py`、`scripts/check_project_outputs.py`、`scripts/run_checks.py`

### Changed
- 强化 SKILL.md 的写入安全约束与参数说明，降低误改 LaTeX 结构风险
- 信息表与文档表述去年份化，提升通用性
- README 增加 `output_mode` 用法与可选自检入口

## [0.1.0] - 2026-01-14

### Added
- 初始版本发布
- 支持为 NSFC 标书正文"（三）研究基础"写作/重构
- 支持同步编排"工作条件"和"研究风险应对"
- 支持证据链验证、可行性四维分析、风险预案生成

### Changed
- 增强 SKILL.md 工作流步骤的详细指导
- 增加 config.yaml 的注释说明
- 增强 README.md 的用户引导

### Fixed
- 修复 quality_contract 配置未在工作流中引用的问题
- 修复工作流步骤缺少路径验证说明的问题
- 修复边缘情况处理说明缺失的问题
