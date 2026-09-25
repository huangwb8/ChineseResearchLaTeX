# Research Idea 变更日志

本文档记录 research-idea skill 的所有重要变更。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)。

## [Unreleased]

### Added

- `0.15.0`：工作 map 增加研究线关系、最强反例与辨别证据的综合要求；正式摘要改为向新读者解释对象、已有答案、边界与 O 机会的论证路径，并加入保真语义复核。
- `0.14.0`：按 v19 证据闭环计划为 `stage-readiness` 增加 required 确定性 evidence-consistency 组件；论文解读、全文源和独立 reviewer 使用版本化执行回执并与源 artifact 对账。
- `0.13.0`：按 v18 审计闭环计划把业务索引哈希交给 BSK 的 evidence binding、Gate 和 transition 重放；Skill 仅保留四条前向边 applicability 与 reviewer thread/done/RESULT 回执对账。移除重复 BSK 的本地 completion contract/attestation 实现。

### Changed

- `0.15.0`：报告契约升级为 `research-idea-report-v3`，默认采用 GB/T 7714—2025 顺序编码引注、`reference_map` 和末尾 `## References`；报告校验检查编号、链接、映射和基本书目形态。v2 R 锚点报告只读兼容，不取得新运行完成资格；指定样式需声明来源并由宿主 AI 复核。同步中英文指南、模板和回归。
- `0.14.1`：将共享领域规则模块从 Skill 根目录迁入 `scripts/edge_rules.py`，同步运行快照、嵌套 Verifier 与回归导入；压缩 `SKILL.md` 的重复说明并新增中英文对齐的用户指南，运行与科研判断契约不变。
- 完成证据升级为 `research-idea-completion-v6`；四条前向边的 verifier result、Gate 与 transition 绑定同一 evidence artifact，最终阶段绑定完成索引并以 BSK 查询接口重放。v2–v5 与 legacy-unbound 现场只读保留。
- 运行声明迁移到 `runtime.kernel` 与 strict-v2 identity policy；启动改用固定托管 BSK diagnostics/capabilities 和原子 `workspace initialize`。论文解读改为按论文隔离任务，只有可对账的 host-agent receipt 才声明独立 agent 身份。
- 移除对 `research-literature-review` 的运行依赖，改为直接调用 `research-literature-search` 生成候选级 `rls.v1` bundle；新颖性、等价性、反方证据和决定性近邻判断继续由本 Skill 结合 Radar 与 Interpretation 完成。
- 完成证据契约升级为 `research-idea-completion-v5`，要求记录候选级查询与 canonical 候选哈希、数量、Search 状态和全量消费状态；v2–v4 仅保留历史读取。
- 删除当前流程与报告中的 Review `Premium` 档位要求，并同步 README、状态说明、运行指南、模板、校验和回归测试。

- `0.11.0`：候选生成同时消费 Radar 核心精读与覆盖全部 Search canonical 候选的辅助 landscape；查新改用 Review `novelty-check`，按风险升级决定性近邻，不再以篇数、多源或全文作为普遍充分性代理。
- `bensz.research.stage-readiness` 升至 4.0.0，分开返回 `pipeline_ready`、`scientific_evidence_sufficient` 与 `claim_eligible`；允许带已披露缺口进入独立审查，但 completed 必须三项均为 true。`bensz.research.hypothesis-merit` 升至 1.1.0，以 `applicability` 防止完成流程消费不适用回执。
- 核对当前托管 BSK 后确认尚不支持 action-specific required Verifier，故保留全局 required 兼容路径；按项目 latest 约定删除 `dependencies.kernel.version`、旧式 `runtime.kernel` 精确绑定和静态 `required_capabilities` 声明，启动时继续按实际 capability 检查。

- `0.10.0`：按 bac-v15 计划接入 BSK 2.1.1 原生身份生命周期。新增原子 `start_workflow.py`，统一环境/capability 预检、v2 literature 身份、领域资料和运行快照；`phase_entry.py` 增加阶段 start/finish/retry，消费 State-bound action authorization、为每个目标 State 创建新 visit/attempt，并支持同 visit attempt supersede。完成收敛改按 source/target identity 链核对授权、Gate 与转移，completion-v4 要求 completed 权威身份及 thread/runner 完成回执；legacy 现场只读 fail-closed。

- `0.9.1`：按 bac-v14 阶段身份计划修复 Kernel 2.1.0 直线流程。首次进入 literature 必须携带非空 run/attempt；`phase_entry.py` 从 BSK 事件投影取得当前 State 权威进入身份，按 action 隔离 Gate 幂等键并复核目标快照。由于 Kernel 尚无 State visit/attempt 轮换接口，失败重试、换 attempt、回退与无身份旧现场显式 fail-closed；完成检查新增首个控制断点诊断。

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
