# Changelog

本文件遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)。

## [Unreleased]

### Changed（变更）

- `0.2.0`：新增证据 frontmatter 契约，要求稳定来源、证据深度、读取范围、问题/方法/结果/限制、支持/反驳关系和稳定引用；全文声明与摘要读取范围冲突时失败，旧笔记仅可显式兼容读取。
- `0.1.2`：将 OpenAI UI 展示元数据并入 `config.yaml:interface`，移除仅托管单个小配置的 `agents/openai.yaml` 目录，保持 Skill 触发语义不变。
- `0.1.1`：统一 Agent 展示名为 `Research Literature Interpretation`，与 Skill slug 和目录命名保持一致。
- 将项目论文库路径统一为 `docs/papers/`，同步更新笔记输出说明和脚本默认参数。
- 对齐 Agent Skills 开发规范：统一作者/版本元数据、OpenAI UI 元数据和设计缺陷上报边界。

## [0.1.0] - 2026-09-04

### Added

- 增加移动端短段落、职责化强调与单一正文渐进披露的写作规范。
- 增加集中式样式配置、写作指南和 `validate_notes.py --style` 检查。
- 增加同时覆盖入门读者与硬核读者的 ResNet 评估用例。

### Fixed

- 允许“我的解释/我的解读”作为知识层级同义标签。
- 拒绝相互矛盾的审核摘要，并避免误改相似的 frontmatter key。
- 样式检查覆盖长列表并忽略 fenced code；非法或非正数阈值提供明确错误。
- 多篇笔记晋级前先完成全量 frontmatter 预检，避免后置坏笔记造成前置笔记先被修改。

### Changed

- 重命名 skill：`research-paper-interpretation` → `research-literature-interpretation`，同步更新 SKILL.md 标识与交叉引用、脚本默认 catalog 路径（`.bensz-api/research-literature-radar/`）与 evals 名称；该新名称不保留旧名兼容。
- 压缩工作型 Markdown，在不改变触发、证据、安全和写作约束的前提下降低上下文体积。
