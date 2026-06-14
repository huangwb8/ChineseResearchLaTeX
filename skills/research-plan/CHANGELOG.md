# Research Plan 变更日志

本文档记录 research-plan skill 的所有重要变更。历史记录中的 make-research-plan 为旧名。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)。

## [Unreleased]

### Added
- 新增 `make-research-plan/references/output-templates.md`：存放 `analysis-framework.md` 与 `plan.md` 输出模板，避免在 `SKILL.md` 内堆叠长模板
- 新增 `make-research-plan/references/implementation-notes.md`：记录脚本实现状态与“硬编码/AI 动态处理”边界（维护者视角）

### Changed
- `make-research-plan/SKILL.md` 瘦身以满足社区推荐的 500 行以内约束：将长模板与实现备注下沉到 `references/`，并在 `SKILL.md` 中保留入口
- 简化 config.yaml，移除未实现功能的配置项（YAGNI 原则）
- 保留 skill_info 和基础工作目录配置
- 预留 apis、pdf_download、analysis_extraction 配置，待功能实现后添加

### Fixed
- **安全性**：修复 initialize.py 的路径验证漏洞，添加符号链接攻击防护
- 验证解析后的路径是否在允许范围内（使用 Path.relative_to）

## [0.2.0] - 2026-06-14

### Changed

- Skill 正式名从 `make-research-plan` 迁移为 `research-plan`。
- `SKILL.md` 与 `README.md` 保留旧名 prompt 兼容说明；系统级旧目录交由 `install-bensz-skills` 清理。
- 历史工作区 `.make-research-plan/` 保持不变，避免破坏已有输出和脚本契约。

## [0.1.0] - 2026-01-19

### Added
- 初始版本发布
- 实现核心功能框架：
  - 工作目录初始化
  - 主题提取与文献调研流程设计
  - PDF 信息提取流程设计
  - 分析框架总结流程设计
  - 个性化计划生成流程设计
- 内化文献调研逻辑（不再依赖 systematic-literature-review）
- 提供 JSON Schema 验证
- 提供 BibTeX 格式化输出
- 创建辅助文档和参考指南

### Planned（计划中）
- 实现自动化文献检索 API 集成
- 实现 PDF 自动下载功能
- 实现方法学信息自动提取
- 添加更多数据源支持
- 实现计划模板系统
- 添加交互式计划审查流程

---

## 变更类型说明

- **Added**: 新增功能
- **Changed**: 功能变更
- **Deprecated**: 即将废弃的功能
- **Removed**: 已删除的功能
- **Fixed**: 问题修复
- **Security**: 安全性改进
