---
name: research-idea
description: 当用户提供研究资料、项目背景、实验结果、论文草稿、PR/仓库信息或自然语言线索，希望在文献调查基础上提出科学问题、凝练可证伪假设、寻找创新点或判断研究想法价值时使用。先建立研究脉络 map，再由多 agent 生成候选，并通过 Premium 查新和独立审查打磨。⚠️ 不适用：用户只需要完整实验方案/分析计划（优先 research-plan）、只要写文献综述正文（优先 research-literature-review）、或只要不需要文献依据的普通头脑风暴。
---
# Research Idea

## 目标

把任意资料转化为领域文献证据、研究脉络 map，以及多个高价值、可查新、可证伪的“科学问题-科学假设”候选，并选出最值得推进的一对。候选生成不得脱离前置文献调查，不能由 AI 仅凭资料臆造。

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

1. 使用匹配 `config.yaml.runtime.kernel` 的 Python 环境，运行 `scripts/init_workspace.py --task-root "{本轮已声明任务根}"` 创建工作区、manifest 与初始状态；已有事件时用 `scripts/idea_runtime.py ... status` 恢复。首次接入先读 [运行说明](references/runtime-guide.md)。
2. 读取资料，只把摘要、结构化事实和必要引用写入隐藏工作区。
3. 用 `research-topic-extractor` 生成主题、5-10 个英文关键词、2-5 个核心问题；保存为 `theme/theme.json`，字段为 `topic`、`keywords`、`core_questions`。

#### 文献调查与解读（候选生成前置）

1. 调用 `research-literature-radar`，根据 `theme/theme.json` 获取领域内重要、经典、前沿和具有启发性的论文。优先获取公开 PDF 正文；若无法获得 PDF，允许使用题目、摘要和可核验元数据，但必须标记证据深度不足。
2. 将雷达结果及其 provenance 保存到 `research-literature-radar/`，至少记录论文稳定 ID、题目、年份、来源、PDF/摘要可用性、入选理由和未覆盖风险。雷达失败或没有达到最低证据量时，不得直接生成候选，应先报告并停止后续依赖步骤。
3. 对入选论文调用 `research-literature-interpretation`，采用并行子 agent 分批执行：
   - 一个子 agent 只负责一篇论文，独立读取该论文的 provenance 与可用正文/摘要，并将结果写入 `research-literature-interpretation/` 下独立的论文目录。
   - 同时运行的解读子 agent 最多 3 个（不含负责调度与汇总的主 agent）；入选论文超过 3 篇时按批次排队，上一批全部完成（或记录失败）后再启动下一批。
   - 本阶段不再嵌套启动额外的并行解读 agent；若单篇需要补证据或定向复核，由该子 agent 在自身任务内完成，不能突破全局并发上限。
   - 主 agent 汇总所有成功解读，并保留每篇论文的失败/证据不足状态；任何论文未完成时不得把研究脉络 map 标记为完整。
   - PDF 可用时优先基于全文；只有摘要时，解读必须收缩到摘要支持的范围，不得补写全文结论。
4. 基于全部解读建立 `research-map/research-map.md`（或等价结构化文件）。研究脉络 map 必须呈现：时间顺序、关键问题演化、代表性方法/机制、证据转折、争议与失败边界、尚未闭合的知识缺口、不同研究线之间的连接，以及每个判断对应的论文锚点。它是候选生成的必需输入，不是最终报告中的装饰性综述。

#### 基于研究脉络 map 的初始候选

将用户资料摘要、`theme/theme.json`、研究雷达摘要、论文解读摘要和 `research-map` 作为共同背景，调用 `parallel-vibe` 一次性启动多个独立 agent 进行初始 brainstorming；默认使用 `n=3`，用户可指定数量。各 agent 必须独立提出并论证候选，不得互相读取草稿或把同一候选改写成多个版本。汇总时去重并保留分歧，最终形成 3-7 个候选。每个候选必须包含：
- 科学问题：明确研究对象、机制/关系/边界条件。
- 可证伪假设：能被实验、数据或观察推翻。
- 关键预测：如果假设成立，应观察到什么。
- 反证路径：什么结果会推翻假设。
- 初始价值判断：新颖性、重要性、可行性和风险。

候选必须明确指出它来自研究脉络 map 的哪个缺口、转折或矛盾，并给出至少一个支持该推理的论文锚点。若 map 证据不足，先补充雷达/解读，不得用“常识”填空。

避免只写宽泛主题，例如“研究 X 的机制”。科学问题必须能被一个具体研究计划承接。

#### 逐对查新

逐一查新每个候选，形成候选池后再比较：

1. 用 `research-topic-extractor` 把该候选转换成查新主题、关键词和核心问题。
2. 将每个候选的主题提取结果保存到 `candidates/Cx/theme.json`。
3. 调用 `research-literature-review`，档位固定为 `Premium`，输出目录限定为 `.bensz-api/task-{yyyymmdd-hhmm}-{简短描述}/research-idea/*/novelty/Cx/`。
4. 每个候选必须形成 `novelty/Cx/novelty-decision.json`，字段包括：
   - `novelty_status`：`未研究` / `部分研究但关键缺口存在` / `已充分研究`
   - `direct_answer`：已有研究是否直接回答该科学问题
   - `equivalent_hypothesis_tested`：是否已有等价假设被检验
   - `key_gap`：关键缺口
   - `decision`：保留 / 修改 / 淘汰

如果所有候选均为“已充分研究”，把查新结论作为反例证据，回到“基于研究脉络 map 的初始候选”重新 brainstorming；只有当 map 本身不足以支持新一轮推理时，才回到文献调查阶段补充证据。

#### 多轮独立打磨

对保留或需修改的候选，用 `parallel-vibe` 做默认 3 轮串行独立审查。`rounds=3` 是外层迭代轮数，`n=3` 是每轮独立 agent 数；必须执行 3 次 `parallel-vibe`，每次把上一轮汇总后的改写版本作为下一轮输入。

```text
科学问题-科学假设有没有什么缺陷？哪里可以改进？
```

执行要求：
- 默认 `rounds=3`、每轮 `n=3`，默认串行；用户明确要求并行时才并行。
- 每轮/每个 thread 独立读取当前候选、用户资料摘要和查新摘要。
- 每个独立 agent 输出缺陷、改进建议、风险和重写版本；汇总后优化当前候选，再进入下一轮。
- `parallel-vibe` 作为内部依赖运行；读取其 summary 后只抽取结论，不向用户交付其路径。

优先使用：

```bash
for round in 1 2 3; do
  python3 parallel-vibe/scripts/parallel_vibe.py \
    --prompt "{第 ${round} 轮审查指令}" \
    --n 3 \
    --out-dir "{workspace_dir}/parallel-vibe/round-${round}"
done
```

系统级安装时可改用 `~/.codex/skills/parallel-vibe/scripts/parallel_vibe.py` 或 `~/.claude/skills/parallel-vibe/scripts/parallel_vibe.py`。

#### 选择最佳方案

用同一套标准比较所有保留候选：科学重要性、新颖性、可证伪性、可行性、解释力、风险透明度。最佳方案应是综合价值、可证伪性和可推进性最强的一对，不一定是最宏大的问题。

#### 写最终报告并验证

按 `references/report-template.md` 写最终 Markdown。写完后运行：

```bash
python3 research-idea/scripts/validate_report.py --report "{最终报告路径}"
# 系统级安装后也可使用：
python3 ~/.codex/skills/research-idea/scripts/validate_report.py --report "{最终报告路径}"
python3 ~/.claude/skills/research-idea/scripts/validate_report.py --report "{最终报告路径}"
```

若校验失败，先修复报告。随后用控制章节的 prepare/submit 验证最终快照；只有状态到达 completed 才交付，单独结构检查通过不能替代完成 Gate。

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
- 多个科学问题-科学假设对。
- 选择理由、最佳方案及原因。
- 查新摘要、证据缺口、可证伪路径和最小下一步。

报告不得暴露 `.bensz-api/task-{yyyymmdd-hhmm}-{简短描述}/research-idea/`、`tests/research-idea/`、`parallel-vibe/`、`.parallel-vibe/`、`.parallel_vibe/`、`@main/summary.md`、manifest 或其他中间产物路径。

### 输出管理

本 Skill 的新任务中间文件统一写入 `./.bensz-api/task-{yyyymmdd-hhmm}-{简短描述}/{skill名}/input|output|log/`。同一任务复用一个任务根目录；多 Skill 协作才创建 `shared/`。正式交付物不写入该目录，历史隐藏目录只允许显式兼容读取、迁移或清理。

- 默认工作区：`{cwd}/.bensz-api/task-{yyyymmdd-hhmm}-{简短描述}/research-idea/`。
- 所有中间文件、查新记录、并行审查产物、草稿和日志都必须保存在隐藏工作区内；除最终 Markdown 外，不要写到项目根目录或 `docs/ideas/`。
- 用 `--task-root` 显式复用本轮任务根，必须位于项目内 `.bensz-api/task-*`；旧 `--workspace-dir` 嵌套布局只保留历史文件，不自动迁移。输出目录不得位于隐藏工作区内。

初始化优先使用脚本：

```bash
python3 research-idea/scripts/init_workspace.py --input-label "{简短主题或资料名}" --cwd . --task-root "{本轮任务根}"
# 系统级安装后也可使用：
python3 ~/.codex/skills/research-idea/scripts/init_workspace.py --input-label "{简短主题或资料名}" --cwd . --task-root "{本轮任务根}"
python3 ~/.claude/skills/research-idea/scripts/init_workspace.py --input-label "{简短主题或资料名}" --cwd . --task-root "{本轮任务根}"
```

脚本先检查 Kernel 版本，以及配置中的主题提取、文献雷达、论文解读、文献综述与并行审查依赖；缺失时早失败。用户指定审查轮次或人数时增加 `--rounds` / `--agents`，自定义文件名增加 `--allow-custom-name`。

### 校验

- 测试源码位于 Skill 的 `tests/`，测试材料和运行日志放本轮工作区的 output/log，最终报告不引用测试路径。
- 普通业务不创建测试区；旧 `--with-test-dir` 仅为开发兼容选项，使用时显式把 `--test-dir` 指向本轮工作区。

- 科学问题必须是问题，不是主题名。
- 假设必须可证伪，不写无法被推翻的价值判断。
- 查新结论必须区分“没有研究过”和“研究过但缺口仍在”。
- 不因查新成本高而跳过 Premium 文献调研。
- 不把文献综述正文当作最终输出；最终输出是研究想法报告。
- 不泄露隐藏工作区、中间文件、agent 内部指令或测试路径。

### 失败与恢复

保留错误证据和已完成产物；通过 `idea_runtime.py status` 重放恢复最近阶段。证据修复后 prepare 新 attempt；已通过的前置证据变化时先 rework 回相应阶段，不能复用旧 Gate。取消用 cancel，Kernel 缺失或不匹配时停止控制流程，不静默降级。

## 控制

使用前读取 [运行契约与命令](references/runtime-guide.md)。配置中的 `runtime` 声明 Kernel、State 与 required Verifier；索引分别位于 [State 集合](references/states/index.json) 和 [Verifier 集合](references/verifiers/index.json)，身份与版本只在索引维护。

- 在 literature → candidates、candidates → review、review → reporting、reporting → completed 的阶段边界调用 `idea_runtime.py prepare`，按 [Verifier 契约](references/verifiers/stage-readiness/VERIFIER.md) 实际核验固定证据，再 submit 绑定的 Agent 结果。
- 主 Agent 负责调用宿主与语义核验，原有文献解读和独立审查协作要求仍执行；Kernel 不负责创建 Agent。handoff 是待办，不能记为通过。
- 脚本检查非空证据、角色、文件哈希、审查结果数量和最终报告结构；Agent 判断文献依据、map 完整性、可证伪性、逐对 Premium 查新、独立审查及报告一致性。
- required 组件均完成并 pass 才推进；fail/uncertain/unchecked/error/timed_out/skipped 均保留阶段。证据不足交由补证据或人工复核，再执行绑定回传，不提供人工强制通过开关。
- 回退用 rework 并记录原因与证据；只允许 State 图中的前置阶段，失效目标及下游检查点。事件保留 run/attempt、契约与证据哈希，用 status 重放，不手改状态文件。

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
