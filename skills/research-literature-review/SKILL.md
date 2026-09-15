---
name: research-literature-review
description: 当用户明确要求"做系统综述/文献综述/related work/相关工作/文献调研"，或为研究想法核对强近邻与新颖性时使用；兼容旧名 systematic-literature-review。标准模式执行查询、检索、评分、相关性选文、写作、引用校验与 PDF/Word 导出，novelty-check 模式只交付强近邻、反方证据和未确认项。查询缺失或无效时默认停止，不静默降级为单查询。支持 en/zh/ja/de/fr/es。
metadata:
  author: Bensz Conan
---
# Research Literature Review

## 目标

- 目标：在一个隔离工作目录内完成“检索 → 去重 → 评分 → 选文 → 写作 → 校验 → PDF/Word 导出”的完整综述流水线。
- 适用：用户明确要系统综述、文献综述、related work、文献调研，并希望得到 LaTeX + BibTeX + PDF/Word 产物。
- 不适用：只想补单条参考文献、只想润色已有正文、只想写普通摘要或与综述无关的文章。
- 最高原则：以最佳可用证据和写作质量完成综述；不确定时说明处理方式，不为赶进度牺牲可信度。
- `research-literature-search` 是阶段 1/2 的必需依赖（contract `rls.v1`）。review 只消费其 manifest、canonical candidates 和 provenance，不再内嵌 provider 或执行第二套 canonical 去重。
- 旧名 `systematic-literature-review` 仅作为 prompt 兼容别名保留；`.systematic-literature-review/` 仍是稳定历史工作区名。

### 输入概览

最少需要：

1. `{主题}`：一句话主题。
2. 可选范围：时间、语言、研究类型、数据库偏好等。
3. 档位：`Premium` / `Standard` / `Basic`；未指定时读取 `config.yaml` 默认值。
4. 目标字数与参考文献范围：未指定时按 `config.yaml.scoring.default_*_range`。
5. 输出目录或安全化前缀：未指定时使用安全化主题名。
6. 查询输入：阶段 1 前必须提供符合公开 schema 的多查询 JSON；推荐用 `--query-file`，也可填写当前 run 的 `input/queries.json`。

## 流程

### 输入

按用户请求和配置文件提供必要输入；缺失信息应明确列出并停止依赖该输入的步骤。

### 执行步骤

- 当用户环境中出现因本 skill 设计缺陷导致的 bug 时，优先使用 `bensz-collect-bugs` 按规范记录到 `~/.bensz-skills/bugs/`，严禁直接修改用户本地 Claude Code / Codex 中已安装的 skill 源码。
- 若 AI 仍可通过 workaround 继续完成用户任务，应先记录 bug，再继续完成当前任务。
- 当用户明确要求“report bensz skills bugs”等公开上报动作时，调用本地 `gh` 与 `bensz-collect-bugs`，仅上传新增 bug 到 `huangwb8/bensz-bugs`；不要 pull / clone 整个 bug 仓库。

### 准备

- 记录主题、档位、字数/参考范围与输出目录。
- 先读取 `references/ai_query_generation_prompt.md`，生成查询 JSON。公开 schema 支持以下三种形态：
  - `{"queries": [{"query": "...", "rationale": "..."}]}`
  - `[{"query": "...", "rationale": "..."}]`
  - `["query 1", "query 2"]`
- 剔除空查询后，有效数量必须满足 `config.yaml:query_input.min_queries/max_queries`（默认 5–25）。
- 已知工作目录时，直接将文件保存到 `<work-dir>/input/queries.json`，或用 `--query-file <path>` 让 runner 将显式输入复制到该位置。工作目录尚未建立时，先运行 `--prepare-only`，填充打印出的 `input/queries.json`，再以 `--resume ... --resume-from 1` 继续。
- 开始前优先阅读：
  - `references/ai_query_generation_prompt.md`
  - `references/ai_scoring_prompt.md`
  - `references/expert-review-writing.md`
  - `references/review-tex-section-templates.md`
  - 涉及翻译时再读 `references/multilingual-guide.md`

### 多查询检索（调用 research-literature-search）

- 查询来源优先级固定为：显式 `--query-file` → 当前 run 的 `input/queries.json` → `input/queries_{stem}.json` → `output/artifacts/queries_{stem}.json` → 当前 run 内唯一历史兼容文件。
- 自动发现多个候选时停止并报告冲突；发现文件但 schema/数量无效时停止并给出修复提示。不得跨 run 猜测查询路径。
- 启动阶段先发现并校验 `research-literature-search`（顺序：`--search-skill-root` → 项目内 `skills/research-literature-search` → 环境变量 → 用户 Skill 根目录）；缺失或 contract 不兼容时 fail-closed，并给出安装提示。
- 调用 search 的 `run` 入口生成 manifest bundle；review 将其作为只读输入包保存并记录 manifest/candidate hash、contract version 和 source path。
- Search Log 的 `search_mode/query_source/requested_query_count/accepted_query_count/fallback_reason` 由 manifest 单向生成；AI 不手写 provider 次数、候选数量或去重结论。
- 单查询只作为显式后备：传 `--allow-single-query-fallback`，可用 `--fallback-reason` 写明原因；日志必须标记 `search_mode=single_query` 和醒目警告。

### 去重（契约验证，不重复去重）

- 验证 manifest、artifact hash、`rls.paper.v1` 和 `candidates_deduped.jsonl`；保留 `2_dedupe` checkpoint 名称以兼容 resume。
- 新运行不得再次执行旧 `dedupe_papers.py` 或改变 canonical 顺序；旧文件/旧 checkpoint 仅通过显式 legacy adapter 读取，并标记 `legacy_adapted`。
- 所有后续流程只读取 search bundle 的 canonical 候选集。

### AI 评分与数据抽取

- AI 按 `references/ai_scoring_prompt.md` 逐篇阅读标题与摘要，输出 `scored_papers.jsonl`。
- 每篇至少包含：`score`、`subtopic`、`rationale`、`alignment`、`extraction`。
- 评分范围固定为 1-10 分；仅对 `>=5` 分文献分配子主题，避免弱相关论文污染子主题规划。
- 自检分布是否健康：高分约 20-40%，中分 40-60%，低分 10-30%。

### 选文与 Bib 生成

- `select_references.py` 按最低相关性、证据角色和软预算选出最终集合；`target_refs` 是预算目标，`max_refs` 是上限，不再用低分或无摘要条目填满旧 `min_refs`。
- 生成 `selected_papers.jsonl`、`references.bib`、`selection_rationale.yaml`。
- Bib 清洗必须保留：大小写无关去重 key、LaTeX 特殊字符转义、缺失字段警告。
- 证据角色使用 `direct-neighbor`、`supporting`、`methodological`、`contradictory`、`boundary`；直接近邻和反方证据优先于宽泛方法相似。
- 标准综述只把有摘要且达到相关性阈值的条目放入正式引用集合。合格论文少于软目标时照常交付较小集合，并在 rationale 写停止理由与证据缺口。

### Novelty check

当调用目的为 `--purpose novelty-check` 时，只运行到阶段 4，输出强近邻、反方/边界证据、未确认项与证据深度，不自动生成长篇正文、PDF 或 Word。只有标题的直接近邻可保留为待升级记录并标记 `do_not_cite`；预印本与正式论文使用同一相关性尺度，发表状态单列。

### 子主题与配额规划

- AI 基于评分结果规划 3-7 个子主题，并给出段落配额。
- 默认思路：引言约 1.5k、讨论/展望各约 1k、结论约 0.6k，其余分给子主题段。
- 结果写入工作条件与数据抽取表，作为写作锚点。

### 字数预算

- 用 `plan_word_budget.py` 生成 3 份预算 CSV，再汇总为 `word_budget_final.csv`。
- 引用段与无引用段预算均需覆盖；总字数误差必须控制在 `config.yaml.word_budget.tolerance` 内。

### 写作

- 正文章节固定为：摘要、引言、子主题段、讨论、展望、结论。
- 写作前读取 `word_budget_final.csv`，按文献综/述预算组织证据。
- 默认采用单篇引用优先；引用要紧跟所支撑的观点，避免段末堆砌。
- 如需详细写作规范，直接遵循：
  - `references/expert-review-writing.md`
  - `references/review-tex-section-templates.md`

### 有机扩写与验证

- 若字数不足，只允许在最短或证据不足的子主题段内做增量扩写，不新增子主题，不改原主张和引用。
- 依次运行：
  - `validate_counts.py`
  - `validate_review_tex.py`
  - 可选 `validate_word_budget.py`
  - `generate_validation_report.py`

### 导出与多语言

- 通过 `compile_latex_with_bibtex.py` 生成 PDF。
- 通过 `convert_latex_to_word.py` 生成 Word。
- 如用户要求多语言版本，使用 `multi_language.py` 翻译正文并智能编译；失败时保留错误报告与 broken 文件，并优先支持恢复备份。

```bash
# 查询文件已准备好：推荐主入口
python3 scripts/run_pipeline.py --topic "{主题}" --query-file ./queries.json --publish-dir ./review-deliverables

# 两步式：先生成模板，再填充 input/queries.json 并恢复阶段 1
python3 scripts/pipeline_runner.py --topic "{主题}" --work-dir <work-dir> --prepare-only
python3 scripts/pipeline_runner.py --resume <work-dir> --resume-from 1 --publish-dir ./review-deliverables

# 临时兼容外部编排器：显式、可审计的单查询后备
python3 scripts/run_pipeline.py --topic "{主题}" --allow-single-query-fallback --fallback-reason "外部编排器暂未提供查询文件"

# 旧入口 / resume
python3 scripts/pipeline_runner.py --topic "{主题}" --domain general --query-file ./queries.json --publish-dir ./review-deliverables

# 显式指定 search Skill（独立安装环境）
python3 scripts/pipeline_runner.py --topic "{主题}" --query-file ./queries.json \
  --search-skill-root /path/to/research-literature-search
python3 scripts/pipeline_runner.py --resume .bensz-api/task-{yyyymmdd-hhmm}-{简短描述}/research-literature-review/{run-id} --publish-dir ./review-deliverables

# 阶段 3 评分后，从第 4 阶段继续
python3 scripts/pipeline_runner.py --resume .bensz-api/task-{yyyymmdd-hhmm}-{简短描述}/research-literature-review/{run-id} --resume-from 4
```

`--resume-from` 只决定继续执行的阶段，不会绕过已有 `pipeline_state.json`。状态文件损坏时先备份或修复，禁止用空 state 覆盖历史 checkpoint。

- 运行环境：Python 3.9+、LaTeX（`xelatex`/`bibtex`）、pandoc。
- 关键脚本：
  - 检索：`multi_query_search.py`、`openalex_search.py`
  - 去重：`dedupe_papers.py`
  - 选文：`select_references.py`、`build_reference_bib_from_papers.py`
  - 数据抽取：`update_working_conditions_data_extraction.py`
  - 字数预算：`plan_word_budget.py`、`validate_word_budget.py`
  - 校验：`validate_counts.py`、`validate_review_tex.py`、`generate_validation_report.py`
  - 导出：`compile_latex_with_bibtex.py`、`convert_latex_to_word.py`

- 初始化：`python3 research-literature-review/scripts/pipeline_cost.py init`
- 抓取定价：`python3 research-literature-review/scripts/pipeline_cost.py fetch-prices`
- 记录 token：`pipeline_cost.py log ...`
- 汇总：`pipeline_cost.py summary`
- 所有成本数据写到内部 `output/cost/`（旧运行仍可显式使用 legacy 目录）。

- `references/ai_query_generation_prompt.md`
- `references/ai_scoring_prompt.md`
- `references/expert-review-writing.md`
- `references/review-tex-section-templates.md`
- `references/multilingual-guide.md`
- `references/development-validation-guide.md`

### 输出

默认发布以下核心文件（通过 `--publish-dir` 指定正式目录时复制）：

- `{主题}_review.pdf`
- `{主题}_review.docx`

可选支持性文件（使用 `--include-supporting` 发布）包括 `{主题}_工作条件.md`、`{主题}_review.tex`、`{主题}_参考文献.bib` 和 `{主题}_验证报告.md`。字数预算、候选文献、评分、选文、摘要补齐和证据卡始终属于内部中间产物，不进入正式发布目录。

必要中间产物包括：

- `papers*.jsonl`
- `scored_papers.jsonl`
- `selected_papers.jsonl`
- `selection_rationale.yaml`
- 可选 `evidence_cards_{主题}.jsonl`

### 输出管理

本 Skill 的新任务中间文件统一写入 `./.bensz-api/task-{yyyymmdd-hhmm}-{简短描述}/{skill名}/input|output|log/`。同一任务复用一个任务根目录；多 Skill 协作才创建 `shared/`。正式交付物不写入该目录，历史隐藏目录只允许显式兼容读取、迁移或清理。

- 默认 `run_pipeline.py` 将运行目录放在 `.bensz-api/task-{yyyymmdd-hhmm}-{简短描述}/research-literature-review/<run-id>/`；查询输入位于 `input/`，内部状态和产物位于 `output/` 下的 `artifacts/`、`reference/`、`cache/`、`scripts/`、`deliverables/`（支持性文件单独位于 `deliverables/supporting/`）。
- 正式交付目录必须通过 `--publish-dir` 显式指定，并且只接收 PDF/Word（或显式开启的支持性文件）。不要把正式目录作为 `--work-dir`。
- AI 临时脚本必须放到内部 `output/scripts/`；不要把临时文件写到运行目录根部，不要使用绝对路径写 `/tmp/*`，也不要读写其他 run 目录。
- 以环境变量 `SYSTEMATIC_LITERATURE_REVIEW_SCOPE_ROOT` 和 `SYSTEMATIC_LITERATURE_REVIEW_SCRIPTS_DIR` 为准。
- search bundle 位于当前 review run 的 `output/artifacts/search_bundle_{stem}/`，review 只读消费其 manifest 指向的相对路径；不得跨 run 猜测或直接信任外部绝对 artifact 路径。

### 校验

完成后执行 Skill 已有的静态检查、脚本验证或人工复核，并记录通过标准。

### 失败与恢复

保留错误证据和已完成产物；仅在输入、环境或外部依赖恢复后从最近的失败步骤重试。

## 约束

- 强制导出 PDF 与 Word；只有明确失败并记录原因时才允许缺失。
- 正文字数与参考文献数必须落在当前档位范围内；可由用户覆盖，默认值以 `config.yaml` 为准。
- 正文固定包含：摘要、引言、至少 1 个子主题段、讨论、展望、结论。
- `\cite{key}` 必须与 BibTeX key 一致；缺失即报错。
- 正文禁止泄露 AI 工作流，例如“检索/去重/评分/选文/字数预算”等元叙事只能写入 `{主题}_工作条件.md`。
- 摘要必须为单段，避免方法学流水账；表格宽度与样式约束见 `references/review-tex-section-templates.md`。
- 不为凑引用而堆砌低分文献；无法确认时优先不改、不引。
- 多查询 JSON 缺失、冲突、不可解析、有效查询少于配置下限或超过上限时，阶段 1 必须 fail-closed；不得以成功退出码伪装成多查询完成。
- 只有调用方显式传入 `--allow-single-query-fallback` 时才允许执行一次单查询，并在 state 与 Search Log 中记录模式、来源、原因和警告。

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
