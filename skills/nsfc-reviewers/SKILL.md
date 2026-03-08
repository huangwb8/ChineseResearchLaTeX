---
name: nsfc-reviewers
description: 当用户明确要求"评审国自然标书"、"模拟专家评审"、"审阅 NSFC 申请书"时使用。模拟领域专家视角对 NSFC 标书进行多维度评审，输出分级问题与可执行修改建议。⚠️ 不适用：用户只是想写/改标书某个章节（应使用 nsfc-*-writer 系列技能）、只是想了解评审标准（应直接回答）、没有明确"评审/审阅"意图。
metadata:
  author: Bensz Conan
  short-description: 模拟专家评审 NSFC 标书
  keywords:
    - nsfc-reviewers
    - proposal review
    - peer review
---

# NSFC 标书专家评审模拟器

## 重要声明（非官方）

- 本技能输出仅用于**写作改进与自查**，不代表任何官方评审口径，也不构成资助结论或承诺。
- “函评/会评给不过”的判断仅作为**当前版本送审风险预估**，用于帮助用户判断优先修改方向，不代表真实评审结果。

## 技能依赖

- 并行多组评审模式依赖 `parallel-vibe` 技能。
- 若 `parallel-vibe` 不可用、被禁用，或 `panel_count == 1`，自动退化为单组模式（仍包含 7 位专家）。
- 专家 prompt 模板位于 `references/expert_*.md`，聚合规则位于 `references/aggregation_rules.md`。

## 安全与隐私（硬规则）

- 默认将标书内容视为**敏感信息**：仅处理用户明确提供的文件/目录；不擅自扩展扫描范围。
- 除非用户明确要求且确认风险：**不联网**、不把原文大段外发、不在输出中复述不必要的个人信息/单位信息。
- 只做“文本读取与评审”，默认不执行任何编译/运行（例如不运行 LaTeX 编译，不执行脚本）。
- 输出若需分享：优先提供“问题摘要 + 可执行修改建议”，必要引用原文时只引用**最短必要片段**。

## 输入

用户至少提供其一：

- `proposal_path`：标书目录（推荐，包含多份 `.tex`）
- `proposal_file`：单个 `.tex` 主文件（如用户只有一个文件）
- `proposal_zip`：压缩包（若用户提供，先解压到临时目录再评审，并在报告中记录解压位置）
  - 解压安全：禁止路径穿越（如 `../`）；避免覆盖用户已有文件；必要时先让用户确认解压位置。

可选补充（用户未给时不要强行假设）：

- `focus`：优先关注某一维度（如“创新性/可行性/研究基础”）
- `output_path`：输出文件路径（默认见“输出”）
- `style`：口吻偏好（如“严格/温和/非常具体”）
- `grant_type`：项目类型（如“青年基金/面上项目”）
- `funding_amount`：项目总经费（若用户明确给出，以用户信息为准）
- `panel_count`：评审组数量（每组固定 7 位专家）
  - 默认值见 `config.yaml:parallel_review.default_panel_count`
  - 上限见 `config.yaml:parallel_review.max_panel_count`

## 输出

- 默认输出文件名见 `config.yaml:output_settings.default_filename`，默认写入标书目录下：`./{default_filename}`。
- 若用户指定 `output_path`，以用户为准；但当路径不可写/目录不存在时应 fail-fast 并提示用户更换路径。
- 并行模式下输出“专家共识 + 独立观点 + 汇总建议”；可按配置附带每位专家原始意见。
- 并行模式下建议将各组原始评审整理为最终交付文件：`./{panel_dir}/G{组号}.md`（`panel_dir` 见 `config.yaml:output_settings.panel_dir`）。
- 中间过程文件默认隐藏到 `config.yaml:output_settings.intermediate_dir`（默认 `.nsfc-reviewers/`），避免根目录出现大量计划/日志/并行运行环境。

## 工作流（执行规范）

### 读取配置（强制）

开始前先读取本技能目录下的 `config.yaml`，并将以下配置作为执行时的单一真相来源：

- `review_dimensions`：评审维度、权重、要点与常见问题（作为检查清单）
- `severity_levels`：P0/P1/P2 分级口径（用于分级）
- `review_grades`：等级与建议（仅在用户需要时输出）
- `stage_assessment`：函评/会评阶段判断的输出开关、二元标签与判断口径
- `funding_context`：青年/面上等常见资助额度区间，以及“资助受限妥协”如何写入报告
- `proposal_files.patterns/exclude`：标书文件识别规则
- `output_settings`：输出文件名、面板目录、中间过程隐藏策略与章节开关
- `parallel_review`：并行评审开关、专家画像、聚合策略

### 阶段一：前置检查（Fail Fast）

1. 校验输入路径存在且可读；若是目录，先按 `proposal_files` 规则筛选出待读文件列表。
2. 若 `.tex` 文件数量为 0：直接报错并请求用户提供正确路径/文件。
3. 若文件数量异常多/目录明显包含大量无关文件：先请用户确认评审范围（避免读错目录/读太多）。

推荐的确定性做法（避免“漏扫子目录 / 误扫中间目录 / 扫到交付产物”）：

```bash
# 列出将被纳入评审的 .tex 文件（递归扫描，并自动跳过 panels/、.nsfc-reviewers/、.parallel_vibe/）
python3 <nsfc_reviewers_path>/scripts/list_proposal_files.py --proposal-path <proposal_root>

# 可选：限制最大文件数（超限退出码=3）
python3 <nsfc_reviewers_path>/scripts/list_proposal_files.py --proposal-path <proposal_root> --max-files 200
```

### 阶段二：通读与结构化理解

1. 按章节顺序快速通读，提取“项目主题/科学问题/假说/目标/技术路线/创新点/研究基础/团队与条件/预期成果”。
2. 生成“标书结构索引”（只需到章节级别），作为后续引用的定位锚点。
3. 识别资助上下文：优先采用用户明确给出的 `grant_type` / `funding_amount`；否则再从目录名、标题页、正文中谨慎识别“青年/面上”等类型。
4. 仅当资助上下文有明确证据时，才使用 `config.yaml:funding_context` 中的常见额度区间辅助判断；若无法确认项目类型，不得硬套“青年 30–40w / 面上 50–60w”。

### 阶段三：并行多组评审（优先）或单组模式（退化）

#### 前置判断

1. 计算 `effective_panel_count`：优先用户输入 `panel_count`，否则使用 `parallel_review.default_panel_count`。
2. 将 `effective_panel_count` 限制在 `[1, parallel_review.max_panel_count]`。
3. 若任一条件成立，直接走单组模式：
   - `parallel_review.enabled == false`
   - `effective_panel_count == 1`
   - 找不到 `parallel-vibe` 脚本

#### parallel-vibe 脚本路径发现顺序

按顺序查找以下路径，命中即使用：

1. `~/.claude/skills/parallel-vibe/scripts/parallel_vibe.py`
2. `~/.codex/skills/parallel-vibe/scripts/parallel_vibe.py`
3. `<当前仓库>/parallel-vibe/scripts/parallel_vibe.py`

若全部不存在：记录警告并退化为串行模式，不中断整体评审。

#### 并行模式步骤

0. **准备中间目录结构（强烈建议）**：

```bash
mkdir -p <proposal_root>/<intermediate_dir>/{logs/plans,snapshot}
```

   - 其中 `<intermediate_dir>` 对应 `config.yaml:output_settings.intermediate_dir`（默认 `.nsfc-reviewers`）。

1. **构造 Master Prompt**（由宿主 AI 完成）：
   - 从 `references/expert_*.md` 读取 7 位专家画像（对应 `config.yaml:parallel_review.reviewer_personas[*].prompt_file`）
   - 从 `references/master_prompt_template.md` 读取 master prompt 模板
    - 注入上下文：阶段二产出的“标书结构索引 + 关键信息摘要”
    - 注入统一质量门槛：问题分级、证据锚点、输出格式
    - 注入独立性约束：每位专家只做独立判断，不假设其他专家意见
   - 注入输出约束：将评审组输出写入当前 thread 的 `workspace/` 根目录下的 `config.yaml:parallel_review.panel_output_filename`
    - 替换模板占位符：将 `{panel_output_filename}` 替换为 `config.yaml:parallel_review.panel_output_filename`
   - 将 master prompt 落盘到一个临时文件（推荐放在 `<proposal_root>/<intermediate_dir>/logs/` 下，便于追溯且不污染根目录），记为 `<master_prompt_path>`
2. **生成 parallel-vibe 计划文件（强制）**：
   - 原因：避免在 CLI 里转义超长 prompt；并避免 `parallel-vibe --prompt` 的自动拆分逻辑（本技能需要“同一 master prompt 在 N 个独立工作区重复执行”）。
   - 优先使用本技能自带脚本生成计划文件：

```bash
python3 <nsfc_reviewers_path>/scripts/build_parallel_vibe_plan.py \
  --panel-count <effective_panel_count> \
  --master-prompt-file <master_prompt_path> \
  --out <plan_json_path>
```

   - 若无法使用脚本，则手工生成 `plan.json`（最小结构）：

```json
{
  "plan_version": 1,
  "prompt": "nsfc-reviewers parallel panels",
  "threads": [
    {
      "thread_id": "001",
      "title": "Panel G001",
      "runner": { "type": "<config:parallel_review.runner>", "profile": "<config:parallel_review.runner_profile>", "model": "", "args": [] },
      "prompt": "<master_prompt>"
    }
  ],
  "synthesis": { "enabled": false }
}
```

3. **调用 parallel-vibe（基于 plan-file）**：

- 推荐先在 `<proposal_root>/<intermediate_dir>/snapshot/` 下准备一份标书快照（如 `proposal_snapshot/`），并将其作为 `--src-dir`，以避免把 `.nsfc-reviewers/`、`panels/` 等中间/交付目录再次复制进各 thread 的 `workspace/`。
- 最小做法：将“待评审标书目录”复制到 `snapshot/` 下，并排除中间/交付目录（具体命令依平台工具而定；原则是：快照目录应只包含标书源文件）。

```bash
python3 <parallel_vibe_path> \
  --plan-file <plan_json_path> \
  --src-dir <proposal_snapshot_root_or_proposal_root> \
  --out-dir <proposal_root>/<intermediate_dir> \
  --timeout-seconds <config:parallel_review.timeout_seconds> \
  --no-synthesize
```

4. **收集并校验各组输出**：
   - 从每个 thread 的 `workspace/` 中读取 `panel_output_filename`
   - 典型路径（运行结束但尚未整理输出时）：`<proposal_root>/<intermediate_dir>/.parallel_vibe/<project_id>/<thread_id>/workspace/<panel_output_filename>`
   - 若你已执行“阶段五：输出整理”，则 parallel-vibe 环境通常位于：`<proposal_root>/<intermediate_dir>/parallel-vibe/<project_id>/...`
   - `parallel-vibe` 会在 stdout 打印本次 `project_root` 路径；优先以该路径为准
   - 若个别 thread 缺失输出，记录缺失并继续聚合已完成结果（fail-soft）
   - 建议将每组最终评审报告复制/整理为最终交付文件：`<proposal_root>/{panel_dir}/G{thread_id}.md`

#### 单组模式步骤（退化）

1. 读取 `references/expert_*.md` 获取 7 位专家画像（创新/方法/基础/严格/建设性/科学意义/清晰度）
2. 模拟并行流程：让 7 位专家依次完成“独立评审”（不得相互参考）
3. 执行组内聚合（共识识别/严重度升级/去重合并）
4. 输出单组评审组报告到 `panel_output_filename`

### 阶段四：聚合、排序与可选结论

#### 跨组聚合（并行多组模式）

1. 从 `references/aggregation_rules.md` 读取跨组聚合规则。
2. 交叉比对 N 组 `panel_review.md`，识别同一问题的不同表述。
3. 跨组共识门槛：至少 `ceil(N * consensus_threshold)` 组指出 → 跨组共识（阈值见 `config.yaml:parallel_review.aggregation.consensus_threshold`）。
4. 严重度二次升级：跨组共识问题 P2→P1→P0（P0 不再升级）。
5. 合并重复问题，保留最完整的证据锚点与可执行建议。
6. 独立观点保留并标注来源组（如“来自组 G001”）。
7. 结果按 P0→P1→P2 输出，并给出最小可行修改序列。
8. 若 `keep_individual_reviews == true`，附录保留各组原始评审报告。

#### 单组汇总

输出“修改建议汇总”，按 P0→P1→P2 排序，并给出最小可行修改序列。

#### 资助额度约束识别（硬规则）

当你评审“研究内容设计偏弱 / 研究方法验证链条偏短 / 样本规模偏小 / 平台建设不完整 / 仅做到最小可行验证”这类问题时，必须先判断它是否与项目资助额度约束有关。

硬规则：

1. **先区分“设计错误”与“受限妥协”**：若短板明显来自青年基金、面上项目等有限资助框架下的现实取舍，不得直接把它写成“申请人能力不足”或“设计偷懒”。
2. **可以指出缺陷，但必须写明根因**：报告中要明确说明“受基金所限，此处设计存在缺陷/偏弱”，并解释为什么该缺陷与资助额度约束有关。
3. **必须补充理想完整版**：凡是归因为资助受限的短板，都要同时写出“若资助不受限时，一个更完整的设计应该怎样做”，帮助用户看到完整版目标。
4. **严重度按科学闭环判定**：若受限设计虽偏弱但仍能支撑核心科学问题成立，通常按 P1/P2 处理；若已经导致核心假说无法有效检验、关键证据链无法闭环，则仍可判为 P0/P1，但必须说明“根因与资助约束相关”。
5. **资助受限不是免责条款**：阶段判断仍然只看“当前版本今天送审能否过”；你只是要把问题说准确，而不是替当前版本免责。

#### 阶段性过会判断（默认输出）

你必须在最终 report 中新增“阶段判断（基于当前版本直接送审）”章节；除非用户明确要求省略，否则默认输出。

硬规则：

1. **必须基于当前版本判断**：按“如果今天就提交这份标书”来判断，不能假设后续还会修改。
2. **必须给出二元结论**：对函评、会评分别明确写 `给过` 或 `不给过`；不允许只写“边缘”“不好说”“看情况”。
3. **不确定性用把握度表达**：若存在摇摆，可补充 `判断把握：高/中/低`，但不能替代二元结论。
4. **会评严于函评**：若判断“函评不给过”，则“会评”必须同步判为“不给过”；若“函评给过”，仍可因相对竞争力不足而判“会评不给过”。
5. **必须说明依据**：每个阶段至少给出 2–3 条关键理由，优先引用 P0/P1 问题与跨组共识。
6. **若判不给过，必须指出翻盘关键**：用 1–3 条最关键修改动作告诉用户“先改什么，最可能把结果翻过来”。
7. **涉及资助受限时要准确归因**：如果关键短板与经费上限有关，可据实写入判断依据；但仍要基于当前可提交版本给出 `给过 / 不给过` 结论。

建议判断口径：

- **函评**：重点看独立阅读时，创新性、科学问题、技术路线与研究基础能否迅速成立，是否足以让多数同行专家给出“建议资助”。
- **会评**：在函评基础上再看相对竞争力、亮点鲜明度、答辩/讨论抗压性，以及短板是否会在会上被放大。
- **P0 兜底规则**：若仍存在未缓解的结构性 P0，默认函评/会评均倾向 `不给过`。

#### 可选综合结论

若用户还要求“综合评分/资助建议”，可额外输出；但不能替代“函评/会评给不过”判断章节。

### 阶段五：输出整理（强制执行）

**重要性**：本阶段是确保输出可追溯的关键步骤，**不可跳过**。当 `config.yaml:output_settings.enforce_output_finalization == true` 时，你不得在未完成本阶段的情况下结束评审。

**目标**：最终交付清晰可见；中间过程统一托管到 `config.yaml:output_settings.intermediate_dir`（默认 `.nsfc-reviewers/`），避免根目录出现计划/日志/并行环境等杂项。

#### 前置检查（按顺序执行）

1. 计算并确认 `effective_panel_count`（见阶段三）。
2. 判断本次评审模式：
   - 若 `effective_panel_count > 1` 且你实际调用了 `parallel-vibe`（或发现 `.parallel_vibe/` 运行环境）→ 视为“并行模式”
   - 否则 → “串行模式”（仍必须创建最小中间目录与日志）

#### 推荐做法：使用脚本自动化输出整理（确定性，强烈推荐）

```bash
python3 <nsfc_reviewers_path>/scripts/finalize_output.py \
  --review-path <proposal_root> \
  --panel-count <effective_panel_count> \
  --intermediate-dir <config:output_settings.intermediate_dir> \
  --apply
```

> 不加 `--apply` 为 DRY-RUN：只打印将执行的动作，不会改动文件。

#### 手动整理（脚本不可用时的 fallback）

并行/串行都必须至少创建最小目录结构：

```bash
mkdir -p <proposal_root>/<intermediate_dir>/{parallel-vibe,logs/plans,snapshot}
```

并行模式：将 `.parallel_vibe/` 的 **项目目录**迁移到 `<intermediate_dir>/parallel-vibe/`（兼容两种来源位置）：

```bash
# 1) 优先从 <proposal_root>/<intermediate_dir>/.parallel_vibe/ 迁移（parallel-vibe --out-dir 指向 intermediate_dir 时常见）
if [ -d "<proposal_root>/<intermediate_dir>/.parallel_vibe" ]; then
  mv "<proposal_root>/<intermediate_dir>/.parallel_vibe/"* "<proposal_root>/<intermediate_dir>/parallel-vibe/" 2>/dev/null || true
  rmdir "<proposal_root>/<intermediate_dir>/.parallel_vibe" 2>/dev/null || true
fi

# 2) 兼容旧实例：从根目录 .parallel_vibe/ 迁移
if [ -d "<proposal_root>/.parallel_vibe" ]; then
  mv "<proposal_root>/.parallel_vibe/"* "<proposal_root>/<intermediate_dir>/parallel-vibe/" 2>/dev/null || true
  rmdir "<proposal_root>/.parallel_vibe" 2>/dev/null || true
fi
```

迁移日志与计划文件（仅在存在时执行）：

```bash
mv "<proposal_root>/master_prompt.txt" "<proposal_root>/<intermediate_dir>/logs/" 2>/dev/null || true
mv "<proposal_root>"/plan*.json "<proposal_root>/<intermediate_dir>/logs/plans/" 2>/dev/null || true
mv "<proposal_root>/proposal_snapshot" "<proposal_root>/<intermediate_dir>/snapshot/" 2>/dev/null || true
```

#### 验证清单（执行后自检，未通过不得结束）

- [ ] `<proposal_root>/<intermediate_dir>/` 已创建，且至少包含 `logs/` 与 `logs/plans/`
- [ ] 若为并行模式：`<proposal_root>/<intermediate_dir>/parallel-vibe/` 下可看到 `<project_id>/...` 运行环境
- [ ] `master_prompt.txt`（或其副本）可在 `<proposal_root>/<intermediate_dir>/logs/` 中找到
- [ ] 最终交付仍位于根目录：`{default_filename}` 与 `{panel_dir}/G*.md`（无关中间文件不应散落在根目录）

## 报告格式（硬门槛）

对每条 P0/P1 问题，必须包含至少一个“证据锚点”：

- `证据锚点`：文件名 + 章节标题/关键句（可选行号）
- `现象`：为什么这是问题（不要空泛）
- `影响`：会如何影响评审判断/可行性/说服力
- `建议`：可执行的修改方案（优先给“怎么改”和“改到什么程度算够”）
- `验证`：改完如何自检（例如“补一张路线图”“补一段对照坐标系”“补一条预实验证据链”）

若该问题与资助额度约束明显相关，还必须额外补充：

- `资助约束说明`：说明这是青年/面上等有限资助框架下的现实妥协，而非纯粹的思路错误
- `完整设计参考`：说明若资助不受限，一个更完整的研究设计应补哪些关键实验、样本、队列、平台或验证层级

并行模式建议结构：

```markdown
# 国自然标书评审意见（N 组独立专家）

## 评审配置
- 评审组数：N 组
- 每组专家：7 位
- 总专家人次：N×7 人次

## 阶段判断（基于当前版本直接送审）
### 函评
- 结论：给过 / 不给过
- 判断把握：高 / 中 / 低
- 评审组倾向：X/N 组判给过，Y/N 组判不给过
- 主要依据：...
- 翻盘关键（仅在不给过时必写）：...

### 会评
- 结论：给过 / 不给过
- 判断把握：高 / 中 / 低
- 评审组倾向：X/N 组判给过，Y/N 组判不给过
- 主要依据：...
- 翻盘关键（仅在不给过时必写）：...

## 跨组共识（多组一致指出）
### P0 级

## 独立观点（单一组提出）
### 来自 组 G001

## 修改建议汇总

## 附录：各组原始评审报告（可选）
```

若某条问题属于“受资助额度限制的设计妥协”，应在对应问题下显式写出“资助约束说明 / 完整设计参考”，而不是只笼统批评“方案偏弱”。

## 使用示例

用户输入：
```text
请评审 /path/to/nsfc_proposal 这个国自然标书，并把意见保存到 /path/to/output.md
```

## 配置参数

详见 `config.yaml`：

- `review_dimensions`：评审维度配置（权重/要点/常见问题）
- `severity_levels`：问题严重程度定义
- `review_grades`：评审等级与建议（可选输出）
- `funding_context`：资助额度约束识别规则（青年/面上常见额度区间、报告写法与归因边界）
- `proposal_files`：标书文件识别规则
- `output_settings`：输出设置（默认文件名/面板目录/中间目录/章节开关；以及输出整理校验：`enforce_output_finalization` / `warn_missing_intermediate` / `validation_level`）
- `parallel_review`：并行多组评审配置（开关/组数/专家画像引用/跨组聚合策略）
