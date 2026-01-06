# Changelog

本文件记录项目的修改历史，方便回顾项目的优化过程。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)。

---

## [Unreleased]

### Added（新增）

- **make_latex_model v2.4.0** - 标题格式对比功能增强
  - **格式对比核心功能**：
    - 新增 `extract_formatted_text_from_word()`：从 Word 段落提取格式化文本片段（加粗信息）
    - 新增 `extract_formatted_text_from_latex()`：从 LaTeX 代码解析 `\textbf{}` 格式
    - 新增 `compare_formatted_text()`：对比 Word 和 LaTeX 的格式一致性
  - **命令行参数扩展**：
    - `compare_headings.py` 新增 `--check-format` 参数：启用格式（加粗）对比
    - 支持向后兼容：默认行为保持不变，仅检查文本内容
  - **报告增强**：
    - 新增 `generate_text_report_with_format()`：生成包含格式差异的文本报告
    - 格式差异报告显示：Word 和 LaTeX 的加粗位置对比、具体差异位置标注
  - **文档更新**：
    - SKILL.md 步骤 2.5 新增格式对比使用说明
    - description 更新：添加"标题格式对比（加粗）"功能描述

- **make_latex_model v2.3.0** - 迭代优化闭环与工作空间重构
  - **工作空间管理（Phase 0）**：
    - 新增 `core/workspace_manager.py`：统一管理 skill 工作目录，避免污染用户项目目录
    - 工作空间结构：`workspace/{project}/baseline/`、`iterations/`、`reports/`、`cache/`、`backup/`
    - 支持旧路径自动迁移和缓存清理策略
  - **基础功能增强（Phase 1）**：
    - 新增 `scripts/prepare_main.py`：预处理 main.tex，自动注释/恢复 `\input{}` 行
    - 新增 `scripts/generate_baseline.py`：自动检测模板文件，使用 Word/LibreOffice 转换为 PDF
    - 新增 `scripts/convergence_detector.py`：综合判断迭代优化是否达到停止条件
    - 新增 `scripts/enhanced_optimize.py`：一键式迭代优化入口
  - **智能调整（Phase 2）**：
    - 新增 `scripts/intelligent_adjust.py`：分析像素差异，根据差异特征推断参数调整建议
  - **配置扩展**：
    - `config.yaml` 新增 `workspace` 配置节（工作空间路径、清理策略）
    - `config.yaml` 新增 `iteration` 配置节（最大迭代、收敛阈值、调整粒度、像素对比配置）
    - `config.yaml` 新增 `baseline` 配置节（转换器优先级、质量验证）
  - **文档更新**：
    - SKILL.md 新增「0.7) 工作空间说明」章节
    - SKILL.md 新增「3.5) 迭代优化闭环」章节

### Changed（变更）

- **make_latex_model v2.2.1** - SKILL.md 文档结构优化（方案 A）
  - **P1 文档优化**：
    - 合并重复的验证清单：4.3 节改为引用第 6 节，减少约 30 行重复内容
    - 整合 Q1、Q1.1、Q2 为一个完整的"Word 打印 PDF"问题，消除主题重复
    - 整合 AI 决策点规范（0.7 节）到第 3 节执行流程的相应步骤中，提升上下文连贯性
    - 新增文档目录结构，提升导航性
  - **优化效果**：
    - 消除约 50+ 行重复内容
    - 提升信息密度和可读性
    - 保持单文档结构，便于 AI 理解

- **make_latex_model v2.2.0** - 架构澄清：AI 与硬编码协调改进
  - **P0 架构澄清**：
    - 在 SKILL.md 中新增「0.6) 执行模式说明」章节：明确硬编码工具与 AI 规划的执行边界
    - 在 SKILL.md 中新增「0.7) AI 决策点规范」章节：定义 4 个关键决策点的输入、逻辑和输出
    - 新增 `scripts/check_state.py`：项目状态检查工具，AI 执行前必须运行的预检查脚本
    - 在「执行流程」中新增「步骤 0：预检查」，强制 AI 在优化前执行状态检查

### Added（新增）

- **make_latex_model**：新增 `check_state.py` 状态检查工具
  - 检查项目是否已初始化（@config.tex 存在）
  - 检查是否有 Word PDF 基准文件
  - 检测基准来源（Word PDF / QuickLook / 未知）
  - 检查编译状态和 PDF 分析结果
  - 生成状态报告并导出 JSON 供 AI 读取

### Changed（变更）

- 更新 `AGENTS.md` 与 `CLAUDE.md` 的目录结构示例，使 `skills/` 示例与当前仓库实际技能（`make_latex_model`）一致
- **make_latex_model**：融入 `analyze_pdf.py` 工具到工作流
- **make_latex_model v2.1.1** - 代码库优化与配置清理
  - **P0 紧急修复**：
    - 修复 SKILL.md 版本号不一致（v1.4.0 → v2.1.0）
    - 清理已追踪的系统垃圾文件（.DS_Store 和 __pycache__）
    - 优化 .gitignore 配置（新增虚拟环境、技能输出目录、macOS 补充规则）
  - **P1 核心优化**：
    - 实施配置继承方案：删除 base.yaml 中重复的 validation.tolerance 和 validation.acceptance_priority 配置
    - 统一颜色定义到单一数据源：在 config.yaml 中新增 style_reference.colors 配置，从 base.yaml 中删除重复的颜色定义
  - **P2 次要改进**：
    - 统一 config.yaml 和 SKILL.md 的技能描述文本
    - 清理 output 目录中的运行时生成文件，添加 README.md 说明文档
  - 在 `SKILL.md` 步骤 2 中新增 "2.2 自动提取样式参数" 小节
  - 在 `scripts/README.md` 中新增 `analyze_pdf.py` 工具文档（作为工具 #1）
  - 优化 `analyze_pdf.py`：添加依赖检查、文件验证、改进输出格式
  - 调整工具编号：`validate.sh` (#2)、`benchmark.sh` (#3)、`extract_headings.py` (#4)、`compare_headings.py` (#5)

### Added（新增）- Skills

- **make_latex_model v2.1.0** - 核心功能完善与工作流优化
  - **验证器插件系统（任务 1.1）**：
    - 实现 `CompilationValidator`：编译状态验证（第一优先级）
    - 实现 `StyleValidator`：样式参数验证（行距、颜色、边距、字号、标题格式）
    - 实现 `HeadingValidator`：标题文字验证（集成 compare_headings.py）
    - 实现 `VisualValidator`：视觉相似度验证（PDF 页面尺寸、每行字数统计）
    - 新增 `scripts/run_validators.py`：Python 验证器运行器
  - **PDF 像素对比工具（任务 1.2）**：
    - 新增 `scripts/compare_pdf_pixels.py`：像素级 PDF 对比工具
    - 支持批量对比多页 PDF
    - 生成 HTML 差异报告和差异热图
    - 计算差异像素比例（changed_ratio）
  - **样式配置双向同步工具（任务 1.3）**：
    - 新增 `scripts/sync_config.py`：LaTeX 配置解析与同步工具
    - 解析 `@config.tex` 中的颜色、字号、边距、行距、标题格式
    - 对比 PDF 分析结果与 LaTeX 配置
    - 支持自动修改和预览模式
  - **一键式优化流程（任务 2.1）**：
    - 新增 `scripts/optimize.py`：完整优化流程自动化
    - 8 步流程：分析 Word PDF → 提取标题 → 对比样式 → 生成建议 → 应用修改 → 编译 → 验证 → 生成报告
    - 新增 `scripts/optimize.sh`：Shell 脚本入口
  - **交互式配置向导（任务 2.2）**：
    - 新增 `scripts/setup_wizard.py`：交互式项目配置向导
    - 引导用户完成项目信息、模板选择、优化级别、Word 模板、高级选项
    - 自动生成项目结构和配置文件
  - **Windows 兼容性改进（任务 3.1）**：
    - 新增 `scripts/validate.bat`：Windows 验证脚本
    - 新增 `scripts/benchmark.bat`：Windows 性能测试脚本
    - 新增 `scripts/optimize.bat`：Windows 优化脚本
  - **字体路径自动检测（任务 3.2）**：
    - 新增 `core/font_detector.py`：跨平台字体检测模块
    - 支持 macOS/Windows/Linux 三大操作系统
    - 自动检测常见中文字体（KaiTi、SimSun、SimHei 等）
    - 自动检测常见英文字体（Times New Roman、Arial 等）

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
