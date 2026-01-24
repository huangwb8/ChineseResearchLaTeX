# check-review-alignment 变更日志

本文档记录 `check-review-alignment/` 的重要变更。格式遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)。

## [Unreleased]

（暂无）

## [1.0.2] - 2026-01-24

### Added（新增）
- `check-review-alignment/scripts/run_ai_alignment.py`：`ai_alignment_input.json` 的 `papers[*]` 补充 `doi`/`url` 字段，提升引用核查可追溯性
- `check-review-alignment/scripts/run_ai_alignment.py`：缺失 bibkey 汇总到 `warnings`，并在 `stats.missing_in_bib_bibkeys` 输出计数
- `check-review-alignment/scripts/run_ai_alignment.py`：PDF 路径位于 work_dir 外时输出 warning（不强制阻断）
- `check-review-alignment/scripts/runtime_utils.py`：当 work_dir 内存在多个 tex 候选时输出 warning，引导用户使用 `--tex` 指定
- `check-review-alignment/SKILL.md`：报告格式新增"具体细节"强制章节，要求每条引用记录四要素（原文内容/文献实际/引用合理性评估/问题级别），提升报告可追溯性

### Changed（变更）
- `check-review-alignment/config.yaml`：版本号 `1.0.1 → 1.0.2`
- `check-review-alignment/scripts/run_ai_alignment.py`：`--prepare` 不再强制依赖 `systematic-literature-review`（依赖检查仅在 `--render` 路径执行）
- `check-review-alignment/scripts/run_ai_alignment.py`：中间文件（`ai_alignment_input.json`）改保存在 `{work_dir}/.check-review-alignment/` 隐藏文件夹，避免污染综述项目根目录
- `check-review-alignment/SKILL.md`：依赖检查口径调整为“仅渲染路径强制”，并同步说明结构化输入字段
- `check-review-alignment/SKILL.md`：同步更新输出路径说明（`ai_alignment_report.md` 和 `ai_alignment_input.json` 均保存在 `.check-review-alignment/` 目录）
- `check-review-alignment/README.md`：同步更新快速开始与 FAQ 口径（只修复 P0、P1 仅警告；`--prepare` 不依赖渲染 skill）
- `check-review-alignment/README.md`：同步更新"输出文件"章节与 FAQ，明确中间文件保存位置
- `check-review-alignment/README.md`：在"快速开始"章节新增"使用前必读"子章节，强调版本控制的重要性，并提供 Git 和手动备份两种方案
- `check-review-alignment/README.md`：在"常见问题"部分新增"如果修改不满意，如何恢复到之前的版本？" FAQ，详细说明回滚方法与最佳实践
- `check-review-alignment/scripts/run_ai_alignment.py`：缺少 tex/bib 时输出友好错误并返回退出码（避免 traceback）

### Fixed（修复）
- `check-review-alignment/scripts/paragraph_analyzer.py`：剔除行内 `%` 注释并忽略 verbatim-like 代码块，避免误抽取 citations
- `check-review-alignment/scripts/paragraph_analyzer.py`：修复 `CitationInContext.sentence_start/sentence_end` 语义（改为句子边界）

## [1.0.1] - 2026-01-24

### Changed（变更）
- `check-review-alignment/config.yaml`：新增致命性错误优先级分级（P0/P1/P2），并将 `ai.paragraph_optimization.enabled` 默认改为 `false`，确保“不为了改而改”
- `check-review-alignment/SKILL.md`：补齐“修改边界与优先级”（P0 必修 / P1 仅警告 / P2 跳过）与报告结构要求（Critical Fixes / Warnings）
- `check-review-alignment/README.md`：同步更新设计哲学、错误优先级说明与 FAQ 口径
- `check-review-alignment/scripts/runtime_utils.py`：增强 `--tex` 参数校验（仅允许文件名，避免路径遍历），并补齐默认 `ai.input_limits`
- `check-review-alignment/scripts/paragraph_analyzer.py`：修复缩写保护逻辑，避免断句前置替换把正则转义字符写回正文

### Added（新增）
- `check-review-alignment/scripts/run_ai_alignment.py`：在 `ai_alignment_input.json` 中打包 `policy`（修改策略/优先级配置），方便宿主 AI 严格按边界执行
- `check-review-alignment/scripts/run_ai_alignment.py`：新增配置健壮性解析（对 `pdf.max_pages` / `ai.input_limits.*` / `ai.modification.max_edits_per_sentence` 做安全回退并记录 warnings）
- `check-review-alignment/scripts/run_ai_alignment.py`：在 `ai_alignment_input.json` 中打包 `skill_info`（name/version/description/category），便于宿主 AI 追溯版本与口径

## [1.0.0] - 2026-01-24

### Changed（变更）
- 破坏性重构：删除静态规则模式，统一为“纯 AI 语义核查与最小化改写”工作流
- `check-review-alignment/SKILL.md`：新增依赖声明与强制依赖检查步骤，收敛为单一 AI 工作流（不再导出 ai_tasks）
- `check-review-alignment/config.yaml`：版本号 `0.2.0 → 1.0.0`；精简配置结构，移除 `similarity.*`、`ai.enabled`、`ai.mode`、`ai.thresholds` 等静态/混合策略配置，并新增 `ai.input_limits` 控制输入截断
- `check-review-alignment/README.md`：更新为纯 AI 模式使用口径

### Removed（移除）
- 删除静态规则实现与混合检查器：`check-review-alignment/scripts/run_alignment.py`、`check-review-alignment/scripts/hybrid_checker.py`
- 删除“任务导出型 AI 模块”和 prompts：`check-review-alignment/scripts/ai_*.py`、`check-review-alignment/prompts/`

### Added（新增）
- `check-review-alignment/scripts/run_ai_alignment.py`：重写为确定性辅助入口（依赖检查/解析抽取/可选渲染），并新增 `ai_alignment_input.json` 输出
- `check-review-alignment/scripts/runtime_utils.py`、`check-review-alignment/scripts/bib_utils.py`：抽离确定性通用逻辑，便于脚本复用与测试
- 新增 A/B 轮轻量测试会话：`check-review-alignment/tests/v202601241048/`、`check-review-alignment/tests/B轮-v202601241048/`，以及对应规划文档：`check-review-alignment/plans/v202601241048.md`、`check-review-alignment/plans/B轮-v202601241048.md`

## [0.2.0] - 2026-01-24

### Added（新增）
- 新增 A/B 轮测试会话：`check-review-alignment/tests/v202601240925/`、`check-review-alignment/tests/B轮-v202601240925/`
- 新增规划文档：`check-review-alignment/plans/v202601240925.md`、`check-review-alignment/plans/B轮-v202601240925.md`
- `check-review-alignment/config.yaml`：新增 `skill_info`（版本号唯一来源）
- 新增用户文档：`check-review-alignment/README.md`

### Changed（变更）
- `check-review-alignment/SKILL.md`：收敛触发边界与关键词（3-5 个核心关键词），并将 AI 模式描述调整为“导出 AI 复核任务”口径

### Fixed（修复）
- `check-review-alignment/scripts/run_ai_alignment.py`：修复 AI 模式开启后构造器参数不匹配导致的崩溃
- `check-review-alignment/scripts/run_ai_alignment.py`：修复 `--auto-apply` 的破坏性行为（无修改时不写回；有修改时先备份再应用）
- `check-review-alignment/scripts/run_alignment.py`：报告头部补充 `tex` 文件名，提升可追溯性
- `check-review-alignment/scripts/run_alignment.py`：`find_tex_and_bib()` 对 glob 结果排序，提升可复现性
- `check-review-alignment/scripts/run_alignment.py`：增强 `find_pdf_for_entry()`，避免 `file` 字段因 `:` 解析导致 Windows/Zotero 路径截断

## [0.1.0] - 2026-01-03

### Added（新增）
- 初始化技能，实现静态规则对齐报告与自动渲染流程
