# nsfc-reviewers - 变更日志

格式遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)。

## [Unreleased]

## [1.0.0] - 2026-02-24

### Changed（变更）

- `config.yaml`：版本号 `0.5.0 → 1.0.0`，标记为正式稳定版本

## [0.5.0] - 2026-02-14

### Added（新增）

- 新增 `scripts/finalize_output.py`：将“输出整理”确定性脚本化（支持 DRY-RUN / `--apply`），自动创建 `.nsfc-reviewers/` 目录结构、归档 `master_prompt.txt` 与 `plan*.json`、并将 legacy `.parallel_vibe/` 运行环境迁移到 `.nsfc-reviewers/parallel-vibe/`，提高并行评审可追溯性。
- 新增轻量测试会话 `tests/并行硬编码-优化-v202602142238/`：覆盖并行/串行两种整理路径的最小可复现验证。

### Changed（变更）

- `SKILL.md`：将“阶段五：输出整理”升级为**强制执行**，并补齐“并行/串行模式”前置判断、脚本推荐用法与验证清单，降低 AI 跳过整理步骤的概率。
- `config.yaml`：`output_settings` 新增输出整理校验开关（`enforce_output_finalization` / `warn_missing_intermediate` / `validation_level`）；版本号 `0.4.1 → 0.5.0`。
- `README.md`：新增输出整理脚本使用说明，明确中间目录的归档内容与触发时机。

## [0.4.1] - 2026-02-14

### Added（新增）

- 新增 `scripts/list_proposal_files.py`：确定性递归发现待评审 `.tex` 文件，并默认跳过 `panels/`、`.nsfc-reviewers/`、`.parallel_vibe/` 等中间/交付目录，降低误扫与递归污染风险。
- 新增轻量测试会话 `tests/v202602140830/` 与 `tests/B轮-v202602140830/`：覆盖文件发现脚本、路径安全门禁与会话结构自检（PLAN/REPORT + artifacts）。

### Fixed（修复）

- `config.yaml`：不再默认排除 `main.tex`，避免目录模式下误判“无 .tex 文件”导致阻塞；版本号 `0.4.0 → 0.4.1`。
- `scripts/cleanup_intermediate.py`：对 `--intermediate-dir` 增加 fail-fast 校验（相对路径、无 `..`、不含斜杠）。
- `scripts/validate_skill.py`：新增对 `output_settings.panel_dir/intermediate_dir` 的路径安全校验，并纳入 `list_proposal_files.py` 存在性检查。

### Changed（变更）

- `SKILL.md`：阶段一补充确定性文件发现命令；并行阶段补齐中间目录预创建与快照提示，减少执行漂移。
- 清理仓库内残留 `.DS_Store` 文件，减少无意义 diff 噪声。

## [0.4.0] - 2026-02-14

### Added（新增）

- 新增“输出整理”阶段：将最终交付（聚合报告 + `panels/`）与中间过程（并行环境/日志/快照）显式隔离到 `config.yaml:output_settings.intermediate_dir`。
- 新增 `scripts/cleanup_intermediate.py`：清理 `.nsfc-reviewers/` 中的并行运行环境与过期日志（默认 DRY-RUN，`--apply` 才执行删除）。
- 新增轻量测试会话 `tests/实例辅助优化-v202602140804/`（`PLAN.md`、`REPORT.md` 与 `_artifacts/`）。

### Changed（变更）

- `config.yaml`：新增 `output_settings.panel_dir/hide_intermediate/intermediate_dir` 与 `maintenance.cleanup`；版本号 `0.3.1 → 0.4.0`。
- `SKILL.md`：并行模式默认将 `.parallel_vibe` 落到中间目录并给出输出整理与迁移口径（兼容旧实例）。
- `README.md`：补充“最终交付 vs 中间过程”目录结构与清理脚本用法说明。

## [0.3.1] - 2026-02-13

### Added（新增）

- 新增 `scripts/build_parallel_vibe_plan.py`：为并行多组评审生成 `parallel-vibe --plan-file` 所需的 `plan.json`（禁用 synth，避免额外消耗）。

### Changed（变更）

- `SKILL.md`：并行模式改为使用 `parallel-vibe --plan-file` + `--src-dir/--out-dir`（适配 `parallel-vibe` 新工作流），并明确 thread 输出位于 `workspace/`。
- `references/master_prompt_template.md`：输出文件名改为 `{panel_output_filename}` 占位符，避免与 `config.yaml` 重复硬编码。
- `config.yaml`：新增 `parallel_review.runner_profile`，用于计划文件中的 `runner.profile`；版本号 `0.3.0 → 0.3.1`。
- `README.md`：补充并行模式与 `parallel-vibe --plan-file` 的关系说明。
- `scripts/validate_skill.py`：增强校验（要求 `--plan-file` 工作流、禁止旧 `--runner` 旗标、校验模板占位符存在）。

## [0.3.0] - 2026-02-10

### Added（新增）

- 支持“多组独立评审委员会并行评审”：每组固定 5 位专家，组内聚合后再跨组聚合输出。
- 新增 `references/`：专家画像、master prompt 模板与跨组聚合规则从配置中分离为可维护的 Markdown 文件。
- 新增轻量测试会话 `tests/独立专家-v202602110611/`（`PLAN.md`、`REPORT.md` 与 `_artifacts/`）。

### Changed（变更）

- `config.yaml`：并行参数从 `reviewer_count` 语义升级为 `panel_count`（组数），并通过 `prompt_file` 引用 `references/` 模板；版本号 `0.2.0 → 0.3.0`。
- `SKILL.md`：工作流从“每 thread 一个专家”改为“每 thread 一组专家（5 位）”，并补齐跨组共识聚合口径。
- `README.md`：更新为多组评审模式用户指南，补充成本说明与输出解读。
- `scripts/validate_skill.py`：增加对 `references/` 与新配置结构的校验，防止 prompt 回流到 `config.yaml`。

### Removed（移除）

- 移除 `config.yaml` 中内联保存的专家 prompt 文本（原 `style` 字段）。

## [0.2.0] - 2026-02-10

### Added（新增）

- 新增并行独立评审能力：支持多位虚拟专家并行评审后聚合输出。
- `config.yaml` 新增 `parallel_review` 配置节：并行开关、专家数、专家画像、聚合规则。
- `SKILL.md` 新增 `reviewer_count` 输入参数与并行报告结构规范。
- `SKILL.md` 新增对 `parallel-vibe` 的依赖说明及脚本路径发现顺序。
- 新增轻量测试会话 `tests/v202602101947/`（`TEST_PLAN.md`、`TEST_REPORT.md` 与 `_artifacts/`）。

### Changed（变更）

- `SKILL.md` 阶段三重构为“并行优先 + 串行退化”双路径，阶段四改为共识聚合流程。
- `README.md` 更新为并行模式用户指南，补充并行触发示例、退化机制和参数说明。
- `config.yaml` 版本号从 `0.1.1` 升级到 `0.2.0`（向下兼容的功能性新增）。

## [0.1.1] - 2026-02-10

### Added（新增）

- 新增 `CHANGELOG.md`，用于记录技能级变更（版本号以 `config.yaml:skill_info.version` 为单一真相来源）。
- 新增 `scripts/validate_skill.py`：面向维护者的轻量一致性自检（frontmatter/config/通用性约束）。

### Changed（变更）

- 重写 `SKILL.md`：增加“非官方声明”“安全与隐私”“输入契约/Fail Fast”“证据锚点硬门槛”，并要求以 `config.yaml` 作为执行时的清单来源。
- 更新 `README.md`：移除具体日期与疑似真实示例内容，补充隐私提示，并将“评审等级/资助建议”明确为可选输出。
- `README.md`：新增“维护者自检”指引（`python3 scripts/validate_skill.py`）。

### Fixed（修复）

- 修复“遵循/官方评审标准”这类可能造成权威背书错觉的表述，统一改为经验性改进清单口径。

## [0.1.0] - 2026-02-10

### Added（新增）

- 初始化技能：提供 NSFC 标书多维度评审流程、问题分级与默认输出约定。
