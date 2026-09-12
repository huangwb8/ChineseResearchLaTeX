# Research Idea 变更日志

本文档记录 research-idea skill 的所有重要变更。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)。

## [Unreleased]

- `0.9.0`：新增轻量 `scripts/phase_entry.py`，把四条前向阶段边收敛为一个不易漏用的入口。脚本通过 BSK API 读取当前 State、按 Skill 声明执行全部 required Verifier、返回 BSK 原生 handoff、由 Kernel 计算 Gate，并仅在 Gate allow 后调用 BSK transition；不自建 State/Gate、attempt 生命周期、handoff/provenance 协议或事件账本。`check_completion.py` 继续作为绕过入口时的独立完成收敛防线。

- 新增 `scripts/check_completion.py` 完成证据收敛检查：在交付 recommended/no_qualified 前核对报告结构、自定义文件名 manifest、bsk meta-state、completed Gate、依赖 Skill 可复核产物和约定独立审查轮次；新增 `completion-evidence.json` 索引契约，版本推进至 0.7.1。缺少 Gate、依赖产物或审查证据时只能作为阶段性结果交付，不追认旧运行。
- 清理 Skill 包内过期测试入口，`skills/research-idea/tests` 不再引用已移除的 `idea_runtime.py` / `phase_evidence.py`，与仓库级当前 Kernel 集成回归保持一致。

- 新增 required `bensz.research.hypothesis-merit` 语义 Verifier，与阶段就绪 Verifier 一起批量记录 Kernel Gate；推荐候选必须接受科学假设价值、创新性、颠覆/改写潜力、非平凡性、关键预测和最强替代方向审问。报告模板和格式检查新增“创新性与颠覆潜力”字段，版本推进至 0.7.0。

- `research-idea` 轻量化：保留五个 Markdown State 与本地语义 Verifier，直接使用 bsk 原生状态不变量、Gate、绑定与日志；移除自建运行时、机械证据脚本和重复快照/重放逻辑，精简领域初始化。最低 Kernel 要求移至 dependencies.kernel，以兼容原生声明加载器。同步操作指南、报告质量与直接 Kernel 集成回归。旧专用 CLI 不兼容，旧运行只读保留；证据内容变化后的重审由 Agent 负责。

## [0.5.0] - 2026-09-10

### Changed

- 建立研究目标、跨论文比较/关系/机会 map 与稳定 O/R 引用；低成本价值筛选先于保留候选的 Premium 查新，明确实质增量与最强替代方向，分开价值、可信度和近期投入。
- 三轮分别挑战价值、检查解释辨别能力、重新选择与迁移；保留默认人数、轮数及查新档位，允许有边界的一次重新探索和零候选结论。
- 报告 v2 显式声明 recommended/no_qualified/insufficient 与执行状态；允许一个或零个保留候选，阶段性评估不能通过完成检查。初始化生成空候选池及独立示例。
- 同步既有阶段和 Verifier 业务判据；变更判据的 Pack 使用新主版本，原状态图、Kernel 依赖及绑定/恢复机制不扩展。

### Fixed

- 支持中文候选及 C 编号标题；检查实质字段、重复编号、O/R 引用定位，旧报告继续结构读取并明确无法用于新运行完成。

### Validation and compatibility

- 补齐仓库 tests/research-idea 回归；新旧固定证据输出比较只用于初步问题发现，未以模型自评替代领域确认，也未宣称完整科研质量验收。
- config 为 Skill 版本来源。旧报告与旧事件不改写，新资产不能续写旧运行；需新任务重新核验。正式源码仅更新仓库副本，未安装到系统目录。


### Added

- `0.4.0`：新增 Skill 自有阶段证据混合 Verifier、五阶段 State Pack、Kernel 1.0.3 精确消费声明及 `idea_runtime.py` 宿主。required 机械检查和绑定的语义回传均通过才推进；支持证据快照、运行/尝试绑定、回退失效、取消和事件重放。
- 新增定向回归与运行指南；覆盖缺失证据、不确定性、跳阶段、错绑/过期回传、内容变化、路径边界、复制安装与原报告 CLI。

### Fixed

- 修复报告标题后不留空行时章节正则吞掉正文首行的问题；共享结构检查支持相对用户项目边界，避免外层临时工作区造成误报，仍拒绝项目内部隐藏交付路径。

### Compatibility

- 受控初始化需要匹配的 Kernel 和 POSIX 文件锁；新增 `--task-root` 复用已声明任务目录，旧 `--workspace-dir` 布局拒绝新写入且不自动迁移。`validate_report.py` 独立 CLI 保留，但不能替代状态流完成。

### Changed

- `0.3.2`：论文解读阶段改为并行子 agent 分批执行；每篇论文一个 agent，同时最多 3 个，超出部分排队，禁止嵌套并行，并要求主 agent 汇总失败与证据不足状态。
- `0.3.1`：统一文献雷达与论文解读的任务工作区子目录为 `research-literature-radar/` 与 `research-literature-interpretation/`，避免 Skill 名称与产物路径脱节。
- `0.3.0`：重构候选生成流程，新增 `research-literature-radar` 与 `research-literature-interpretation` 前置阶段；要求先形成带论文锚点的研究脉络 map，再由多个独立 agent 基于 map 生成初始候选。
- 同步更新 `config.yaml`、`init_workspace.py`、README 与报告模板，增加文献雷达、论文解读和研究脉络 map 的中间产物目录及输出要求。
- 默认最终报告目录由项目根目录调整为 `./docs/ideas/`；`init_workspace.py`、`config.yaml` 与 README 示例同步更新。
- `SKILL.md` frontmatter `description` 聚焦触发条件与能力边界，移除具体 `Research-Idea_*.md` 文件名；文件名模板保留在输出规范中。

- `config.yaml`：版本号 `0.2.0 → 0.2.1`；最终报告泄露校验新增 `.parallel-vibe/` 禁止路径，兼容 `parallel-vibe` 默认工作区目录变更。
- 本轮补丁版本推进至 `0.2.2`，用于记录默认报告目录与触发描述调整。
- `SKILL.md` / `scripts/validate_report.py`：同步最终报告不得暴露 `.parallel-vibe/` 中间产物路径。
- 依赖口径迁移为 `research-topic-extractor` 与 `research-literature-review`。
- 依赖检查脚本增加旧名 fallback：`get-review-theme`、`systematic-literature-review`。
- README 与 SKILL 文档同步更新相邻 skill 边界说明。

## [0.1.0] - 2026-06-14

### Added

- 初始化 `research-idea` skill：根据用户资料提出多个关键科学问题与可证伪科学假设。
- 新增隐藏工作区规范：默认 `.research-idea/run-{timestamp}/` 保存全部中间文件，最终报告不泄露中间路径。
- 新增依赖协作流程：使用 `get-review-theme` 提取查新主题，使用 `systematic-literature-review` Premium 档查新，使用 `parallel-vibe` 默认 3 轮串行独立审查。
- 新增 `scripts/init_workspace.py`：初始化隐藏工作区、测试区、运行清单和默认输出路径。
- 新增 `scripts/validate_report.py`：验证最终 Markdown 文件名、必需章节、问题-假设对数量、可证伪表述和中间路径泄露。
- 新增 `scripts/check_dependencies.py`：检查 `get-review-theme`、`systematic-literature-review` 与 `parallel-vibe` 是否可发现，依赖缺失时早失败。
- 新增 `references/report-template.md`、`references/novelty-check.md` 与 `references/agent-review-prompt.md`，分别规范最终报告、查新判定和独立审查输入。
- 新增 `README.md` 与 `config.yaml`：提供用户使用指南、WHICHMODEL 初始建议、默认目录、依赖、轮次、输出和校验规则。

### Changed

- 强化默认 3 轮口径：明确 `rounds=3` 为外层迭代轮数，每轮使用 `parallel-vibe --n 3` 进行独立审查。
- 强化最终报告校验：要求至少 3 个候选、每个候选包含关键预测/反证路径/查新结论，查新摘要必须说明 Premium 档，最佳方案必须包含多维选择理由。
- 收紧中间文件隔离：`parallel-vibe`、查新产物、manifest、agent review 和草稿均限定在隐藏工作区内，最终报告不得泄露内部路径。
- 使用 `compact-bensz-skills` 压缩工作型 Markdown：`SKILL.md` 从 188 行降至 165 行，工作型 Markdown 总词数减少 302，压缩校验 0 error / 0 warning。
## Unreleased

- 测试目录默认改为项目 `tests/research-idea`，与任务级运行工作区分离。
- 全面优化：引入 `artifact_ready`、`execution_recorded`、`evidence_sufficient`、`claim_eligible` 四层完成语义及 `bounded_recommendation`/`degraded` 降级状态；新完成证据索引支持 run/attempt 绑定、内容快照和 authoritative attempt 校验。
- 强化 Premium 查新和论文解读契约：要求稳定来源、证据深度、读取范围、多源/全文/等价性门禁；并行审查需记录 thread、模型、输入/输出快照和执行时间，`synthetic_review` 不计入独立审查。
- 同步 State/Verifier 运行说明与报告模板，明确依赖故障、科研前置条件不足和 BAC 本地完整性边界不得认证 completed。
