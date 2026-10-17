# Changelog

All notable changes to this skill will be documented in this file.

The version number is the single source of truth in `config.yaml` (`skill_info.version`).

## [Unreleased]

### Changed
- 版本推进至 `1.6.0`：删除旧版入口和兼容分支，备份、诊断和脚本 API 只使用当前路径与当前字段；移除 `Tier1/Tier2` 旧分层命名。
- 版本推进至 `1.5.1`：删除信息表生成入口与隐式读取路径，脚本目录只保留确定性检查和安全写入职责；将 `HybridCoordinator` 更名为 `Coordinator`。
- 删除不再参与主流程的信息表模板、`init` CLI 和交互式信息表代码；输入提取清单并入 `references/section_writing.md`，脚本只保留确定性检查与安全写入。
- 将旧的 `HybridCoordinator` 重命名为 `Coordinator`，移除已停用的 Tier2 编排字段和信息表字数解析路径。
- 清理已停用的 `assets/` 资源目录，删除旧版 `coach`、`review`、`examples` 和 `apply-section` 入口及其专用模块，配置只保留当前主流程需要的字段。
- 补充 `SKILL.md` 的参考资料路由，并在 README 提供索引。

- 版本推进至 `1.5.0`：主流程收敛为“宿主 AI 一次性完成理解与改写，Python 完成安全检查与写入”，不再保留旧版兼容入口。

- 版本推进至 `1.3.4`：将主标题规范收敛为“国内外研究现状”，禁止把“本项目切入点”并入标题；研究意义默认压缩为 2–3 段，研究现状主题小节默认 1 段、最多 2 段，并在 Tier2、写作教练、模板、示例和验收清单中同步篇幅与段落边界。

### Added
- 增加标准立项依据内容链，明确研究意义、国内外研究现状、独立的“科学问题与科学假设”小节和小结，以及前期工作与项目切入点的承接位置。
- Tier2 新增章节边界审查与结构化输出；跨小节移动须先形成章节级提案，再生成正文 diff。
- 增加三类前期工作位置 fixture，覆盖研究意义中过早出现、研究现状末尾桥接和详细模型/终点后移。
- 按标准项目样例重写结构模板与方向示例，避免“研究背景—现状—局限性—切入点”四段骨架继续误导新任务。

### Changed
- 版本推进至 `1.3.4`，同步更新 README、脚本指南、Tier2 参考规范、结构模板和方向示例。
- 收回“主验证场景与可证伪判定规则”“总体研究目标与研究思路”等超出立项依据边界的固定章节，将其明确归入研究内容、研究方案或研究基础。
- 明确要求“科学问题与科学假设”在研究现状之后单独成节，位于小结之前；同步更新模板、示例、写作 Prompt 和 Tier2 检查。
- 将默认流程改为完全自动：自动选择/创建正文目标、执行 Tier1+Tier2、自主生成与修订正文、生成 diff、备份并写入；不再要求用户中途确认或审核。`preview` 默认自动写入，`--dry-run` 保留只读模式。
- 写作教练与 Tier2 将缺失信息转为最小保守假设和待核验项，自动继续执行，不生成“需要你补充/确认的问题”。
- 移除默认流程中的交互式信息表问答入口；信息表由宿主 AI 从现有材料自动提取和补齐。
- Tier2 架构改为宿主 AI 直接执行：新增 `references/tier2_semantic_review.md` 作为唯一审查规范；Python `diagnose` 仅负责 Tier1 确定性检查，不再通过 `AIIntegration.responder` 分块、缓存或生成 Tier2 fallback 结论，并移除 Tier2 专用 CLI 参数与 prompt 配置。
- Tier2 宿主 AI 语义检查改为主诊断流程的必选步骤：由当前宿主 AI 直接执行，不再因结构检查失败而静默跳过。
- 移除术语矩阵与固定内容维度检查链路及其独立 `terms` 命令；逻辑、术语、论证维度和专业可读性统一交由宿主 AI 按参考规范自主规划，Python 保留确定性校验和安全写入。
- 移除 Python 侧固定吹牛式表述词表与 `BoastfulExpressionAI` 运行时调用；措辞风险改由宿主 AI 按 `references/boastful_expression_guidelines.md` 进行语义复核，脚本继续负责引用、路径和结构命令等确定性检查。
- 增加面向大同行的专业可读性复核准则：`review`、`coach --stage polish` 和 Tier2 均要求识别长句层级、指代/缩写界定、抽象名词关系与段内衔接问题，并在不改变事实、限定、术语和 LaTeX 结构的前提下给出保真改法。
- Tier2 新增向后兼容的 `readability` 列表，聚合与 HTML 展示均保留旧字段；无 AI 回退继续输出确定性的可读性自检，不将其作为拒写条件。
- 新增 `references/professional_readability_guidelines.md`，同步更新 README、SKILL 和参考文档索引。
- 合并 README 与 `references/docs/` 中重复的教程、工作流和架构说明；删除不再需要的 `references/docs/` 文档目录。
- 按 2026-08-23 精简重构计划，将 Skill 契约改为语义写作优先：取消固定文件名、固定标题、开篇 300 字和四维度硬门槛。
- 默认输出 `preview`/unified diff 并自动写入；保留引用 key、白名单、备份与回滚保护，`--dry-run` 提供只读模式。
- 新增 `scripts/run.py preview` 与通用变更范围检查；`apply-section` 降级为 legacy 兼容入口。
- 精简配置与 AI 提示词，支持自定义文件名和标题宏。
- auto-test-skill A/B 轮优化：无唯一目标不再回退固定路径；统一 realpath/白名单校验；preview 对结构命令返回非零并提示缺失 bibkey；修复 coach/review/HTML 的旧四小节引导；Tier2 分块改为不依赖标题宏。
- 新增 `tests/test_semantic_boundaries.py`，覆盖目标解析、结构 diff、正文-only diff 和引用守护。

## [1.0.0] - 2026-02-24

### Changed
- `config.yaml`：版本号 `0.7.9 → 1.0.0`，标记为正式稳定版本

## [0.7.9] - 2026-02-22

### Added
- 第三方约束（瘦身提质）诊断预警：预估页数（经验估算）、核心文献数（去重 cite keys）、开篇 300 字信号检查（启发式）

### Changed
- 配置兜底字数调整为 9000±800，并新增 `constraints.*` 约束区间（页数/字数/文献数量/开篇长度）
- `test-session` 将 pytest/python 缓存隔离到会话目录，保证测试中间产物可追溯且集中收口

## [0.7.8] - 2026-02-17

### Added
- 科学问题与科学假设写作要点参考文档（用于“瓶颈→约束→问题→假设”的闭环自检）

### Changed
- 信息表与写作教练：强化“科学问题≠研究目标”“假设不写验证方式”“瓶颈→约束映射”提示
- 信息表生成标题去年份化（避免时间敏感硬编码）
## Unreleased

- runs/cache 默认收敛到任务级 `.bensz-api/task-.../nsfc-justification-writer`。
