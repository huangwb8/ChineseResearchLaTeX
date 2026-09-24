---
name: research-idea
description: 当用户提供研究资料、项目背景、实验结果、论文草稿、PR/仓库信息或自然语言线索，希望在文献调查基础上提出科学问题、凝练可证伪假设、寻找创新点或判断研究想法价值时使用。⚠️ 不适用：用户只需要完整实验方案/分析计划（优先 research-plan）、只要写文献综述正文（优先 research-literature-review）、或只要不需要文献依据的普通头脑风暴。
metadata:
  author: Bensz Conan
  keywords: [research-idea, scientific question, falsifiable hypothesis]
---
# Research Idea

## 目标

从用户资料与可审计文献证据中建立研究脉络，提出科学问题和可证伪假设，分开判断科学价值、可信度与近期投入，形成有界推荐、当前范围内无合格候选或证据不足结论。候选必须来自前置调查，不得仅凭资料臆造。

相邻 Skill：`research-topic-extractor` 提取检索主题；`research-literature-search` 生成 `rls.v1` 候选与 provenance；`research-literature-radar` 建立全量 landscape；`research-literature-interpretation` 逐篇解读；`parallel-vibe` 独立审查。完整综述使用 `research-literature-review`，实验/分析计划使用 `research-plan`。

## 流程

### 输入

- 必需：文本、文件/目录、URL、论文线索、实验现象、仓库或 PR 背景中的至少一种。
- 可选：研究目标、时间/资源边界、输出路径、审查轮数和人数。
- 默认报告目录：`./docs/ideas/`；默认任务区：`./.bensz-api/task-{yyyymmdd-hhmm}-{简短描述}/research-idea/`。
- 默认审查 3 轮、每轮 3 人；论文解读最多并行 3 个任务。

### 执行步骤

1. **启动与归纳。** 阅读 [运行说明](references/runtime-guide.md)，锁定任务目录，只用 `scripts/start_workflow.py` 建立 BSK 身份；仅当 `status=initialized` 且 run/visit/attempt 非空时开始 literature 阶段。摘要目标贡献、服务的问题/决策和资源状态，只保存必要的脱敏内容。用 `research-topic-extractor` 生成主题、5–10 个英文关键词、2–5 个核心问题，并在 `input/theme.json` 引用原始产物。

2. **文献证据。** 用 `research-literature-radar` 消费 Search manifest 和全部 canonical 候选，生成逐条覆盖的 landscape 与 hash/计数摘要；未全量对账或 hash 漂移时停止。对入选论文调用 `research-literature-interpretation`：一任务一论文、最多并行 3 个、不嵌套；只有可对账的宿主回执才称“独立 agent”。全文优先，只有摘要时收缩结论；记录稳定来源、证据深度/范围、问题、方法、结果、限制和支持/反驳关系。

3. **研究 map。** 按 [研究综合指南](references/research-synthesis.md) 写 `output/research-map.md`，包含研究线比较、landscape 覆盖、关系/演化、稳定 O 机会编号、R 核心论文锚点和 Search record ID。来源关系与“待验证综合判断”分开；时间先后、术语相似或测量差异不自动证明继承、因果或矛盾。

4. **生成与筛选候选。** 以用户摘要、主题、证据和 map 为共同事实，用 `parallel-vibe n=3` 独立生成候选；首轮不预设最佳方向，agent 不互读草稿。初始探索 3–7 个，最终可保留一个或零个。按 [报告模板](references/report-template.md) 写问题、假设、关键预测、反证、价值/非平凡性、创新/颠覆潜力、最近工作增量、最强替代方向、可信度、投入和 O/R 依据。定义性假设、无知识增量、方法名代替机制或无意义场景迁移优先重构/淘汰。全部不合格时最多用新证据或新解释重新探索一次；资料不足保持 `insufficient`。

5. **候选级查新。** 对每个拟保留候选生成 `candidates/Cx/theme.json`，围绕直接近邻、等价假设、反方证据和适用边界提出 5–25 条查询，调用 `research-literature-search` 生成独立 `rls.v1` bundle。逐条消费 canonical 候选，按 [查新指南](references/novelty-check.md) 保存 `novelty/Cx/novelty-decision.json`。摘要可排除明显不等价工作；决定新颖性的近邻才升级全文。决定性近邻未核验时可带缺口进入审查，但 `scientific_evidence_sufficient=false`、`claim_eligible=false`。淘汰项记录未执行查新的原因，不伪造结果。

6. **独立审查与选择。** 按 [审查参考](references/agent-review-prompt.md) 串行执行约定轮次，默认依次挑战价值、解释/辨别能力、重新选择与迁移边界。reviewer 必须独立读证据，并有 thread/done/RESULT completed 回执、模型、输入/输出哈希和时间；只有 RESULT、角色化草稿或复述不计入 required review。主 Agent 按论证与反例综合，不按多数票；实质改写问题/假设后重新查新。分别报告价值、可信度和投入，不用可行性抵消低价值。

7. **结论与报告。** 结论只能是 `recommended`、`no_qualified` 或 `insufficient`；`bounded_recommendation`/`degraded` 可阶段性交付但不能 completed。按模板写报告并运行：

```bash
python3 research-idea/scripts/validate_report.py --report "{最终报告路径}"
python3 research-idea/scripts/check_completion.py --project-root . --task-root "{本轮任务根}" --report "{最终报告路径}"
```

自定义文件名时为结构校验增加 `--allow-custom-name`，或让完成检查读取 manifest。保存 `research-idea/output/completion-evidence.json`（schema `research-idea-completion-v6`），绑定依赖产物、论文解读、reviewer、汇总和最终综合。只有 required Verifier、BSK Gate、`completed` 状态和完成检查全通过，才能宣称完成。

### 输出

最终交付一个 Markdown，默认路径：

```text
./docs/ideas/Research-Idea_{github仓库名}_{pr名}_{时间戳}.md
```

无法识别仓库/PR 时用当前目录/分支，仍失败则用 `repo`/`manual`。报告包含证据深度、研究 map、候选或零候选依据、价值/可信度/投入、最近工作、查新、反证、风险和最小下一步；不得暴露隐藏任务区、测试/parallel-vibe 路径、manifest 或内部指令。

### 输出管理

同一任务复用一个 `.bensz-api/task-*` 根；各 Skill 使用独立 `input|output|log`，跨 Skill 材料才放 `shared/`。查新、审查、草稿和日志留在隐藏工作区，正式报告留在用户目录。`--task-root` 必须位于项目内；旧 `--workspace-dir` 布局只读保留，不自动迁移。

### 校验

- 分开核验 `artifact_ready`、`execution_recorded`、`evidence_sufficient`、`claim_eligible`；文件存在或格式通过不证明科学 claim。
- Search bundle 保留 `rls.v1`、查询/canonical hash、数量和全量消费状态；论文解读、全文源与 reviewer 回执可回到源 artifact。
- 拟推荐候选不得跳过多查询查新。关键编码手册、独立真值、标注一致性、审计/伦理前置或 baseline evidence 缺失时，只能给 `insufficient`/`bounded_recommendation`。
- 测试源码位于 `tests/research-idea/`；缓存和日志写任务区。版本只在 `config.yaml:skill_info.version` 维护；接口或目录变化同步 README、CHANGELOG 和测试。

### 失败与恢复

保留错误证据和已完成产物，按运行快照、Kernel 投影、active attempt 与原参数恢复。证据变化或 Verifier 失败时以 `phase_entry.py --mode retry` supersede attempt，再重新授权/审查；旧 handoff、Gate 和授权不得复用。Skill/解释器漂移、legacy 身份、快照损坏、Kernel 不可用或 transition 失败时停止，不补写历史身份或伪称完成。

## 控制

`config.yaml:runtime` 声明五个 State 和两个 required Verifier；索引见 [states](references/states/index.json) 与 [verifiers](references/verifiers/index.json)。`stage-readiness` 判断流水线/证据/claim 就绪度，`hypothesis-merit` 审问创新性、非平凡性与颠覆潜力。BSK 负责身份、绑定、Gate、事件和状态；本 Skill 只保留领域适配。

每阶段先以 `phase_entry.py --mode start` 消费当前 visit/attempt 的 action authorization，再用 `--mode finish` 获取 handoff并提交绑定同一 `evidence_hash`/`evidence_refs` 的 required 结果。全部结果 completed 且 pass 才转移；其它 verdict 留在当前 State。

`scripts/edge_rules.py` 供阶段入口、完成检查和 evidence-consistency 共享：四条前向边的 hypothesis-merit applicability 依次为 `not_applicable`、`applicable`、`not_applicable`、`applicable`。BSK 校验 evidence/Gate/transition 绑定，Skill 对账论文解读与 reviewer 回执。v2–v5 或未绑定 transition 的旧现场只读保留。

## 约束

遵守以下公共约束，并执行本 Skill 的专属边界。

<!-- BEGIN COMMON CONSTRAINTS -->
<!-- Source-Hash: sha256:15120201e9e0c7569517261d57ecefb63ac279c26ed13876f8e95b6dc35854d3 -->
<!-- Template-ID: skill-common-constraints; Template-Version: 1; Sync-Policy: exact-block -->

### 公共硬约束

本块由 `docs/templates/skill-common-constraints.md` 统一维护；每个 `SKILL.md` 的 `## 约束` 必须逐字同步本块，不得在副本中改写公共规则。

- 任务需要落盘时，使用唯一的 `./.bensz-api/task-{yyyymmdd-hhmm}-{简短描述}/` 根目录；共享材料放入 `shared/`，Skill 专属材料放入该 Skill 的 `input/`、`output/`、`log/`。
- 正式交付物、源代码和正式计划按项目约定保存，不写入任务工作区；未经授权不覆盖、删除、迁移或远程写入。
- 项目维护变更检查 BAC 可用性并记录需求、AI 产出、工具结果、文件改动和验证摘要；BAC 只做过程审计，不替代署名、责任或合规判断。
- 不记录 API Key、访问令牌、密码、Cookie、环境/凭据文件、私有 Prompt、身份信息、本地用户名、主机名或不必要的大体积原始数据。
- 文件路径必须规范化并限制在授权项目范围内；外部 URL、子进程和网络访问遵循最小权限，防止路径遍历、SSRF 和命令注入。
- Skill 版本唯一记录在自身 `config.yaml:skill_info.version`；公开 API、协议、目录或配置变更同步文档与 `CHANGELOG.md`。
- `bensz-collect-bugs` 是一个 Agent Skill；仅将 Bensz Agent Skill 或 Bensz 基础设施本身的设计缺陷交给它。先脱敏写入 `~/.bensz-skills/bugs/`，当前任务不中断，只有用户明确要求才公开上报，禁止直接修改用户已安装的 Skill 源码。

<!-- End of canonical common constraints. -->
<!-- END COMMON CONSTRAINTS -->

### Skill 专属约束

不得超出 frontmatter description 和上述流程范围；不得把未验证信息、未执行步骤或阶段性结果伪装成确定结论。
