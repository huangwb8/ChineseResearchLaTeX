# Changelog

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)。

## [0.1.3] - 2026-02-23

### Changed（变更）

- 将推荐库文件从 `nsfc_2026_recommend_overrides.toml` 重命名为 `nsfc_code_recommend.toml`，去除年份绑定，提升通用性
- 同步更新所有引用该文件名的文档与脚本（`SKILL.md`、`README.md`、`config.yaml`、`scripts/nsfc_code_rank.py`、`scripts/nsfc_code_new_report.py`、`scripts/validate_skill.py`、`references/demo/NSFC-CODE-v202602230900.md`）

## [0.1.2] - 2026-02-23

### Added（新增）

- 新增报告骨架生成脚本：`scripts/nsfc_code_new_report.py`（生成 `NSFC-CODE-vYYYYMMDDHHmm.md` 固定结构模板，降低手误）

### Changed（变更）

- `SKILL.md` / `README.md` / `scripts/validate_skill.py`：同步补充报告骨架脚本的用法与结构校验

## [0.1.1] - 2026-02-23

### Changed（变更）

- `scripts/nsfc_code_rank.py`：新增 `--prefix` 过滤候选代码首段前缀，降低跨学科噪声
- `SKILL.md` / `README.md` / `config.yaml`：同步补充 `--prefix` 的使用说明与参数口径

### Fixed（修复）

- `scripts/nsfc_code_rank.py`：目录输入时跳过 `NSFC-*` 报告与常见元文档，避免输出回灌污染候选粗排
- `scripts/nsfc_code_rank.py`：对 `recommend` 轻量去模板化，提高相似度区分度
- `scripts/nsfc_code_rank.py`：输入路径不存在时早失败并给出清晰错误提示

## [0.1.0] - 2026-02-23

### Added（新增）

- 新增 `nsfc-code` 技能骨架：只读读取标书正文，结合 2026 申请代码推荐库输出 5 组主/次代码推荐与理由
- 新增候选代码粗排脚本：`scripts/nsfc_code_rank.py`
