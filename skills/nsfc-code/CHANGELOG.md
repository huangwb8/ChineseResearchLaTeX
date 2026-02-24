# Changelog

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)。

## [1.0.0] - 2026-02-24

### Changed（变更）

- `config.yaml`：版本号 `0.1.6 → 1.0.0`，标记为正式稳定版本

## [0.1.6] - 2026-02-23

### Fixed（修复）

- `SKILL.md`：修复 shell 代码块的弯引号（可复制可执行）；`nsfc_code_new_report.py` 示例命令补齐 `--ts "${TS}"`，避免时间戳不一致导致 `cp` 找不到文件
- `scripts/nsfc_code_rank.py`：新增 `--output-dir`（与 `SKILL.md` 示例对齐），并跳过 `.nsfc-code/` 目录，避免工作区回灌污染粗排

### Changed（变更）

- `scripts/nsfc_code_rank.py`：优先使用标准库 `tomllib`（Python 3.11+）解析 TOML（不可用时回退到最小解析器），提升对推荐库格式变化的鲁棒性
- `scripts/validate_skill.py`：smoke 校验改为 JSON 结构解析，并覆盖 `--output-dir` 行为（生成文件 + JSON 可解析）

## [0.1.5] - 2026-02-23

### Changed（变更）

- `SKILL.md`：引入隐藏工作区机制——每次运行在工作目录下创建 `.nsfc-code/v{ts}/` 子目录，所有中间文件（粗排结果、调试日志等）隔离写入该子目录；工作目录根层只保留最终交付文件 `NSFC-CODE-v{ts}.md`
- `SKILL.md`：执行流程新增"步骤 1：确定时间戳与工作区"，脚本命令同步增加 `--output-dir` 参数
- `config.yaml`：`allowed_write_globs` 新增 `.nsfc-code/**`；`output_contract` 新增 `work_dir` 字段；版本升至 `0.1.5`

## [0.1.4] - 2026-02-23

### Changed（变更）

- `SKILL.md`：在"硬性约束"中新增"唯一交付文件"条款，明确禁止在用户工作目录创建任何中间文件/临时文件，脚本产物只能写入 `skills/nsfc-code/` 内部或内存

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
