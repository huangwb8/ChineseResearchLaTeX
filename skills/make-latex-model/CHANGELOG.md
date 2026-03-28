# Changelog

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)。

## [Unreleased]

### Added（新增）

- 新增 `scripts/plan_package_regression.py`：可按 `config.yaml` 的公共包回归规则输出受影响项目、官方 build 命令，以及在可用时附带 compare 建议，作为修改 `packages/bensz-*` 前的确定性安全门禁。
- 新增 `references/SCRIPT_SCOPE.md`：按“跨产品线辅助脚本 / NSFC 专项工具”重新整理脚本职责矩阵，不再用 legacy 叙事描述当前 skill 的能力边界。

### Changed（变更）

- 将 `make-latex-model` 升级到 `v3.1.1`，把 `SKILL.md`、`README.md`、`docs/WORKFLOW.md`、`docs/FAQ.md`、`docs/BASELINE_GUIDE.md`、`scripts/README.md` 与根级索引里的历史过渡口径改写为“当前状态直述”：`validate.sh`、`optimize.py`、`templates/nsfc/*.yaml` 等脚本统一定义为 NSFC 专项工具，而不是把当前 skill 表述成旧版 NSFC 流程的改良或继承。
- 将 `make-latex-model` 升级到 `v3.1.2`：删除 `templates/nsfc/*.yaml` 这层按年度固化 NSFC 标题文字的模板设计，改为由 `scripts/core/template_catalog.py` 提供稳定结构默认值；`config_loader.py`、`extract_headings.py`、`setup_wizard.py` 与相关 README/索引同步去除对这些 YAML 的硬依赖，项目级 `.template.yaml` 仍可保留局部覆盖能力。

### Fixed（修复）

- 修复 `scripts/check_state.py` 仍把所有项目都按 `NSFC + extraTex/@config.tex` 初始化的误判问题：现改为从 `config.yaml` 的 `product_line_rules` 读取产品线识别、初始化标记与官方构建命令，`paper / thesis / cv` 不再被错误标记为“未初始化”。
- 修复基线与建议文案过度绑定基金委/`word.pdf` 的问题：`config.yaml` 新增 `baseline.preferred_candidates` 与 `analysis_command` 作为单一真相来源，状态检查输出改为通用 PDF 基线口径，同时继续兼容 legacy `word.pdf`。

### Changed（变更）

- 统一对外名称为 `make-latex-model`，README / 索引 / 示例命令同步保留对旧写法 `make_latex_model` 的兼容提示。
- 将版本号按 `SKILL.md` 同步回 `config.yaml`、`README.md` 与项目级索引，当前统一为 `v3.0.1`。
- 将产品线判定与脚本边界从 `SKILL.md` 下沉到 `references/PRODUCT_LINE_RULES.md` 与后续统一收口的脚本职责文档，减少核心工作文档冗余，并把当前版本提升为 `v3.0.1`。

## [3.0.0] - 2026-03-27

### Added（新增）

- 新增面向 `NSFC / paper / thesis / cv` 四条产品线的分层判定与官方验证矩阵。
- 新增 Skill 级 `CHANGELOG.md`，把 `make-latex-model` 的版本演进落到技能目录内维护。

### Changed（变更）

- 将 `make-latex-model` 从“NSFC 专用 `@config.tex` 微调器”重定位为“ChineseResearchLaTeX 模板落地与高保真对齐 skill”。
- `SKILL.md`、`README.md`、`docs/WORKFLOW.md`、`docs/FAQ.md` 全面改为基于当前 `packages/ + projects/ + 官方构建脚本` 的真实架构。
- `config.yaml` 升级到 `3.0.0`，增加 `product_line`、`target_scope`、`baseline_pdf`、`acceptance_mode` 等面向当前仓库的参数语义。
- `scripts/README.md` 明确辅助脚本为“可选工具箱”，并将旧版 NSFC 专用脚本降级为 legacy 入口。
