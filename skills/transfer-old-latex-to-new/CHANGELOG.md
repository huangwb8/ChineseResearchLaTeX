# Changelog

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)。

## [Unreleased]

### Fixed

- 修复 `scripts/validate_config.py` 默认读取 `config.yaml` 的路径错误：`python scripts/validate_config.py` 现在会正确指向 skill 根目录配置，不再误读 `scripts/config.yaml` 并开箱失败。
- 修复 `tests/test_smoke.py` 在 pytest 环境下返回布尔值导致的 `PytestReturnNotNoneWarning`：现改为纯断言式测试，`pytest skills/transfer-old-latex-to-new/tests -q` 恢复为无 warning 通过。

### Changed

- 统一对外名称为 `transfer-old-latex-to-new`，README / 索引 / 示例命令同步保留 `migrating-latex-templates` 的兼容说明。
- 将版本号按 `SKILL.md` 同步回 `config.yaml`、`README.md` 与项目级索引，当前统一为 `v2.0.0`。
- 优化 legacy CLI 与配置校验链路：`scripts/run.py` 现在明确标注为 `ChineseResearchLaTeX` 模板迁移 legacy CLI，并为 `analyze/apply/compile/restore` 正式接入 `--profile`；`scripts/validate_config.py` 也新增未知 profile 拦截与 `skill_info.version` / `metadata.skill_version` 一致性校验。
- 收紧 skill 内部口径：`config.yaml` 为 legacy NSFC 增强节点补充作用域说明，`scripts/README.md` 与 `scripts/core/README.md` 明确区分主 workflow、legacy CLI 与 NSFC 倾向模块。
- 新增 auto-test 优化记录：补充 `plans/v202603280647.md`、`tests/v202603280647/`、`plans/B轮-v202603280653.md` 与 `tests/B轮-v202603280653/`，沉淀本次 A 轮 / B 轮审查与验证证据。

## [v2.0.0] - 2026-03-27

### Changed

- 将 skill 的主定位从“旧 NSFC 标书迁移到新模板目录”升级为“面向当前 ChineseResearchLaTeX 四条产品线的模板迁移与重构编排”。
- 重写 [SKILL.md](SKILL.md)：不再把 `old/new` 双目录、固定 `runs/` 输出和固定交付物作为主约束，改为强调 AI 自主托管输入解析、目标落层和输出形态。
- 重写 [README.md](README.md)：用户使用方式改为“给任意材料 + 给目标”，不再要求用户先整理成固定输入输出协议。
- 更新 [config.yaml](config.yaml)：版本跃迁到 `2.0.0`，并明确该配置主要服务 legacy CLI，而不是限定整个 skill 的输入输出边界。
- 更新 [scripts/README.md](scripts/README.md)：将 `run.py`、`migrate.sh` 等脚本降级为可选的 legacy CLI 后备说明。
