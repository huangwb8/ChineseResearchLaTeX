---
name: research-literature-review
description: 当用户要求系统综述、文献综述、related work、相关工作或文献调研时使用；也支持明确的研究查新任务。兼容旧名 systematic-literature-review。仅检索候选论文、单条引文核查或既有正文润色不属于本 Skill。
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

## 流程

### 输入

最少需要：

1. `{主题}`：一句话主题。
2. 可选范围：时间、语言、研究类型、数据库偏好等。
3. 档位：`Premium` / `Standard` / `Basic`；未指定时读取 `config.yaml` 默认值。
4. 目标字数与参考文献范围：未指定时按 `config.yaml.scoring.default_*_range`。
5. 输出目录或安全化前缀：未指定时使用安全化主题名。
6. 查询输入：阶段 1 前必须提供符合公开 schema 的多查询 JSON；推荐用 `--query-file`，也可填写当前 run 的 `input/queries.json`。

明确叙述性进展综述、正式系统综述或 novelty-check。查询由 AI 按主题生成，不把内部 JSON 准备责任转嫁给用户；仅缺少会影响范围的关键信息时澄清。

### 执行步骤

- 当用户环境中出现因本 skill 设计缺陷导致的 bug 时，优先使用 `bensz-collect-bugs` 按规范记录到 `~/.bensz-skills/bugs/`，严禁直接修改用户本地 Claude Code / Codex 中已安装的 skill 源码。
- 若 AI 仍可通过 workaround 继续完成用户任务，应先记录 bug，再继续完成当前任务。
- 当用户明确要求“report bensz skills bugs”等公开上报动作时，调用本地 `gh` 与 `bensz-collect-bugs`，仅上传新增 bug 到 `huangwb8/bensz-bugs`；不要 pull / clone 整个 bug 仓库。

#### 准备

- 记录主题、档位、字数/参考范围与输出目录。
- 先读取 `references/ai_query_generation_prompt.md`，生成查询 JSON。公开 schema 支持以下三种形态：
  - `{"queries": [{"query": "...", "rationale": "..."}]}`
  - `[{"query": "...", "rationale": "..."}]`
  - `["query 1", "query 2"]`
- 剔除空查询后，有效数量必须满足 `config.yaml:query_input.min_queries/max_queries`（默认 5–25）。
- 已知工作目录时，直接将文件保存到 `<work-dir>/input/queries.json`，或用 `--query-file <path>` 让 runner 将显式输入复制到该位置。工作目录尚未建立时，先运行 `--prepare-only`，填充打印出的 `input/queries.json`，再以 `--resume ... --resume-from 1` 继续。
- 参考资料按阶段读取，入口与用途见 [README 的参考资料索引](README.md#参考资料与读取时机)；评分时读评分模板，写作时读写作指南与 TeX 模板，翻译资料仅在翻译任务中读取。

#### 多查询检索（调用 research-literature-search）

- 查询来源优先级固定为：显式 `--query-file` → 当前 run 的 `input/queries.json` → `input/queries_{stem}.json` → `output/artifacts/queries_{stem}.json` → 当前 run 内唯一历史兼容文件。
- 自动发现多个候选时停止并报告冲突；发现文件但 schema/数量无效时停止并给出修复提示。不得跨 run 猜测查询路径。
- 启动阶段先发现并校验 `research-literature-search`（顺序：`--search-skill-root` → 项目内 `skills/research-literature-search` → 环境变量 → 用户 Skill 根目录）；缺失或 contract 不兼容时 fail-closed，并给出安装提示。
- 调用 search 的 `run` 入口生成 manifest bundle；review 将其作为只读输入包保存并记录 manifest/candidate hash、contract version 和 source path。
- Search Log 的 `search_mode/query_source/requested_query_count/accepted_query_count/fallback_reason` 由 manifest 单向生成；AI 不手写 provider 次数、候选数量或去重结论。
- 单查询只作为显式后备：传 `--allow-single-query-fallback`，可用 `--fallback-reason` 写明原因；日志必须标记 `search_mode=single_query` 和醒目警告。

#### 去重（契约验证，不重复去重）

- 验证 manifest、artifact hash、`rls.paper.v1` 和 `candidates_deduped.jsonl`；保留 `2_dedupe` checkpoint 名称以兼容 resume。
- 新运行不得再次执行旧 `dedupe_papers.py` 或改变 canonical 顺序；旧文件/旧 checkpoint 仅通过显式 legacy adapter 读取，并标记 `legacy_adapted`。
- 所有后续流程只读取 search bundle 的 canonical 候选集。

#### AI 评分与数据抽取

- AI 按 `references/ai_scoring_prompt.md` 逐篇阅读标题与摘要，输出 `scored_papers.jsonl`。
- 每篇至少包含：`score`、`subtopic`、`rationale`、`alignment`、`extraction`。
- 评分范围为 `config.yaml:scoring.score_scale`（默认 1–10）；达到 `selection.minimum_score`（默认 5）才分配子主题，避免弱相关论文污染子主题规划。
- 评分依主题适配程度，不强制高/中/低分比例；相关性不是偏倚风险或证据强度。

#### 选文与 Bib 生成

- `select_references.py` 按最低相关性、证据角色和软预算选出最终集合；`target_refs` 是预算目标，`max_refs` 是上限，不再用低分或无摘要条目填满旧 `min_refs`。
- 生成 `selected_papers.jsonl`、`references.bib`、`selection_rationale.yaml`。
- Bib 清洗必须保留：大小写无关去重 key、LaTeX 特殊字符转义、缺失字段警告。
- 证据角色使用 `direct-neighbor`、`supporting`、`methodological`、`contradictory`、`boundary`；直接近邻和反方证据优先于宽泛方法相似。
- 标准综述只把有摘要且达到相关性阈值的条目放入正式引用集合。合格论文少于软目标时照常交付较小集合，并在 rationale 写停止理由与证据缺口。
- 显式 `do_not_cite=true` 的条目不得进入标准综述的选文和 Bib；原始评分审计保留，查新模式仍可保留禁止引用的待核验线索。

#### Novelty check

当调用目的为 `--purpose novelty-check` 时，只运行到阶段 4，输出强近邻、反方/边界证据、未确认项与证据深度，不自动生成长篇正文、PDF 或 Word。只有标题的直接近邻可保留为待升级记录并标记 `do_not_cite`；预印本与正式论文使用同一相关性尺度，发表状态单列。

#### 子主题与配额规划

- AI 基于评分结果规划 3-7 个子主题，并给出段落配额。
- 默认思路：引言约 1.5k、讨论/展望各约 1k、结论约 0.6k，其余分给子主题段。
- 结果写入工作条件与数据抽取表，作为写作锚点。

#### 字数预算

- 用 `plan_word_budget.py` 生成 3 份预算 CSV，再汇总为 `word_budget_final.csv`。
- 引用段与无引用段预算均需覆盖；总字数误差必须控制在 `config.yaml.word_budget.tolerance` 内。
- 生成和验证预算必须传递同一档位与目标字数；独立校验可用 `--review-level` 或 `--target-words`。预算生成仅额外允许读取 Skill 自带的只读配置，其余输入和输出仍限于当前工作目录。

#### 写作

- 默认章节为摘要、引言、主体、讨论、展望、结论。正文直接呈现领域认识、研究发现、争议与证据边界；摘要、引言、主体、讨论、展望和结论均不叙述本次综述写作前如何调研文献，也不把这些内容挪到脚注、图表或附录。
- 本次综述的数据库与平台、检索式、检索日期或更新截止日、追溯方式、纳排与筛选过程、文献数量、评分选文及 RoB/GRADE 是否实施等说明，统一写入工作条件、Search Log 或配套报告；不以“透明检索”“叙述性综述”或未实施某项方法的免责声明带回正文。主题、人群、疾病阶段等实质范围可在引言简要界定。
- 讨论原始研究的设计、偏倚、异质性、疗效及外推限制仍是正文任务；区分“被综述研究的方法”与“本次综述的制作过程”。仅用户或目标期刊明确要求方法报告（如 PRISMA）时，才按要求另设方法章节或补充材料；仅称“系统综述”不自动加入流程叙述，也不得虚构已完成的方法或据此宣称符合报告规范。
- 写作前读取 `word_budget_final.csv` 与完整证据资料，预算用于检查篇幅，不机械逐篇填空。关键主张核对人群、设计、终点、数值、不确定性及指南版本；证据深度在工作条件中如实说明。
- 证据卡保留完整摘要和已有提取字段；显式截断时依 source_id/source_record 回读原始选文。缺证据先补检或缩小主张，不靠语言扩写填满预算。
- 新稿用 `render_review_template.py --title ... --body ... --bib ... --output ...` 应用真实学术模板；已有完整 TeX 或指定版式保留。阅读 `references/review-tex-section-templates.md` 后再写导言区。
- 默认采用单篇引用优先；引用要紧跟所支撑的观点，避免段末堆砌。
- 如需详细写作规范，直接遵循：
  - `references/expert-review-writing.md`
  - `references/review-tex-section-templates.md`

#### 有机扩写与验证

- 若字数不足，先判断是否遗漏问题、比较或证据；只有新增内容有实际解释价值时扩写。结构或主张需要改变时回到证据与规划阶段，不为凑字数重复边界声明。
- 交稿前逐段检查正文是否在回答“这篇综述是怎样做出来的”；若是，将过程信息移至配套材料，删去重复声明。该语义检查同时覆盖中文、英文、摘要、脚注、图表与附录，不能只凭流程关键词或数据库名判定，也不能据脚本通过宣称已完成。
- 依次运行：
  - `validate_counts.py`
  - `validate_review_tex.py`
  - `validate_subtopic_count.py`（默认 3–7 个主体主题）
  - `validate_word_budget.py`（已有预算时执行）
  - `generate_validation_report.py`

#### 导出与多语言

- 通过 `compile_latex_with_bibtex.py` 生成 PDF；内置 BST 直接引用当前宿主机 Skill 根目录下 `references/latex-template/` 中的样式文件，不另写或复制样式。未解析引文/交叉引用及缺字阻断导出，最终 `.log/.blg` 留在内部供排查。`--template` 只提供搜索目录，不会应用版式。
- 通过 `convert_latex_to_word.py` 生成 Word，一级标题默认 Heading1，使用随 skill 提供的数字引文 CSL。
- 导出后实际检查首页、正文、最长表格、图注与参考文献，并核对 PDF/Word 的正文、图表和书目完整性。把检查页码、结果及未验证项写入工作条件中的交付检查记录；编译成功不代表目视或证据审查通过。
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

- 开发与完整运行环境：Python 3.11+、LaTeX（`xelatex`/`bibtex`）、pandoc；Python 包及版本约束统一读取 `config.yaml:dependencies.python`，环境准备时按该列表安装。
- 关键脚本：
  - 检索与 canonical 验证：`search_skill_resolver.py`（旧 provider/去重脚本仅供显式 legacy 兼容）
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

### 输出

标准运行默认发布完整文稿包（`--publish-dir` 指定正式目录）：

- `{主题}_review.pdf`
- `{主题}_review.docx`

同时包含 `{主题}_工作条件.md`、`{主题}_review.tex`、`{主题}_参考文献.bib`、`{主题}_验证报告.md` 及 TeX 实际引用的相对图表、片段。成品不生成或交付 README；使用说明与限制写入已有工作条件。Skill 自带的 BST 由 TeX 直接引用宿主机上的绝对路径（不带 `.bst` 后缀），系统样式由 TeX 发行版提供，均不复制到成品目录；仅用户明确指定的本地自定义资源随稿保留。缺必需文件或资源时停止发布；保留原有文件，未经明确授权不覆盖。`--readers-only` 显式只交 PDF/Word，`--include-supporting` 保留为完整包入口。字数预算、候选文献、评分、选文、摘要补齐和证据卡始终属于内部材料，不进入正式发布目录。

必要中间产物包括：

- `papers*.jsonl`
- `scored_papers.jsonl`
- `selected_papers.jsonl`
- `selection_rationale.yaml`
- 可选 `evidence_cards_{主题}.jsonl`

### 输出管理

本 Skill 的新任务中间文件统一写入 `./.bensz-api/task-{yyyymmdd-hhmm}-{简短描述}/{skill名}/input|output|log/`。同一任务复用一个任务根目录；多 Skill 协作才创建 `shared/`。正式交付物不写入该目录，历史隐藏目录只允许显式兼容读取、迁移或清理。

- 默认 `run_pipeline.py` 将运行目录放在 `.bensz-api/task-{yyyymmdd-hhmm}-{简短描述}/research-literature-review/<run-id>/`；查询输入位于 `input/`，内部状态和产物位于 `output/` 下的 `artifacts/`、`reference/`、`cache/`、`scripts/`、`deliverables/`（支持性文件单独位于 `deliverables/supporting/`）。
- 正式交付目录必须通过 `--publish-dir` 显式指定，默认接收完整文稿包；仅阅读模式只接收 PDF/Word。不要把正式目录作为 `--work-dir`。
- 任务工作区的内部 README 不属于综述成品，不复制到正式目录。不要自行向成品补写 README 或复制内置 BST/CSL；宿主机 Skill 路径变化或换机时，用接收端 Skill 资源路径更新 TeX 引用后重编译。
- AI 临时脚本必须放到内部 `output/scripts/`；不要把临时文件写到运行目录根部，不要使用绝对路径写 `/tmp/*`，也不要读写其他 run 目录。
- 以环境变量 `SYSTEMATIC_LITERATURE_REVIEW_SCOPE_ROOT` 和 `SYSTEMATIC_LITERATURE_REVIEW_SCRIPTS_DIR` 为准。
- search bundle 位于当前 review run 的 `output/artifacts/search_bundle_{stem}/`，review 只读消费其 manifest 指向的相对路径；不得跨 run 猜测或直接信任外部绝对 artifact 路径。

### 校验

阶段 6 只有计数、TeX 结构、子主题、已有预算、摘要可用性和报告生成均通过才完成；恢复已完成运行也重新校验并导出当前稿件。报告只证明其实际检查范围，不能由 key 对齐推断论断正确或全文已读。最终交付另需实际渲染、内容一致性与资源复现检查；未执行项保持未验证。

### 失败与恢复

保留错误证据和已完成产物；仅在输入、环境或外部依赖恢复后从最近的失败步骤重试。

## 约束

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

- 完整综述必须导出 PDF 与 Word；失败时记录原因并保留未完成状态，缺任一格式不得发布。`novelty-check` 不适用。
- 正文字数依用户要求与当前配置验收；参考数量为软预算，保留相关性门槛，不凑篇数；篇数缺口与停止理由写入工作条件。
- 默认正文包含摘要、引言、3–7 个主体主题、讨论、展望和结论；结构检查不代替学术内容审查。
- `\cite{key}` 必须与 BibTeX key 一致；缺失即报错。
- 本次综述的文献调研与制作过程写入配套材料，默认不进入正文；方法报告仅按写作步骤所列的明确要求处理。保留对原始研究方法与证据局限的必要分析，不虚构检索、独立筛选或偏倚评价。
- 摘要必须为单段，避免方法学流水账；表格宽度与样式约束见 `references/review-tex-section-templates.md`。
- 不为凑引用而堆砌低分文献；无法确认时优先不改、不引。
- 多查询 JSON 缺失、冲突、不可解析、有效查询少于配置下限或超过上限时，阶段 1 必须 fail-closed；不得以成功退出码伪装成多查询完成。
- 只有调用方显式传入 `--allow-single-query-fallback` 时才允许执行一次单查询，并在 state 与 Search Log 中记录模式、来源、原因和警告。



不得超出本 Skill description 和上方流程所声明的范围；不将未验证的信息伪装成确定结论。
