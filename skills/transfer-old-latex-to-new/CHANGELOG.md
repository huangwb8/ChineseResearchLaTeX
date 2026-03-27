# Changelog

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)。

## [Unreleased]

### Changed

- 统一对外名称为 `transfer-old-latex-to-new`，README / 索引 / 示例命令同步保留 `migrating-latex-templates` 的兼容说明。
- 将版本号按 `SKILL.md` 同步回 `config.yaml`、`README.md` 与项目级索引，当前统一为 `v2.0.0`。

## [v2.0.0] - 2026-03-27

### Changed

- 将 skill 的主定位从“旧 NSFC 标书迁移到新模板目录”升级为“面向当前 ChineseResearchLaTeX 四条产品线的模板迁移与重构编排”。
- 重写 [SKILL.md](SKILL.md)：不再把 `old/new` 双目录、固定 `runs/` 输出和固定交付物作为主约束，改为强调 AI 自主托管输入解析、目标落层和输出形态。
- 重写 [README.md](README.md)：用户使用方式改为“给任意材料 + 给目标”，不再要求用户先整理成固定输入输出协议。
- 更新 [config.yaml](config.yaml)：版本跃迁到 `2.0.0`，并明确该配置主要服务 legacy CLI，而不是限定整个 skill 的输入输出边界。
- 更新 [scripts/README.md](scripts/README.md)：将 `run.py`、`migrate.sh` 等脚本降级为可选的 legacy CLI 后备说明。
