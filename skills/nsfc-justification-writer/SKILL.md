---
name: nsfc-justification-writer
description: 当用户要求写作、重构、审查或润色 NSFC/科研基金申请书的立项依据时使用；不负责研究目标、技术路线或其他章节的正文写作。
metadata:
  author: Bensz Conan
  keywords:
    - nsfc-justification-writer
---
# 科研立项依据写作器

## 目标

本 Skill 将 NSFC/科研基金申请书的立项依据整理为可核验、论证连贯且保留 LaTeX 结构的正文。它适用于新写、重构、审查和润色立项依据；宿主 AI 负责理解材料、安排论证和改写正文，Python 脚本负责确定性检查与安全写入。

立项依据的内容链为：**研究意义 → 国内外研究现状 → 科学问题与科学假设 → 小结**。研究目标、技术路线、主验证场景、终点、阈值和风险处理属于后续章节，本 Skill 只在需要时作简短衔接，不展开这些内容。

## 流程

### 输入

- 必需：项目根目录，以及目标立项依据正文或可定位该正文的项目材料。
- 通常读取：目标 `.tex`、研究内容、研究基础和项目 `.bib`；只读取完成当前论证所需的内容，不归档无关原始材料。
- 可选：CLI 的 `--target-file`、完整正文提案文件和 `--override` 配置。目标文件按“显式配置 → 文件名含立项依据或 justification 的候选 → 字典序”选择；找不到时使用配置允许的默认目标并创建文件。
- 先按需读取 [分节写法](references/section_writing.md) 规划论证地图和段落推进；完成正文后读取 [质量控制](references/quality_control.md) 执行一次语义复核。
- 不把密钥、令牌、凭据、Cookie、完整私有 Prompt 或不必要的大体积原始数据写入产物、日志或报告。

### 执行步骤

1. 读取目标正文、相关研究内容、研究基础和 `.bib`，确认研究对象、现有瓶颈、证据、科学问题和假设；信息不足时采用最小保守假设，并把待核验项列入输出。
2. 宿主 AI 一次性完成结构判断、论证规划、正文生成和语义审查。研究意义默认 2–3 段、约占正文 15%–25%；研究现状按主题组织，每个研究现状主题默认 1 段、必要时最多 2 段；科学问题用疑问句，科学假设用可证伪的预测性陈述。
3. 保留已核验事实、限定、引用、标签和 LaTeX 结构；不新增无法在项目 `.bib` 中核验的文献、结果或绝对化结论。按 [质量控制](references/quality_control.md) 检查事实与证据、逻辑闭环、章节边界和专业可读性。
4. 将完整正文提案交给 `scripts/run.py preview`。脚本检查路径白名单、引用 key/DOI、正文结构命令和变更范围，并可报告字数统计；检查通过后默认备份并写入，`--dry-run` 只生成 diff。
5. 需要单独查看机器结果时使用 `diagnose`、`refs` 或 `wordcount`；需要回溯历史时使用 `list-runs`、`diff` 和 `rollback`。

### 输出

- `preview`：目标文件的正文-only unified diff；成功写入时同时返回目标路径、修改摘要、假设/待核验项、备份路径和回滚命令。
- `diagnose`：结构、引用、DOI、字数和配置约束的文本摘要；传入 `--json-out` 时额外保存 JSON。
- `refs`：引用核验摘要及 BibTeX 补齐/核验提示；`wordcount`：按选定口径统计当前字数，不设默认目标、容差或偏差状态。
- `list-runs`、`diff`、`rollback`：列出运行记录、查看某次运行的备份差异或从备份恢复。

### 输出管理

- 运行记录、临时 diff 和备份使用 `config.yaml` 的 `workspace.runs_dir`，默认位于当前任务的 `./.bensz-api/task-{yyyymmdd-hhmm}-{简短描述}/nsfc-justification-writer/`。
- 正式正文只写入自动确定且通过白名单的目标 `.tex`；不写 `main.tex`、配置文件、`.cls` 或 `.sty`。正式源代码、文档和计划仍写入仓库约定路径，不放入任务工作区。
- `preview` 默认自动写入；需要只读审查时显式使用 `--dry-run`。每次写入前备份，回滚默认先备份当前版本；回滚必须显式传入 `--yes`。
- 任务失败时保留提案、诊断、diff 和错误信息，避免覆盖原正文；不得自动删除、迁移或远程上传用户文件。

### 校验

- 运行 `python skills/nsfc-justification-writer/scripts/run.py validate-config`，确认配置字段和写入白名单有效。
- 运行 `diagnose`，通过标准是目标路径在项目范围内、所有 `\\cite{...}` key 可在配置的 `.bib` 中找到、结构命令没有未经允许的变化，且字数统计结果已报告（不作目标值判断）。
- 运行 `preview --dry-run`，确认变更只涉及正文；出现结构/配置命令时默认拒绝，只有项目白名单允许且用户明确传入 `--allow-structural-change` 才能继续。
- 运行 `python skills/nsfc-justification-writer/tests/test_semantic_boundaries.py` 验证目标定位、字数无约束统计、引用守护、备份/回滚和正文-only diff；测试缓存集中在 `.bensz-api/`。
- 结构规范另由仓库级 Skill 检查器验证；本 Skill 不把结构检查器当作语义质量判断的替代品。

### 失败与恢复

- 目标不明确、路径越界或不在白名单：停止写入，报告候选和原因；修正配置或显式目标后从目标定位重新开始。
- 缺失输入：继续使用最小保守假设，但必须输出待核验项；不得补造文献、结果或结论。
- 缺失引用 key、结构命令变化或安全检查失败：保留提案和诊断结果，拒绝写入；修正正文后重新运行 `preview`。
- 写入异常：以原文件和写入前备份为恢复起点，保留 run 记录；不要把部分写入宣称为完成。
- 需要撤销已写入内容时，先用 `list-runs` 找到 `run_id`，再执行 `rollback --yes`；无法定位匹配目标的备份时停止并报告，不使用不确定的旧备份。

## 约束

遵守以下公共约束，并执行本 Skill 的专属边界。

<!-- BEGIN COMMON CONSTRAINTS -->
<!-- Source-Hash: sha256:06cb6c120cdd9b63b209c9e53b6e01d42c90e9d93bd857a0f093127b69a0f03f -->
<!-- Template-ID: skill-common-constraints; Template-Version: 1; Sync-Policy: exact-block -->
### 公共硬约束

- 任务需要落盘时，使用唯一的 `./.bensz-api/task-{yyyymmdd-hhmm}-{简短描述}/` 根目录；共享材料放入 `shared/`，Skill 专属材料放入该 Skill 的 `input/`、`output/`、`log/`。
- 正式交付物、源代码和正式计划按项目约定保存，不写入任务工作区；未经授权不覆盖、删除、迁移或远程写入。
- 项目维护变更检查 BAC 可用性并记录需求、AI 产出、工具结果、文件改动和验证摘要；BAC 只做过程审计，不替代署名、责任或合规判断。
- 不记录 API Key、访问令牌、密码、Cookie、环境/凭据文件、私有 Prompt、身份信息、本地用户名、主机名或不必要的大体积原始数据。
- 文件路径必须规范化并限制在授权项目范围内；外部 URL、子进程和网络访问遵循最小权限，防止路径遍历、SSRF 和命令注入。
- Skill 版本唯一记录在自身 `config.yaml:skill_info.version`；公开 API、协议、目录或配置变更同步文档与 `CHANGELOG.md`。
- 仅将 Skill 或 Bensz 基础设施本身的设计缺陷交给 `bensz-collect-bugs`；先脱敏写入 `~/.bensz-skills/bugs/`，当前任务不中断，只有用户明确要求才公开上报，禁止直接修改用户已安装的 Skill 源码。
<!-- End of canonical common constraints. -->
<!-- END COMMON CONSTRAINTS -->

### Skill 专属约束

- 只改自动确定且通过白名单的正文；保留标题、章节/环境命令、标签和引用命令。
- 不改 `main.tex`、项目配置、`.cls` 或 `.sty`；`allow_missing_citations` 为 false 时，缺失 bibkey 默认拒绝写入。
- 不把研究目标、技术路线、主验证场景、终点、阈值或风险处理写成立项依据的主体论证；不把未验证信息伪装成确定结论。
- `bensz-collect-bugs` 是一个用于缺陷留痕与按需上报的 Agent Skill；仅处理本 Skill 或 Bensz 基础设施本身的流程漏判、输入契约不完整和环境假设错误，不处理用户资料错误、第三方服务波动、用户主动改源码或模型偶发波动。
- 缺陷先脱敏记录到 `~/.bensz-skills/bugs/`，当前任务不中断；默认不收集本地用户名、主机名、工作目录或其它敏感信息。
- 只有用户明确要求公开上报时，才使用本机 `gh api` 按文件路径提交脱敏记录；不 clone 或 pull 上游仓库。
- 严禁直接修改用户本地已安装 Skill 的源代码来“顺手修 bug”。
