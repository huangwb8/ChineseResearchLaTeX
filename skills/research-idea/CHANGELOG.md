# Research Idea 变更日志

本文档记录 research-idea skill 的所有重要变更。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)。

## [Unreleased]

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
