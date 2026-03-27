# Changelog

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)。

## [Unreleased]

### Changed（变更）

- 统一对外名称为 `make-latex-model`，README / 索引 / 示例命令同步保留对旧写法 `make_latex_model` 的兼容提示。
- 将版本号按 `SKILL.md` 同步回 `config.yaml`、`README.md` 与项目级索引，当前统一为 `v3.0.0`。

## [3.0.0] - 2026-03-27

### Added（新增）

- 新增面向 `NSFC / paper / thesis / cv` 四条产品线的分层判定与官方验证矩阵。
- 新增 Skill 级 `CHANGELOG.md`，把 `make-latex-model` 的版本演进落到技能目录内维护。

### Changed（变更）

- 将 `make-latex-model` 从“NSFC 专用 `@config.tex` 微调器”重定位为“ChineseResearchLaTeX 模板落地与高保真对齐 skill”。
- `SKILL.md`、`README.md`、`docs/WORKFLOW.md`、`docs/FAQ.md` 全面改为基于当前 `packages/ + projects/ + 官方构建脚本` 的真实架构。
- `config.yaml` 升级到 `3.0.0`，增加 `product_line`、`target_scope`、`baseline_pdf`、`acceptance_mode` 等面向当前仓库的参数语义。
- `scripts/README.md` 明确辅助脚本为“可选工具箱”，并将旧版 NSFC 专用脚本降级为 legacy 入口。
