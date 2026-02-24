# Changelog

All notable changes to this skill will be documented in this file.

The version number is the single source of truth in `config.yaml` (`skill_info.version`).

## [Unreleased]

（暂无）

## [1.0.0] - 2026-02-24

### Changed
- `config.yaml`：版本号 `0.7.9 → 1.0.0`，标记为正式稳定版本

## [0.7.9] - 2026-02-22

### Added
- 第三方约束（瘦身提质）诊断预警：预估页数（经验估算）、核心文献数（去重 cite keys）、开篇 300 字信号检查（启发式）

### Changed
- 配置兜底字数调整为 9000±800，并新增 `constraints.*` 约束区间（页数/字数/文献数量/开篇长度）
- `test-session` 将 pytest/python 缓存隔离到会话目录，保证测试中间产物可追溯且集中收口

## [0.7.8] - 2026-02-17

### Added
- 科学问题与科学假设写作要点参考文档（用于“瓶颈→约束→问题→假设”的闭环自检）

### Changed
- 信息表与写作教练：强化“科学问题≠研究目标”“假设不写验证方式”“瓶颈→约束映射”提示
- 信息表生成标题去年份化（避免时间敏感硬编码）
