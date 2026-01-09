# Changelog

本文件记录项目的修改历史，方便回顾项目的优化过程。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)。

---

## [Unreleased]

### Changed（变更）

- 更新 [AGENTS.md](AGENTS.md) 和 [CLAUDE.md](CLAUDE.md)：在"变更记录规范"中新增"Skill 文档编写原则"子章节，明确 Skill 文档（SKILL.md）应始终展示最新状态，不包含版本标记等对 AI 执行无用的元信息；包括内容优先于版本、简洁标题、单一职责等原则及设计公式

- 更新 [AGENTS.md](AGENTS.md) 和 [CLAUDE.md](CLAUDE.md)：在"核心工作流/执行流程"中新增"计划制定原则"，要求任务按优先级从上到下罗列，不使用时间限制表述（如"第1-2周"、"第3-4周"等）；同时更新 CLAUDE.md 的"任务管理"章节同步此原则

- 更新 [README.md](README.md)：在"AI 模型配置建议"中补充 Claude Code + Claude 4.5 Opus "比较昂贵"的提示，新增 Codex CLI + GPT-5.2 Medium 的推荐组合，并在"API 获取建议"中补充 Packycode Codex 站点说明与扩写 DMXAPI 介绍
- 更新 [AGENTS.md](AGENTS.md)：修正目录结构，移除不存在的根级 `scripts/`，并说明脚本主要位于 `skills/*/scripts/`
- 更新 [CLAUDE.md](CLAUDE.md)：修正目录结构，移除不存在的根级 `scripts/`，并说明脚本主要位于 `skills/*/scripts/`
- 更新 `skills/make_latex_model/README.md`：补充“优先用 Prompt 调用 Skill”的推荐用法，并将脚本流程作为备选
- **nsfc-justification-writer v0.2.0** - 升级信息表与文档，并补齐可复现的“诊断→写入→验收”闭环
  - 更新 `skills/nsfc-justification-writer/references/info_form.md`：8 项信息表（必填/选填标识），与 `extraTex/1.1.立项依据.tex` 的 4 个 `\subsubsection` 对齐
  - 更新 `skills/nsfc-justification-writer/config.yaml` 与 `skills/nsfc-justification-writer/SKILL.md`：加入字数参数、术语 alias_groups、Tier1/Tier2（可选）诊断说明

- **nsfc-justification-writer v0.3.0** - 落地改进计划（P1–P3），主推“渐进式写作引导”
  - 更新 `skills/nsfc-justification-writer/scripts/run.py`：新增 `init/coach/review/refs` 与 `diff/rollback/list-runs` 子命令，`diagnose` 支持 `--html-report`
  - 更新 `skills/nsfc-justification-writer/core/term_consistency.py`：术语矩阵改为“按章节统计命中次数”，并识别“同章内不一致”
  - 更新 `skills/nsfc-justification-writer/core/reference_validator.py` 与 `skills/nsfc-justification-writer/core/diagnostic.py`：增加 DOI 缺失提示（可核验性增强）
  - 更新 `skills/nsfc-justification-writer/core/hybrid_coordinator.py`：`apply-section` 默认严格拒绝“缺失 bibkey 的 \\cite{...}”（防止幻觉引用）
  - 更新 `skills/nsfc-justification-writer/README.md`、`skills/nsfc-justification-writer/SKILL.md`、`skills/nsfc-justification-writer/scripts/README.md`：补齐渐进式写作闭环与新命令用法

- **nsfc-justification-writer v0.4.0** - 对齐配置/示例/体验与可扩展性
  - 更新 `skills/nsfc-justification-writer/SKILL.md`：补齐“4 段闭环”与 4 个 `\\subsubsection` 标题的映射表，并修正工作流编号
  - 更新 `skills/nsfc-justification-writer/templates/structure_template.tex`：为每个 `\\subsubsection` 增加写作要点注释
  - 更新 `skills/nsfc-justification-writer/core/example_matcher.py` 与 `skills/nsfc-justification-writer/examples/`：引入 `*.metadata.yaml` 关键词元数据，扩展多学科示例与匹配逻辑
  - 更新 `skills/nsfc-justification-writer/templates/html/report_template.html`：新增“点击行号复制/复制页面链接”的交互与更清晰的定位说明
  - 更新 `skills/nsfc-justification-writer/core/config_loader.py`、`skills/nsfc-justification-writer/config/presets/`、`skills/nsfc-justification-writer/scripts/run.py`：支持 `--preset` 学科预设与用户 `override.yaml` 配置覆盖（可用 `--no-user-override` 关闭）
  - 更新 `skills/nsfc-justification-writer/tests/`：补齐 diagnostic/writing_coach/example_matcher 单测与 integration 流程用例
  - 新增 `skills/nsfc-justification-writer/docs/`：补齐教程与架构说明

- **nsfc-justification-writer v0.5.0** - 按改良计划完成 P0–P2（稳定性/体验/可扩展性）
  - 更新 `skills/nsfc-justification-writer/core/config_loader.py` 与 `skills/nsfc-justification-writer/scripts/run.py`：新增 `validate-config` 配置校验命令，并默认做关键字段类型校验（可用 `NSFC_JUSTIFICATION_WRITER_DISABLE_CONFIG_VALIDATION=1` 关闭）
  - 更新 `skills/nsfc-justification-writer/core/ai_integration.py`、`skills/nsfc-justification-writer/core/hybrid_coordinator.py` 与 `skills/nsfc-justification-writer/scripts/run.py`：Tier2 支持分块处理与 `.cache/ai` 缓存（`--chunk-size/--max-chunks/--fresh`）
  - 更新 `skills/nsfc-justification-writer/core/term_consistency.py` 与 `skills/nsfc-justification-writer/config.yaml`：跨章节一致性升级为“研究对象/指标/术语”三维矩阵（`terminology.dimensions`）
  - 更新 `skills/nsfc-justification-writer/core/reference_validator.py`、`skills/nsfc-justification-writer/core/diagnostic.py` 与 `skills/nsfc-justification-writer/core/bib_manager_integration.py`：修复 bib DOI 解析并新增 DOI 格式异常提示，`refs` 支持可选 Crossref 联网校验（`--verify-doi crossref`）
  - 更新 `skills/nsfc-justification-writer/examples/` 与 `skills/nsfc-justification-writer/core/example_matcher.py`：新增 chemistry/biology/math 示例与领域加权提示
  - 新增 `skills/nsfc-justification-writer/docs/workflows/`：补齐典型工作流文档（已有草稿迭代、引用/DOI 核验）
  - 更新 `skills/nsfc-justification-writer/tests/`：补齐 AI 集成/配置校验/分块与缓存/术语维度等测试用例

- **nsfc-justification-writer v0.6.0** - 按 v202601091932 完成“AI 主导 + 优雅降级”的全缺陷修复
  - 新增 `skills/nsfc-justification-writer/core/io_utils.py`：流式读取与按 `\\subsubsection` 边界分块（降低大文件峰值内存）
  - 更新 `skills/nsfc-justification-writer/core/latex_parser.py`：替换正则解析为更稳健的结构解析（支持嵌套花括号/可选短标题/更可靠的注释剥离），并新增“标题候选 + AI 语义匹配”能力
  - 更新 `skills/nsfc-justification-writer/core/hybrid_coordinator.py` 与 `skills/nsfc-justification-writer/scripts/run.py`：`apply-section` 增强错误提示与修复建议，新增 `--suggest-alias`；Tier2 对超大文件优先流式分块
  - 更新 `skills/nsfc-justification-writer/core/term_consistency.py`、`skills/nsfc-justification-writer/core/writing_coach.py` 与 `skills/nsfc-justification-writer/config.yaml`：新增 `terminology.mode=auto|ai|legacy`，AI 可用时叠加语义一致性检查并自动回退到矩阵规则
  - 更新 `skills/nsfc-justification-writer/core/prompt_templates.py` 与 `skills/nsfc-justification-writer/core/config_loader.py`：Prompt 支持“路径或多行内联文本”，并支持按 `--preset` 变体覆盖（如 `prompts.tier2_diagnostic_medical`）
  - 更新 `skills/nsfc-justification-writer/core/example_matcher.py`：AI 语义示例推荐（带理由）+ 关键词 fallback
  - 更新 `skills/nsfc-justification-writer/config.yaml`、`skills/nsfc-justification-writer/core/config_loader.py` 与 `skills/nsfc-justification-writer/SKILL.md`：版本升级至 v0.6.0，并同步文档

- **transfer_old_latex_to_new** - 脚本目录结构优化
  - 移动 `demo_core_features.py` → [scripts/demo.py](skills/transfer_old_latex_to_new/scripts/demo.py)：演示脚本归位到 scripts/ 目录
  - 移动 `run_tests.py` → [scripts/quicktest.py](skills/transfer_old_latex_to_new/scripts/quicktest.py)：快速测试工具重命名并归位
  - 更新两个脚本的路径引用(`Path(__file__).parent.parent`)以适配新位置
  - 新增 [scripts/README.md](skills/transfer_old_latex_to_new/scripts/README.md)：文档化所有脚本用途与使用场景
  - 技能根目录更清爽,仅保留配置文件和文档

- **transfer_old_latex_to_new** - LaTeX 中间文件隔离优化
  - 修改 [compiler.py](skills/transfer_old_latex_to_new/core/compiler.py)：使用 `-output-directory` 参数将 LaTeX 编译中间文件(.aux/.log/.bbl/.blg/.out/.toc 等)重定向到 `runs/<run_id>/logs/latex_aux/` 目录
  - 编译成功后自动复制 `main.pdf` 到项目根目录,方便用户查看
  - 项目目录保持清洁,不再产生编译"垃圾"文件
  - 更新 [SKILL.md](skills/transfer_old_latex_to_new/SKILL.md)：文档化目录结构与编译隔离机制

- **transfer_old_latex_to_new v1.3.1** - 易用性与可测试性增强
  - 新增一键迁移脚本：[scripts/migrate.sh](skills/transfer_old_latex_to_new/scripts/migrate.sh)（analyze→apply→(可选)compile）
  - CLI 增强：[scripts/run.py](skills/transfer_old_latex_to_new/scripts/run.py) 支持 `--runs-root` 隔离 runs 输出，并补充路径校验与更友好的错误提示
  - 进度反馈：[migrator.py](skills/transfer_old_latex_to_new/core/migrator.py) 集成进度条（rich 可用则使用，否则回退到文本）
  - 文档拆分：新增 [docs/](skills/transfer_old_latex_to_new/docs/) 并精简 [SKILL.md](skills/transfer_old_latex_to_new/SKILL.md)

- **transfer_old_latex_to_new v1.4.0** - P1 质量保障落地
  - 新增配置校验工具：[scripts/validate_config.py](skills/transfer_old_latex_to_new/scripts/validate_config.py)（类型/范围/编译序列等常见错误提前拦截）
  - runs 管理子命令：[scripts/run.py](skills/transfer_old_latex_to_new/scripts/run.py) 新增 `runs list/show/delete`（迁移历史可追溯，删除需 `--yes`）
  - 文档补齐：新增 [docs/faq.md](skills/transfer_old_latex_to_new/docs/faq.md) 与 [docs/case_study_2025_to_2026.md](skills/transfer_old_latex_to_new/docs/case_study_2025_to_2026.md)
  - 运行更干净：脚本默认不写 `__pycache__`（避免在项目目录产生中间文件）

### Added（新增）

- 新增 `make_latex_model` 入口文档：`skills/make_latex_model/README.md`

- 新增迁移验证记录：`tests/v202601081624/TEST_REPORT.md`

- 新增 NSFC 2026 新模板写作 Skill 迁移建议计划（已脱敏）：`plans/v202601081910.md`

- **nsfc-justification-writer v0.2.0** - 硬编码确定性能力与配套脚本
  - 新增脚本入口：`skills/nsfc-justification-writer/scripts/run.py`（diagnose/wordcount/terms/apply-section）
  - 新增核心模块：`skills/nsfc-justification-writer/core/`（结构解析、引用核验、字数统计、术语矩阵、安全写入、可观测性）
  - 新增单元测试：`skills/nsfc-justification-writer/tests/`（pytest）
  - 新增示例与模板：`skills/nsfc-justification-writer/examples/`、`skills/nsfc-justification-writer/templates/`
  - 新增诊断示例：`skills/nsfc-justification-writer/references/diagnostic_examples.md`

- **nsfc-justification-writer v0.3.0** - 渐进式写作与可视化/版本能力
  - 新增渐进式写作引导：`skills/nsfc-justification-writer/core/writing_coach.py`（coach）
  - 新增交互式信息表收集：`skills/nsfc-justification-writer/core/info_form.py`（init --interactive）
  - 新增评审建议生成：`skills/nsfc-justification-writer/core/review_advice.py`（review）
  - 新增 HTML 诊断报告：`skills/nsfc-justification-writer/core/html_report.py`、`skills/nsfc-justification-writer/templates/html/report_template.html`
  - 新增版本 diff/回滚：`skills/nsfc-justification-writer/core/versioning.py`
  - 新增示例推荐：`skills/nsfc-justification-writer/core/example_matcher.py`（coach --topic / examples）
  - 新增 prompts 外部化：`skills/nsfc-justification-writer/prompts/`
  - 新增端到端测试：`skills/nsfc-justification-writer/tests/e2e/test_cli_flow.py`

- 新增 NSFC 2026 新模板写作主技能（MVP，按新板块契约落到 `extraTex/*.tex`）
  - `skills/nsfc-justification-writer/`：对应 `（一）立项依据`
  - `skills/nsfc-research-content-writer/`：对应 `（二）研究内容`（并编排创新点与年度计划）
  - `skills/nsfc-research-foundation-writer/`：对应 `（三）研究基础`（并编排工作条件与风险应对）

- 新增 `transfer_old_latex_to_new` v1.3.0 详细改进计划：`plans/v202601081102.md`
  - **核心修复**：移除所有 AI 功能占位符，实现真实的 AI 集成
  - **AI 集成层**：创建 `core/ai_integration.py`，利用 Claude Code/Codex 当前环境（无需额外配置）
  - **迁移策略**：实现一对多/多对一迁移（`core/strategies.py`）
  - **模块集成**：集成 `ContentOptimizer`、`ReferenceGuardian`、`WordCountAdapter` 到主流程
  - **CLI 扩展**：添加 `--optimize`、`--adapt-word-count`、`--ai-enabled` 选项
  - **实施计划**：4 个 Sprint，预计 6-8 小时
  - **问题诊断**：彻底代码审查发现 AI 功能虚假实现、依赖不存在模块、迁移策略不完整

- 新增 `transfer_old_latex_to_new` v1.3.0 优化计划：`plans/v202601081002.md`
  - **性能优化**：引入分层缓存机制、批量 AI 调用、并行化处理（预期性能提升 5-10 倍）
  - **质量保证**：建立测试体系（pytest，目标覆盖率 80%）
  - **用户体验**：实时进度反馈、细粒度错误恢复、简化配置（预设模板）
  - **高级功能**：智能版本检测、AI 写作风格评分、插件化架构
  - **用户痛点彻底解决**（3 个新增优化项）：
    - ✅ **优化项 12：字数自动适配** - 自动检测旧字数 → 新字数，调用 AI 或写作技能扩展/精简
    - ✅ **优化项 13：引用强制保护** - AI 调用前强制保护所有引用，输出后验证并自动修复
    - ✅ **优化项 14：AI 智能优化写作** - AI 自动识别并修复冗余、逻辑、证据、清晰度、结构问题
  - **分阶段实施计划**：5 个阶段，预计 10-13 周（新增 3 个核心优化项）

- 新增 `transfer_old_latex_to_new` 工程化落地优化计划：`plans/v202601080843.md`
- **transfer_old_latex_to_new（MVP 可执行闭环）**
  - 新增可执行脚本入口：`skills/transfer_old_latex_to_new/scripts/run.py`（`analyze/apply/compile/restore`）
  - 新增 `runs/<run_id>/` 工作空间：结构分析、迁移计划、日志、交付物与快照备份集中管理
  - 新增核心模块：结构分析、映射生成、迁移执行（原子写入+白名单保护）、编译日志摘要、交付物生成
  - 新增最小烟雾测试：`skills/transfer_old_latex_to_new/tests/test_smoke.py`

- **transfer_old_latex_to_new v1.1.0** - 🤖 AI 驱动映射引擎：让 AI 真正理解文件映射关系
  - **移除硬编码相似度公式**：不再使用固定权重（`0.7 * stem + 0.2 * title + 0.1 * content`）计算相似度
  - **AI 语义判断**：让 AI 真正理解文件内容（文件名、章节结构、内容语义、迁移合理性）后判断映射关系
  - **映射引擎重构**：
    - 新增 `_build_file_context()`: 为 AI 构建文件上下文（路径、结构、摘要、预览）
    - 新增 `_ai_judge_mapping()`: AI 判断映射关系的异步函数（占位符，待集成实际 AI 调用）
    - 新增 `compute_structure_diff_async()`: 异步版本的结构差异分析
    - 保留 `_fallback_score_pair()`: 当 AI 不可用时使用简单启发式规则
  - **配置文件优化**：
    - 移除硬编码权重配置（`title_similarity_weight`、`content_similarity_weight` 等）
    - 新增 `mapping.strategy`: `ai_driven`（AI 语义判断）/ `fallback`（简单启发式）
    - 新增 `mapping.thresholds`: AI 判断阈值（high/medium/low）
    - 新增 `mapping.fallback`: 回退策略配置（文件名匹配、包含关系、Jaccard 相似度）
  - **文档更新**：
    - SKILL.md 新增"AI 语义判断"章节，详细说明 AI 判断流程和判断维度
    - README.md 更新核心能力，突出"AI 语义映射"
  - **版本升级**：v1.0.0 → v1.1.0

- **transfer_old_latex_to_new v1.2.0** - 📦 资源文件智能处理：保证引用完整性
  - **核心问题解决**：迁移过程自动处理资源文件（图片、代码等），保证引用完整性
  - **新增资源文件扫描**：
    - 新增 `core/resource_manager.py` 模块：资源文件扫描、复制、完整性验证
    - 支持资源类型：
      - 图片：`\includegraphics{figures/fig1.pdf}`
      - 代码：`\lstinputlisting{code/algo.py}`
      - 其他文件：`\import{path}{file}`

### Fixed（修复）

- **transfer_old_latex_to_new** - 修复 `compile_project()` 在 `-output-directory` 隔离中间文件时，`bibtex` 因工作目录切换导致无法定位 `.bst/.bib` 的问题
  - 在 `bibtex` 步骤注入 `BSTINPUTS/BIBINPUTS` 搜索路径（指向项目根目录），确保可读取 `bibtex-style/` 与 `references/`
  - 编译成功判定纳入 `bibtex` 返回码，避免“引用未生成但仍显示成功”

- **transfer_old_latex_to_new** - 修复 `ReferenceGuardian.restore_references()` 在 Python 3.12 下替换 `\\ref/\\cite` 等内容时触发 `re.error: bad escape` 的问题
  - **增强迁移流程**（`core/migrator.py`）：
    - 第一步：迁移 `.tex` 内容文件
    - 第二步：扫描旧项目的资源文件
    - 第三步：复制资源文件到新项目（只复制缺失的，避免覆盖）
    - 第四步：验证新项目中的资源引用完整性
  - **LaTeX 工具增强**（`core/latex_utils.py`）：
    - 新增 `extract_graphics()`: 提取图片引用
    - 新增 `extract_lstinputlisting()`: 提取代码文件引用
    - 新增 `extract_imports()`: 提取 LaTeX import 路径
    - 新增 `extract_all_resource_paths()`: 提取所有外部资源文件路径
  - **配置优化**：
    - `migration.figure_handling`: `copy`（复制，默认推荐）/ `link`（软链接）/ `skip`（跳过）
  - **结果报告增强**：
    - `ApplyResult` 新增 `resources` 字段，包含资源处理详情
    - 扫描摘要：总资源数、缺失数、涉及目录
    - 复制摘要：复制数、跳过数、失败数、创建的目录
    - 验证摘要：有效资源数、缺失资源数、损坏的引用
  - **文档更新**：
    - SKILL.md 新增"资源文件处理"章节
    - 核心模块索引新增"资源管理"模块
  - **版本升级**：v1.1.0 → v1.2.0

- **complete_example v1.1.0** - 🔒 安全增强：系统文件保护与格式注入扫描
  - **SecurityManager 模块**：统一的安全检查和访问控制
    - 系统文件黑名单保护（`main.tex`、`@config.tex` 绝对禁止修改）
    - SHA256 哈希校验（检测文件是否被外部篡改）
    - 格式注入检测（扫描并自动清理危险的格式指令）
    - 白名单模式匹配（只允许编辑符合正则表达式的文件）
    - 违规报告生成（详细的安全违规日志）
  - **FormatGuard 增强**：集成 SecurityManager 进行预检查
    - 编辑前自动进行系统文件检查和完整性校验
    - 应用前自动进行格式注入检查和清理
    - 支持自动清理模式（默认启用）
  - **配置文件更新**：新增 `security` 配置节
    - 系统文件黑名单和白名单配置
    - 格式关键词黑名单配置
    - 文件完整性校验配置
    - 内容安全扫描配置
  - **文档更新**：
    - SKILL.md 新增"分层安全保护"章节
    - 详细说明三层安全架构（系统文件/用户内容/内容扫描）
    - 配置示例和使用说明

- **complete_example v1.0.0** - AI 增强版 LaTeX 示例智能生成器
  - **核心功能**：AI 驱动的示例内容生成，支持用户自定义叙事提示
  - **用户提示机制**：允许通过 `narrative_hint` 参数指定研究主题、方法、场景，AI 根据提示编造合理的示例内容
  - **运行目录隔离**：所有运行输出（备份、日志、分析结果）放在 `skills/complete_example/runs/<run_id>/` 目录中，完全不对项目目录造成污染
  - **架构设计**：AI 负责"语义理解"，硬编码负责"结构保护"，有机协作
  - **核心模块**：
    - `SemanticAnalyzer`：AI 语义分析器（章节主题理解、资源相关性推理）
    - `AIContentGenerator`：AI 内容生成器（叙述性文本生成、自我优化）
    - `ResourceScanner`：资源扫描器（figures、code、references）
    - `FormatGuard`：格式守护器（格式保护、哈希验证、自动回滚）
    - `CompleteExampleSkill`：主控制器（完整工作流协调）
  - **工具模块**：LLM 客户端、LaTeX 解析、BibTeX 解析、文件操作

### Fixed（修复）

- 修复并落地 `transfer_old_latex_to_new`（对齐 `plans/v202601081102.md` 的核心问题）
  - 新增 `skills/transfer_old_latex_to_new/core/ai_integration.py`：统一 AI 接口，未接入真实 AI 时优雅降级
  - 修复错误导入：移除 `get_ai_config` 与 `skill_core` 依赖，避免运行时 `ModuleNotFoundError`
  - 集成可选后处理：`apply_plan()` 支持 `--optimize` 内容优化与 `--adapt-word-count` 字数适配
  - CLI 扩展：`skills/transfer_old_latex_to_new/scripts/run.py` 新增 `--no-ai/--optimize/--adapt-word-count`
  - 同步更新文档与测试：保证默认环境下功能可用且用法一致
  - **使用示例**：基本用法、高级用法（医疗影像、材料科学、临床试验、传统 ML）
  - **配置文件**：完整的 YAML 配置（LLM、参数、运行管理、资源扫描、格式保护、AI 提示词）
  - **测试框架**：单元测试、集成测试、AI 能力测试
  - **文档**：SKILL.md、README.md、设计计划 [plans/v202601071300.md](plans/v202601071300.md)

- **make_latex_model v2.7.0** - 全自动化工作流程优化
  - **PDF 基准获取增强**：
    - 步骤 2.1 改为"获取 Word PDF 基准"（原"生成 Word PDF 基准"）
    - 新增"方案 0：用户已提供 PDF"作为首选方案（最快，零操作）
    - 调整 LibreOffice 为"方案 1"，Microsoft Word COM 为"方案 2"
    - 渲染质量对比表格新增"用户已提供 PDF"条目
    - Q1 常见问题同步更新：支持用户已提供 PDF 或自动生成
  - **文档优化**：
    - 移除所有"在 Microsoft Word 中打开模板"等手动操作说明
    - Q1 重写：强调完全自动化的工作流程
    - 删除步骤 2.3"手动测量（备用方案，不推荐）"章节（AI 无法执行）
    - 删除"迁移说明"章节（工作空间管理章节）
    - 步骤 2.5 新增 `--auto-convert` 自动转换 .doc 为 .docx
    - 移除年份偏倚：将所有具体年份（2026）改为通用表述（2025/最新模板/YYYY-MM-DD）
    - 修正标题层级：移除所有子章节的冗余编号前缀（如 3.5.1→、4.1→、5.0→）
  - **核心理念**：本技能为全自动化技能，用户无需手动操作任何 GUI 工具

- **make_latex_model v2.6.0** - 文档格式优化
  - 移除 SKILL.md 中所有主要章节标题前的序号（如 `## 1)` → `##`）
  - 更新文档目录中的锚点链接以匹配新的标题格式
  - 提升文档可读性和链接稳定性

- **make_latex_model v2.5.0** - HTML 可视化报告与自动修复建议
  - **Phase 2: HTML 报告增强**：
    - 新增 `render_formatted_text_html()`：将格式片段渲染为 HTML（加粗用 `<b>` 标签）
    - 新增 `generate_html_report_with_format()`：生成包含格式对比的 HTML 报告
    - HTML 报告支持：
      - 加粗文本可视化（`<b>` 标签深蓝色显示）
      - 并排对比（Word vs LaTeX）
      - 格式差异高亮（黄色背景 + 详细位置标注）
      - 响应式设计，最大宽度 1400px
      - 四种统计卡片：完全匹配、文本差异、格式差异、仅在一方
  - **Phase 3: 自动修复建议**：
    - 新增 `generate_latex_fix_suggestions()`：生成 LaTeX 修复代码
    - `compare_headings.py` 新增 `--fix-file` 参数：输出修复建议到指定文件
    - 自动生成可直接复制的 `\section{}` 和 `\subsection{}` 代码
    - 根据 Word 格式生成正确的 `\textbf{}` 标记
  - **命令行增强**：
    - `--check-format` 模式下支持 HTML 报告（移除"后续版本增强"的临时提示）
    - 新增 `--fix-file` 参数，与 `--check-format` 配合使用
  - **文档更新**：
    - SKILL.md 步骤 2.5 新增 HTML 可视化报告使用说明（第 5 条）
    - SKILL.md 步骤 2.5 新增 LaTeX 修复建议使用说明（第 6 条）
    - description 更新：添加"HTML 可视化报告、LaTeX 自动修复建议"
  - **完整实现计划 v202601060836**：
    - ✅ Phase 1（核心功能）：100% 完成
    - ✅ Phase 2（可视化增强）：100% 完成
    - ✅ Phase 3（自动修复建议）：100% 完成

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

- **项目指令文档** - 新增 LaTeX 编译4步法规范
  - **CLAUDE.md 和 AGENTS.md**：新增「LaTeX 编译规范」章节
    - 说明 PDF 渲染4步法：`xelatex → bibtex → xelatex → xelatex`
    - 每步的作用说明（生成辅助文件、处理参考文献、解析文献引用、确保交叉引用正确）
    - 使用原则：修改参考文献后必须完整执行4步，仅修改正文时可省略 bibtex 步骤
  - **有机整合**：与现有「LaTeX 标题换行控制」章节并列，形成完整的 LaTeX 操作规范

- **项目指令文档** - 指令规范精炼与一致性增强
  - **CLAUDE.md 和 AGENTS.md**：精炼「项目目标」「联网与搜索」表述，补充“不自动清理/删除 `.DS_Store`”边界，并统一核心章节一致性提示

### Changed（变更）

- **make_latex_model v2.7.1** - 修复验证器运行入口
  - 修复 `scripts/run_validators.py` 的导入路径，避免 `validators` 相对导入报错

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

---

## 模板版本历史

### 2025-03-12：v2.5.0 重大更新

> :warning: 修复：面上、地区基金"3.正在承担的与本项目相关的科研项目"段落结尾缺少分号

![mQW1QFdXDq](https://chevereto.hwb0307.com/images/2025/03/12/mQW1QFdXDq.png)

### 2025-03-01：v2.4.6

- 优化：`\kaishu` → `\templatefont` 增强字体兼容性
- 优化：改善 `subsubsection` 序号显示
- 修复：系统 TimesNewRoman 适用于 macOS/Overleaf

### 2025-01-25：v2.4.2

- 修复：面上和地区基金 `font/` 文件夹缺失
- 修复：面上模板 `(建议 8000 字以下)` 未加粗
- 优化：增强 Overleaf/macOS 平台兼容

### 2025-01-24：2025 版发布

完整更新说明详见博客文章《[国家自然科学基金的 LaTeX 模板](https://blognas.hwb0307.com/skill/5762)》。
