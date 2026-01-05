# Changelog

本文件记录项目的修改历史，方便回顾项目的优化过程。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)。

---

## [Unreleased]

### Changed（变更）

- 更新 `AGENTS.md` 与 `CLAUDE.md` 的目录结构示例，使 `skills/` 示例与当前仓库实际技能（`make_latex_model`）一致
- **make_latex_model**：融入 `analyze_pdf.py` 工具到工作流
  - 在 `SKILL.md` 步骤 2 中新增 "2.2 自动提取样式参数" 小节
  - 在 `scripts/README.md` 中新增 `analyze_pdf.py` 工具文档（作为工具 #1）
  - 优化 `analyze_pdf.py`：添加依赖检查、文件验证、改进输出格式
  - 调整工具编号：`validate.sh` (#2)、`benchmark.sh` (#3)、`extract_headings.py` (#4)、`compare_headings.py` (#5)

### Added（新增）- Skills

- **make_latex_model v2.0.0** - 通用化重构
  - **核心架构重构**：实现配置与代码分离，支持任意 LaTeX 模板
  - **分层配置系统**：
    - `config.yaml`：技能默认配置
    - `templates/`：模板配置目录（支持继承）
    - `.template.yaml`：项目本地配置
  - **新增核心模块**：
    - `core/config_loader.py`：配置加载器（支持三层合并和继承）
    - `core/template_base.py`：模板基类
    - `core/validator_base.py`：验证器基类
  - **模板配置**：
    - `templates/nsfc/base.yaml`：NSFC 基础模板
    - `templates/nsfc/young.yaml`：青年基金模板
    - `templates/nsfc/general.yaml`：面上项目模板
    - `templates/nsfc/local.yaml`：地区基金模板
  - **工具脚本重构**（支持命令行参数）：
    - `validate.sh --project PATH [--template NAME]`
    - `extract_headings.py --file PATH [--project PATH] [--config PATH]`
  - **向后兼容**：现有 NSFC 项目无需修改即可继续使用
  - **测试覆盖**：新增向后兼容性测试 `tests/test_backward_compat.py`

- **make_latex_model v1.4.0** - 标题文字对齐功能
  - 新增自动化工具：
    - `scripts/extract_headings.py`：从 Word/LaTeX 提取标题文字
    - `scripts/compare_headings.py`：对比标题文字差异，生成 HTML 可视化报告
  - 修订核心目标：明确"标题文字对齐"与"样式参数对齐"的双重目标
  - 修订绝对禁区：允许修改 `main.tex` 中的标题文本，禁止修改正文内容
  - 集成到 `validate.sh`：自动检查标题文字一致性
  - 解决问题：修复了对"样式对齐"的理解偏差，现在同时关注样式参数和标题文字分布

## [1.0.0] - 2026-01-05

### Added（新增）

- 初始化 AI 项目指令文件
- 生成 `CLAUDE.md`（Claude Code 项目指令）
- 生成 `AGENTS.md`（OpenAI Codex CLI 项目指令）
- 配置项目工程原则和工作流

### Changed（变更）

### Fixed（修复）

---

## 记录规范

每次修改 `CLAUDE.md` 或 `AGENTS.md` 时，请按以下格式追加记录：

```markdown
## [版本号] - YYYY-MM-DD

### Changed（变更）
- 修改了 XXX 章节：原因是 YYY，具体变更内容是 ZZZ

### Added（新增）
- 新增了 XXX 功能/章节：用途是 YYY

### Fixed（修复）
- 修复了 XXX 问题：表现是 YYY，修复方式是 ZZZ
```

### 版本号规则（可选）

- **主版本号**：重大架构变更
- **次版本号**：新增功能或章节
- **修订号**：修复问题或微调

### 变更类型说明

| 类型 | 说明 |
|------|------|
| Added | 新增的功能或章节 |
| Changed | 对现有功能或内容的变更 |
| Deprecated | 即将移除的功能（警告） |
| Removed | 已移除的功能 |
| Fixed | 修复的问题 |
| Security | 安全相关的修复 |
