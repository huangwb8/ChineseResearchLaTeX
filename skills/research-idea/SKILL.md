---
name: research-idea
description: 当用户提供研究资料、项目背景、实验结果、论文草稿、PR/仓库信息或自然语言线索，希望在文献调查基础上提出科学问题、凝练可证伪假设、寻找创新点或判断研究想法价值时使用。⚠️ 不适用：用户只需要完整实验方案/分析计划（优先 research-plan）、只要写文献综述正文（优先 research-literature-review）、或只要不需要文献依据的普通头脑风暴。
---
# Research Idea

## 目标

把资料转化为可追溯的研究脉络 map 和科学问题，分开判断科学价值、判断可信度与近期投入，形成可推荐、当前范围内无合格候选或证据不足的结论。候选生成不得脱离前置文献调查，不能由 AI 仅凭资料臆造。

与相邻 skill 的边界：
- `research-topic-extractor`：只负责把资料提炼成可检索主题。
- `research-literature-radar`：先发现并筛选经典、前沿和重要论文，形成候选文献池。
- `research-literature-interpretation`：逐篇解读入选论文，提取问题、机制、证据、边界和可迁移启发。
- `research-literature-review`：负责 Premium 查新和证据综述。
- `parallel-vibe`：负责默认 3 轮串行独立审查与打磨。
- `research-plan`：在已有科学问题和假设后，才用于实验设计或分析计划。

## 流程

### 输入

- 必需：任意资料或信息，如文本、文件、文件夹、URL、论文线索、实验现象、代码仓库或 PR 背景。
- 可选：
- 输出路径：用户指定时遵从；未指定时放在 `./docs/ideas/`。
- 工作区：用户指定时遵从；未指定时为当前工作目录下 `.bensz-api/task-{yyyymmdd-hhmm}-{简短描述}/research-idea/`。
- 轮次：默认 3 轮；用户指定时遵从。

### 执行步骤

#### 初始化与资料归纳

1. 先读 [运行说明](references/runtime-guide.md)，核对 `config.yaml.dependencies.kernel` 的环境要求。直接用 `bsk workspace init --task-root` 复用本轮已声明任务目录，再用 `scripts/init_workspace.py` 初始化研究参数和候选空模板、`bsk state transition --skill-root` 进入 literature。已有任务按运行说明读取 Kernel 快照与来源恢复。
2. 读取资料，在现有输入摘要中说明目标研究贡献、服务的问题或决策，以及时间与资源约束。资源区分已具备、明确没有、尚不清楚；源码没有某能力不等于团队无法建设。目标未说明时给出暂定解释，只有不同解释会改变主线选择时才澄清。只保存脱敏摘要和必要引用。
3. 用 `research-topic-extractor` 生成主题、5-10 个英文关键词、2-5 个核心问题；保存为本 Skill 的 `input/theme.json`（引用主题提取 Skill 的原始产物），字段为 `topic`、`keywords`、`core_questions`。

#### 文献调查与解读（候选生成前置）

1. 调用 `research-literature-radar`，根据 `input/theme.json` 获取领域内重要、经典、前沿和具有启发性的论文。优先获取公开 PDF 正文；若无法获得 PDF，允许使用题目、摘要和可核验元数据，但必须标记证据深度不足。
2. 将雷达结果及其 provenance 保存到本任务 `research-literature-radar/output/`，至少记录论文稳定 ID、题目、年份、来源、PDF/摘要可用性、入选理由和未覆盖风险。雷达失败或没有达到最低证据量时，不得直接生成候选，应先报告并停止后续依赖步骤。
3. 对入选论文调用 `research-literature-interpretation`，采用并行子 agent 分批执行：
   - 一个子 agent 只负责一篇论文，独立读取该论文的 provenance 与可用正文/摘要，并将结果写入本任务 `research-literature-interpretation/output/` 下独立的论文目录。
   - 同时运行的解读子 agent 最多 3 个（不含负责调度与汇总的主 agent）；入选论文超过 3 篇时按批次排队，上一批全部完成（或记录失败）后再启动下一批。
   - 本阶段不再嵌套启动额外的并行解读 agent；若单篇需要补证据或定向复核，由该子 agent 在自身任务内完成，不能突破全局并发上限。
   - 主 agent 汇总所有成功解读，并保留每篇论文的失败/证据不足状态；任何论文未完成时不得把研究脉络 map 标记为完整。
   - PDF 可用时优先基于全文；只有摘要时，解读必须收缩到摘要支持的范围，不得补写全文结论。
4. 主 Agent 基于全部解读建立本 Skill 的 `output/research-map.md`，先读 [研究综合指南](references/research-synthesis.md)。主体包含研究线比较表、关系与演化说明、带稳定 O 编号的研究机会清单，并保留时间线与论文 R 编号锚点。区分有来源的关系与待验证综合判断；不能把时间先后、相似术语或不同测量结果写成继承、因果或矛盾。没有争议也可从重要未测量现象与适用边界提出问题，不编造冲突。缺少关键证据时定向补读。

#### 初始候选与低成本价值筛选

将用户摘要、主题、文献证据与 map 作为共同事实，调用 `parallel-vibe`，默认 `n=3`，由独立 agent 提出初始候选。首轮不提供预定最佳方向或优先级，也不互读草稿。按问题选择现象、测量、机制边界或决策等不同角度，不固定套用角色。综合检查研究对象、解释或预期贡献是否实质不同，去重并保留分歧与淘汰理由。

初始探索数量遵循 config 的 min/max_candidates；最终保留数量另行决定，可以只有一个或为零。按 [研究综合指南](references/research-synthesis.md) 和 [报告模板](references/report-template.md) 表达每个候选；报告保留模板的字段名与章节名，每项用短句或 O/R 引用减少重复，不合并标签或自创同义标题：
- 具体科学问题、可证伪假设、关键预测和反证路径；观察应能区分可能答案，不只写效果更好。
- 价值与非平凡性：成功增加什么知识或改变什么决策，失败排除什么解释，常规解释和简单方法为何尚不足。
- 创新性与颠覆潜力：相对最近邻工作的概念增量；若成立会改写什么机制理解、理论框架、测量范式或决策，若失败会排除什么重要解释；为什么不是换对象、换数据、加参数或组合方法。
- 最近工作与实质增量：新条件检验什么重要边界，不能只强调对象、参数或组合没有出现过。
- 最强替代方向、推翻优先级的条件；分开写判断可信度与近期投入。
- 脉络依据：稳定的 O 机会编号与 R 论文锚点，能够回到 map 与原证据。

昂贵查新前判定保留、实质重构、工程事项或淘汰。假设由定义保证、收益仅是增加信息/预算、方法名掩盖缺失机制、无意义的场景迁移、成功失败均无知识增量时优先重构或淘汰。简单方法获胜、复现和负结果仍可有价值，但须说明重要问题与证据。

全部不合格时，判断原因在候选构造还是 map 证据。以新证据或新解释角度最多重新探索一次（config.max_reexplorations，用户明确预算优先），不能仅改名；仍无合格项则评估淘汰结论。资料不足保留 insufficient，不把未执行工作当作无合格候选。

#### 逐对查新与最近工作比较

只有通过价值筛选、拟作为研究方向保留的候选进入完整 Premium 查新：
1. 调用 `research-topic-extractor`，将该候选主题、关键词、核心问题写入 `candidates/Cx/theme.json`。
2. 调用 `research-literature-review`，档位仍固定 `Premium`；在同一任务根中按依赖 Skill 边界归档，并在 `novelty/Cx/` 记录相对来源。复用本轮精读与来源定位，不擅自降低依赖的交付标准。
3. 按 [查新指南](references/novelty-check.md) 核对问题/假设是否已被等价回答，以及新增条件能否改变已有认识；优先比较最可能否定新意的近邻工作。
4. 保存 `novelty/Cx/novelty-decision.json`，包括执行状态、已有答案、剩余未知、差异意义、未确认等价性和处理决定。直接近邻全文受限时结论为未定；未完成方向只能作为探索线索。实质改写问题/假设后重新查新。

已充分研究不能凭协议更齐全或措辞更宏大保留；重要复现若形成不同的研究问题，重新论证并查新。价值筛选已足以淘汰的候选记录依据和未执行查新的原因，不伪造 Premium 执行记录。零候选仍保留 candidates 与 novelty 证据角色，后者说明淘汰所依据的既有证据、哪些无需查新及原因。

#### 多轮独立审查

用 `parallel-vibe` 执行 config 约定的外层串行轮数与每轮独立人数，默认均为 3；不得用一次调用冒充多轮。每轮使用上一轮事实修正和汇总，但不要求接受上一轮推荐。具体任务见 [审查参考](references/agent-review-prompt.md)：
- 第一轮挑战选题价值：成功是否值得做、平凡解释、最强替代方向。
- 第二轮检查解释与辨别能力：定义性假设、关键反例、强基线、实质重构。
- 第三轮重新选择与迁移检查：最强备选、选择敏感性、外推边界、最终去留。

每轮只记录新增发现、对候选的影响、未决分歧和证据；草稿可不变，但字节一致不构成新的科学审查。各 agent 独立读证据，主 Agent 按论证和反例综合，不以多数票替代判断。需补读、重构或重新生成时回到相应步骤，不能仅追加免责声明。零候选仍按约定轮次复核淘汰的充分性、遗漏替代方向及重启条件。

用户减少轮次时，将三类判断合并分配到实际轮次；增加轮次时针对前轮未解问题继续审查，不编造执行记录。不自动缩减轮数或提高人数。

#### 分开选择科学价值与近期投入

分别给出科学价值优先级、判断可信度和近期投入建议；保留并列、不同意见及资源变化后的选择。不得设置可用高可行性抵消低科学价值的加权总分。低价值但易做的事项可列工程建议，高价值但条件不足的方向保留条件性定位。

形成以下业务结论：`recommended`（价值论证成立，保留候选完成必要查新和审查）、`no_qualified`（证据足以淘汰当前候选，已完成约定探索与复核）、`insufficient`（输入、文献或必要执行未完成）。没有合格候选仅针对当前评估范围，不能声称全领域无题可做。

#### 写最终报告并验证

按 `references/report-template.md` 写最终 Markdown。写完后运行：

```bash
python3 research-idea/scripts/validate_report.py --report "{最终报告路径}"
# 系统级安装后也可使用：
python3 ~/.codex/skills/research-idea/scripts/validate_report.py --report "{最终报告路径}"
python3 ~/.claude/skills/research-idea/scripts/validate_report.py --report "{最终报告路径}"
```

报告采用 `config.output.report_contract` 的显式结论和执行状态，开头一页以内说明问题、价值、证据链、最近工作差异与确定程度。校验失败先修复；insufficient 也保留“查新摘要”“风险与下一步”“证据缺口与恢复位置”，不能将它们合并为自由标题。正式结论须经阶段就绪 Verifier、科学假设价值 Verifier 与 bsk Gate 核验并到达 completed 才能宣称完成；insufficient 可交付明确标识的阶段性评估，保留当前状态、缺口和恢复位置，不能进入 completed。结构通过不认证科学价值或新颖性。

### 输出

最终交付一个 Markdown 文件。未指定输出目录时，写入当前项目的 `./docs/ideas/`；默认命名为：

```text
Research-Idea_{github仓库名}_{pr名}_{时间戳}.md
```

完整默认路径为 `./docs/ideas/Research-Idea_{github仓库名}_{pr名}_{时间戳}.md`。用户显式指定输出目录或文件名时遵从，但不得将正式报告放入隐藏工作区。

如果无法识别 GitHub 仓库名或 PR 名，使用当前目录名与当前分支名；仍无法识别时分别使用 `repo` 与 `manual`。

报告必须包含：
- 文献调查摘要与证据深度说明。
- 研究脉络 map 的时间线、研究线、关键转折和知识缺口摘要。
- 保留候选及独立价值判断；零候选给出范围、淘汰依据、重新探索结果与重启条件。
- 科学价值与近期投入两种排序及最强替代方向；证据不足时给出缺口和恢复位置。
- 查新摘要、证据缺口、可证伪路径和最小下一步。

报告不得暴露 `.bensz-api/task-{yyyymmdd-hhmm}-{简短描述}/research-idea/`、`tests/research-idea/`、`parallel-vibe/`、`.parallel-vibe/`、`.parallel_vibe/`、`@main/summary.md`、manifest 或其他中间产物路径。

### 输出管理

本 Skill 的新任务中间文件统一写入 `./.bensz-api/task-{yyyymmdd-hhmm}-{简短描述}/{skill名}/input|output|log/`。同一任务复用一个任务根目录；多 Skill 协作才创建 `shared/`。正式交付物不写入该目录，历史隐藏目录只允许显式兼容读取、迁移或清理。

- 默认工作区：`{cwd}/.bensz-api/task-{yyyymmdd-hhmm}-{简短描述}/research-idea/`。
- 所有中间文件、查新记录、并行审查产物、草稿和日志都必须保存在隐藏工作区内；除最终 Markdown 外，不要写到项目根目录或 `docs/ideas/`。
- 用 `--task-root` 显式复用本轮任务根，必须位于项目内 `.bensz-api/task-*`；旧 `--workspace-dir` 嵌套布局只保留历史文件，不自动迁移。输出目录不得位于隐藏工作区内。

初始化分为 bsk 工作区准备和领域资料初始化，命令与参数见 [运行说明](references/runtime-guide.md#初始化与阶段)。脚本只生成输入参数、候选空模板和正式报告路径，不管理状态或事件；用户指定审查轮数和人数时保留其设置。

### 校验

- 测试源码位于仓库 `tests/research-idea/`，测试材料和运行日志放本轮工作区的 output/log，最终报告不引用测试路径。
- 普通业务不创建测试区；开发验证材料写本轮工作区，不通过业务初始化脚本创建测试目录。

- 科学问题必须是问题，不是主题名。
- 假设必须可证伪，不写无法被推翻的价值判断。
- 查新结论必须区分“没有研究过”和“研究过但缺口仍在”。
- 拟推荐候选不得因成本高而跳过 Premium；价值筛选淘汰的事项明确记为未执行，不冒充查新通过。
- 不把文献综述正文当作最终输出；最终输出是研究想法报告。
- 不泄露隐藏工作区、中间文件、agent 内部指令或测试路径。

### 失败与恢复

保留错误证据和已完成产物；按运行说明读取 Kernel 领域快照、事件和原参数恢复。证据修复或契约变化后使用新 attempt；前置证据改变时核验返工并回到受影响阶段，下游结论由 Agent 标为待复核。取消记录原因并停止推进；Kernel 缺失或不可用时保留草稿与缺口，不宣称阶段通过。

## 控制

使用前读取 [运行契约与命令](references/runtime-guide.md)。`runtime` 声明 State 与 required Verifier；[State 索引](references/states/index.json) 与 [Verifier 索引](references/verifiers/index.json) 维护各自身份和版本。

- 五个 State 只定义阶段、图边和 bsk 原生不变量；阶段就绪 Verifier 按 [阶段契约](references/verifiers/stage-readiness/VERIFIER.md) 判断下一阶段是否就绪，科学假设价值 Verifier 按 [价值契约](references/verifiers/hypothesis-merit/VERIFIER.md) 判断拟推荐或拟淘汰结论是否经受创新性、非平凡性和颠覆潜力审问。
- 主 Agent 实际读取来源，按运行指南直接调用 Kernel API 获取全部 required handoff、回传判断并批量记录 Gate。然后使用相同 run/attempt 调用 `bsk state transition --skill-root`；检查 JSON status，而非只看退出码。
- 全部 required 结果完成且 pass 才允许对应转移；fail/uncertain/unchecked/error/timed_out/skipped 均不前进。科学充分性、角色覆盖、轮次独立性、假设价值及源/目标匹配由 Agent 判断，报告格式由 validate_report 检查。
- bsk 负责协议、结果绑定、Gate、事件和状态；不在 Skill 增加运行时包装、锁、快照或重放引擎。可按需使用内置文件/路径/引用 Verifier，不能替代科研判断。
- Kernel 不自动发现全部证据文件变化。Agent 在转移前核对最新来源；变化后新建 attempt 并重审，旧回传不能重新绑定。人工复核提供新增证据，不提供强制通过开关。

## 约束

遵守以下公共约束，并执行本 Skill 的专属边界。

### 公共硬约束

- 任务需要落盘时，使用唯一的 `./.bensz-api/task-{yyyymmdd-hhmm}-{简短描述}/` 根目录；共享材料放入 `shared/`，Skill 专属材料放入该 Skill 的 `input/`、`output/`、`log/`。
- 正式交付物、源代码和正式计划按项目约定保存，不写入任务工作区；未经授权不覆盖、删除、迁移或远程写入。
- 项目维护变更检查 BAC 可用性并记录需求、AI 产出、工具结果、文件改动和验证摘要；BAC 只做过程审计，不替代署名、责任或合规判断。
- 不记录 API Key、访问令牌、密码、Cookie、环境/凭据文件、私有 Prompt、身份信息、本地用户名、主机名或不必要的大体积原始数据。
- 文件路径必须规范化并限制在授权项目范围内；外部 URL、子进程和网络访问遵循最小权限，防止路径遍历、SSRF 和命令注入。
- Skill 版本唯一记录在自身 `config.yaml:skill_info.version`；公开 API、协议、目录或配置变更同步文档与 `CHANGELOG.md`。
- 仅将 Skill 或 Bensz 基础设施本身的设计缺陷交给 `bensz-collect-bugs`；先脱敏写入 `~/.bensz-skills/bugs/`，当前任务不中断，只有用户明确要求才公开上报，禁止直接修改用户已安装的 Skill 源码。
<!-- End of canonical common constraints. -->

### Skill 专属约束

不得超出本 Skill description 和上方流程所声明的范围；不将未验证的信息伪装成确定结论。
