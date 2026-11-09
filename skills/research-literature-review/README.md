# Research Literature Review（相关性驱动版）— 用户使用指南

本 README 面向**使用者**：如何触发并正确使用 `research-literature-review` skill。执行指令与硬性规范在 `SKILL.md`；默认参数在 `config.yaml`。

版本以 `config.yaml:skill_info.version` 为唯一来源。

维护者：回归测试统一放在 `scripts/test_*.py`，运行方式见[维护与回归测试](#维护与回归测试)。

## 参考资料与读取时机

`references/` 保存按阶段读取的现行规范，无需在每次任务开始时全部加载。执行流程由 `SKILL.md` 定义，可配置默认值以 `config.yaml` 为准；参考资料展开对应阶段的细节。

| 资料 | 用途与读取时机 |
| --- | --- |
| [查询生成模板](references/ai_query_generation_prompt.md) | 检索前生成符合查询契约的 JSON |
| [评分与选文说明](references/ai_scoring_prompt.md) | 评分时确定相关性、子主题与数据抽取要求，说明软预算选文边界 |
| [专家写作指南](references/expert-review-writing.md) | 写作时形成综合判断，核对证据与引用 |
| [TeX 章节模板](references/review-tex-section-templates.md) | 新建或调整稿件结构、表格及版式时读取 |
| [多语言指南](references/multilingual-guide.md) | 用户明确要求翻译时读取 |

历史评分迁移说明已合并至本 Skill 的 `CHANGELOG.md`，不再单独维护多份现行规则。检索引擎及参数由必需依赖 `research-literature-search` 管理，review 不维护第二套引擎优先级。

检索依赖：`research-literature-search` `rls.v1`，最低版本见 `config.yaml:dependencies.required_skills`。review 负责评分、选文、写作与 PDF/Word 导出；阶段 1/2 只消费 search 的 manifest bundle，不再复制 provider 或二次 canonical 去重。独立安装时可用 `--search-skill-root` 指定依赖路径。

Python 依赖及版本约束统一维护在 `config.yaml:dependencies.python`，环境准备时按该列表安装；完整运行还需 Python 3.11+、XeLaTeX、BibTeX 和 Pandoc。

## 文稿质量与完整交付

默认生成紧凑的学术文稿：标题、摘要与正文连续排版，自动章节编号；Word 从 Heading1 开始，使用黑色标题、统一正文样式和数字引文。封面、目录或其它指定版式按用户要求处理。新稿正文片段可这样排版（Bib 先放到输出目录）：

```bash
python scripts/render_review_template.py --title "研究进展" --body body.tex --bib 主题_参考文献.bib --output 主题_review.tex
```

证据卡默认保留完整摘要和已有提取字段，不再用前 800 字符代替整段结果。每个关键结论仍需核对研究身份、人群、终点、数字及不确定性；摘要覆盖率不等于全文阅读，相关性评分不等于证据等级。

综述正文默认直接呈现研究发现、争议与证据边界。摘要、引言及其它正文位置不介绍本次综述如何检索、筛选和选文，不附带“透明检索支持”或“未进行双人筛选/GRADE”等制作过程声明，也不把它们挪到文稿脚注、图表或附录。这些信息留在工作条件、Search Log 和配套报告中，检索及证据核验照常进行。原始研究的设计、偏倚和适用范围仍需讨论。仅用户或目标期刊明确要求方法报告（如 PRISMA）时才另设方法章节或补充材料；仅称“系统综述”不自动加入过程叙述，也不据此宣称符合报告规范。

自动报告只说明实际检查范围，未经执行的论断核验、全文审计、PDF/Word 目视与复现检查标为未验证。编译器检测缺字和未解析引用，保留最终日志；Word 显示 Pandoc 警告。交付前仍需实际比较正文、标题、图表与书目，并在工作条件中记录检查位置。

迁移已有自动化时：默认标准运行会交完整包，若仍只需阅读文件使用 `--readers-only`；直接 Python 调用 `publish_deliverables` 保留 `include_supporting=False` 默认，但两种模式都要求非空 PDF/Word 配对。图表、片段和用户指定的本地自定义资源应放在 supporting 内，以静态相对路径引用；动态宏路径先具体化。内置 BST 直接引用宿主机 Skill 的绝对路径，系统 TeX 包与样式由发行版提供，均不复制到成品。恢复已完成运行会重新检查并导出当前稿件，不沿用旧结果证明新文件通过。`--force-pass` 已停用。

Word CSL 复用仓库既有 Vancouver 样式，版权及 CC BY-SA 3.0 说明保留在 `references/latex-template/review-numeric.csl`；PDF 使用现有 GB/T BST，两者引文编号均按首次出现顺序，书目排版不承诺逐像素一致。Word 保留摘要标签；默认宋体在支持 `fc-list` 的环境中可回退到本机已安装的宋体或 Noto/思源宋体，用户自定义字体保持原样。接收端仍需安装相应字体，跨系统打开后应复核换行和表格。

综述成品不含 README，使用说明和限制写入已有的工作条件。仓库中本 Skill 的 README 与任务工作区内部 README 各自保留，不进入成品目录。

## 旧名兼容

- 当前正式名：`research-literature-review`
- 旧名：`systematic-literature-review`
- 兼容状态：旧名 prompt 暂时仍会触发本 skill；安装新版本时系统级旧目录会被清理，不再保留 wrapper 目录。
- 历史工作区：`.systematic-literature-review/` 保持不变，这是稳定产物目录，不等同于 skill 新名称。

## 快速开始

```text
请使用 research-literature-review skill 写一篇“HER2-ADC 在乳腺癌中的研究进展”的 Premium 级综述。
输入：主题与时间范围（近 2023–2025 年为主，更早但特别重要的研究也可纳入）
输出：PDF、Word，以及可复核的检索与引用支持材料
另外，还有下列参数约束：
- 结构要求：增加“未来 3 年研究方向”小节
- 输出目录：`./review-deliverables/`
```

技能会先生成并保存 5–25 条查询，再启动检索。你不需要猜 `queries_{stem}.json` 之类的内部文件名。

## 设计理念
- AI 先生成并显式保存查询 JSON → 多源检索 → 去重 → 标题/摘要 1–10 分相关性与证据角色 → 相关性阈值与软预算选文 → **自动生成"综/述"字数预算（70% 引用段 + 30% 无引用段，3 次采样均值，空 ID 行支持无引用大纲）** → 资深领域专家自由写作。
- 档位影响默认字数与参考预算（可覆盖），支持三档：**Premium（旗舰级）**、**Standard（标准级）**、**Basic（基础级）**。参考范围是预算和上限；合格文献不足时不会用低相关材料填满。
- `--purpose novelty-check` 面向研究想法查新，只运行到强近邻选文与缺口记录，不自动生成长篇正文、PDF 或 Word。
- 强制导出 PDF/Word；硬校验：必需章节、字数 min/max、相关性驱动的引用范围、\cite 与 bib 对齐、子主题与摘要可用性；已有预算时校验覆盖率/总和，报告生成失败也会阻止阶段完成。
- **最高原则**：AI 不得偷懒或短视地为了速度做错误事；不确定必须说明；最终润色仅做衔接与结构调整，不得改动文献题目/摘要所含事实/数字。
- **稳健性**：查询缺失、冲突、格式错误或数量越界时默认停止；`--resume-from` 始终先加载 checkpoint，并校验查询文件是否仍存在、SHA-256 指纹是否变化；Bib 自动转义 `&`、补充缺失字段并大小写无关去重 key。
- **多语言支持**：支持将综述翻译为多种语言（en/zh/ja/de/fr/es），尝试修复 LaTeX 渲染错误，保留引用和结构不变。详见[多语言支持](#多语言支持)。

## 多查询输入契约

### 支持的 JSON

推荐使用带理由的对象格式：

```json
{
  "queries": [
    {
      "query": "HER2 antibody drug conjugate breast cancer clinical trial",
      "rationale": "核心临床证据"
    }
  ]
}
```

也支持对象数组和字符串数组。空查询会被剔除；有效查询默认至少 5 条、至多 25 条。

### 输入来源优先级

| 优先级 | 来源 | 适用场景 |
|---|---|---|
| 1 | `--query-file` / `--queries` | 推荐；路径明确，runner 会复制到当前 run 的 `input/queries.json` |
| 2 | `<work-dir>/input/queries.json` | 两步式准备后填写 |
| 3 | `input/queries_{stem}.json` | 当前 run 的兼容文件 |
| 4 | `output/artifacts/queries_{stem}.json` | 当前 run 的旧版产物 |
| 5 | 唯一历史 stem 文件 | 只读兼容，不再生成这种名称 |

自动发现多个文件会停止并列出冲突。发现文件但 JSON 无效或数量越界也会停止，不会改跑单查询。

### 搜索模式如何审计

`pipeline_state.json` 和 `search_log_*.json` 会明确记录：

- `search_mode`：`multi_query` 或 `single_query`
- `query_source`
- `requested_query_count` / `accepted_query_count`
- `query_file_sha256`（state）
- `fallback_reason`

因此，“单查询返回很多结果”不会再被误认为多查询成功。

### Search manifest 交接

阶段 1 会在当前 run 的 `output/artifacts/search_bundle_{stem}/` 生成并校验：

```text
manifest.json
candidates_raw.jsonl / candidates_normalized.jsonl / candidates_deduped.jsonl
provenance.jsonl / dedupe_map.json / search_log.json
```

`manifest.json` 记录 `rls.v1`、候选 schema、查询 SHA-256、provider attempts、截断/失败统计和每个 artifact hash。阶段 2 仅做完整性验证并保留旧 `2_dedupe` checkpoint 名称；缺依赖、契约不兼容、文件删除或 hash 改变时 fail-closed。

review 与 search 可能在同一 Python 进程内运行；search 的查询解析与 manifest 校验均使用独立命名的 `rls_contract.py`，旧 `query_contract.py` 保留兼容导入，避免误用 review 查询结构而丢失 `query_id`。

## 本地缺陷修复后的运行边界

预算生成可读取 Skill 自带的只读配置，任务自定义配置须位于当前工作目录内；候选、大纲和输出仍执行路径隔离。预算校验新增 `--review-level standard|basic|premium`，流水线会传递当前档位与目标字数，独立调用也可用 `--target-words` 覆盖。

标准综述排除显式标记 `do_not_cite=true` 的记录，保留原评分审计，并在选文理由中统计此类候选；查新模式仍允许把它们保留为待核验线索。Bib 生成会将独立的字面换行转义正规化为空格，并保留已有 LaTeX 转义和命名宏。

PDF 编译将内置 BST 绑定到当前宿主机 Skill 的 `references/latex-template/`，TeX 直接引用该绝对路径（省略 `.bst` 后缀）；系统 BST 通过 `kpsewhich` 查找，两者均不复制到成品。换机或 Skill 安装路径变化时，更新 TeX 引用后重编译。引用分布检查支持 `citep`、`citet` 等命令、可选参数和跨行花括号，忽略注释中的引用。历史 JSONL 去重入口按文件行读取，保留摘要内合法的 Unicode 行分隔符。

## 字数预算的设计哲学

`word_budget_final.csv` 采用**柔性指导**而非**刚性约束**的设计：

- **为什么不严格限制？** 如果 AI 被强制按每篇文献的精确字数写作，会产生机械、割裂的文本，失去学术综述应有的流畅性和连贯性。
- **实际作用**：字数预算作为 AI 写作时的**重要参考**，帮助 AI 理解各章节的相对权重和文献的重要性排序，但允许 AI 根据内容需要灵活调整。
- **预期偏差**：各章节实际字数与预算偏差 ±30% 是正常的，这正是"资深领域专家自由写作"的体现。
- **硬性约束**：总字数范围与引用上限依配置检查，引用下限按实际合格选文调整；结构与资料可用性另行检查，篇幅不能证明内容质量。

这种设计让 AI 既有章法可循，又保留了人类专家写作时的自然节奏和判断力。

## 关于摘要补全功能

### OpenAlex 摘要缺失现状

基于对 51 个系统综述项目、共 24,315 篇文献的统计分析，我们发现从 OpenAlex 下载的文献中：

| 指标 | 数值 | 百分比 |
|------|------|--------|
| 总文献数 | 24,315 篇 | 100% |
| **缺失摘要的文献** | 6,929 篇 | **28.5%** |
| 有摘要的文献 | 17,386 篇 | 71.5% |

**核心发现**：近三分之一的文献在 OpenAlex 中没有摘要信息，且不同主题的缺失率差异显著（3.8% - 44.6%）。

### 摘要补全实际效果

基于对 23 个系统综述项目的统计分析，摘要补全功能的实际效果如下：

| 指标 | 数值 | 说明 |
|------|------|------|
| 分析项目数 | 23 个 | 系统综述项目 |
| 原本缺失摘要的文献 | 3,496 篇 | 从 OpenAlex 下载时缺失 |
| 成功补全摘要 | 755 篇 | 通过其他数据源补全 |
| **总体补全率** | **21.6%** | 相对于原本缺失的文献 |
| 补全率范围 | 0% - 87.3% | 不同项目差异很大 |
| 高补全率项目 (>50%) | 2 个 | ICI-marker-01 (87.3%)、cancer-transcriptomic-subtype-01 (59.1%) |
| 零补全率项目 | 11 个 | 约 48% 的项目未能补全任何摘要 |

**关键发现**：
- 约 21.6% 的缺失摘要能够成功补全
- 补全效果高度依赖于文献领域和可获取性
- 即使补全率不高，补全的摘要对高相关文献的评估仍有重要价值
- 免费数据源（Semantic Scholar 等）存在访问限制，导致部分项目补全失败

### 为什么默认开启摘要补全？

尽管摘要补全会延长整体工作时间（通常增加 20-40%），但我们**强烈建议保持此功能开启**，理由如下：

1. **提升文献评估准确性**：完整的摘要是 AI 进行相关性评分（1-10 分）和子主题分组的关键依据。缺失摘要会导致评分偏差，可能错误排除高相关文献或纳入低相关文献。

2. **保证综述质量**：没有摘要的文献难以进行深度分析和批判性评估，直接影响综述的学术价值和可信度。

3. **性价比权衡**：
   - 关闭摘要补全：节省时间，但约 28.5% 的文献缺失摘要，影响评估准确性
   - 开启摘要补全：延长 20-40% 时间，平均可补全 21.6% 的缺失摘要，显著提升文献覆盖质量
   - 实际价值：即使只能补全部分摘要，这些摘要往往对应高相关文献，对综述质量影响 disproportionately 大

4. **不可逆性影响**：文献筛选阶段的错误会通过后续所有环节放大，后期补救成本远高于前期摘要补全成本。

### 配置说明

在 `config.yaml` 中通过以下参数控制：

```yaml
search:
  abstract_enrichment:
    enabled: true          # 是否启用摘要补齐（建议保持开启）
    stage: post_selection  # 默认：仅对 selected_papers 补齐，避免检索阶段全局补齐导致慢与 cache 膨胀
    max_papers_total: 200
    retry_rounds: 3
    min_abstract_chars: 80
    timeout_seconds: 3

cache:
  api:
    enabled: true          # 默认开启：提升稳定性、降低重复运行成本
    mode: minimal          # 默认：不缓存 OpenAlex 原始分页响应；需要更强可复现性可切 full
```

**建议**：除非时间极端受限且可接受质量损失，否则请保持 `enabled: true`。

## 档位选择指南

### 三档位对照表

| 档位 | 字数范围 | 参考文献数 | 典型场景 | PDF 页数 | 别名 |
|------|---------|-----------|---------|---------|------|
| **Premium（旗舰级）** | 10000–15000 | 80–150 | • *Nature Reviews* 级别综述<br>• *Chemical Reviews* 级别综述<br>• 专著式综述 | 16–25 页 | 旗舰级、顶刊级、高级 |
| **Standard（标准级）** | 6000–10000 | 50–90 | • 学位论文 Related Work<br>• 普通期刊综述<br>• NSFC 标书立项依据<br>• 项目提案 | 10–16 页 | 标准级、常规 |
| **Basic（基础级）** | 3000–6000 | 30–60 | • 快速调研<br>• 课程作业<br>• 会议论文 Related Work<br>• 入门了解领域 | 5–10 页 | 快速级、基础级、入门 |

### 如何选择合适的档位？

| 你的需求 | 推荐档位 | 理由 |
|---------|---------|------|
| 投稿 *Nature Reviews*、*Chemical Reviews* 等顶刊 | **Premium** | 符合顶刊深度与广度要求 |
| 学位论文的 Related Work 章节 | **Standard** | 多数导师接受此范围 |
| 普通期刊（非顶刊）发表综述 | **Standard** | 符合一般期刊要求 |
| NSFC 标书的"立项依据"部分 | **Standard** | 足够支撑科学问题阐述 |
| 快速了解一个新领域 | **Basic** | 快速生成，节省时间 |
| 课程作业或文献调研报告 | **Basic** | 符合课程要求，不超标 |
| 会议论文的 Related Work | **Basic** | 会议页数限制通常较严格 |

### 提示：覆盖默认参数

所有档位的字数和参考文献数均可通过提示词覆盖，例如：

```
请做"Transformer 在 NLP 中的应用"综述，标准级，正文 8000-10000 字，参考文献 70-90 篇。
```

## 提示词示例

> 子主题与段落配额由 AI 自动决定

### 最小可用
```
请用 research-literature-review 做主题"AI for protein design"的文献综述，基础级，近五年英文。
```

### 指定输出范围
```
请做"Transformer 在金融风控中的应用"综述，旗舰级，正文 12000-14000 字，参考文献 100-130 篇。
```

### 明确写作风格
```
请做"癌症免疫检查点抑制剂疗效预测生物标志物"的综述，旗舰级，字数范围默认，写作风格偏 Nature Reviews，子主题由你自动决定。
```

### 校验不够时的有机扩写
```
请在 {子主题名} 段内有机扩写，保持原主张和引用不变，只补充 2–3 条具体证据/数字/反例与衔接句；本段目标约 {目标字数} 字，当前不足 {差额} 字。原文如下：{原段落全文}
```

### 按预算写作（含无引用段落）
```
请读取 `.bensz-api/task-{yyyymmdd-hhmm}-{简短描述}/research-literature-review/{run-id}/output/artifacts/word_budget_final.csv`，引用段按每篇文献的“综/述”字数预算写，无引用段（文献ID为空，如摘要/结论/展望）按该行预算控制长度；可合并引用但需贴近预算总字数。
```

## 常见问题

### Q：没有查询文件，可以直接运行吗？

A：可以先用 `--prepare-only` 创建 `<work-dir>/input/queries.json`，填好后再从阶段 1 恢复。普通运行缺少有效查询时会停止。

### Q：外部编排器暂时只能提供主题，怎么办？

A：临时显式添加 `--allow-single-query-fallback`，并用 `--fallback-reason` 写明原因。Search Log 会带警告；这不是多查询模式。

### Q：resume 时查询文件被改过会怎样？

A：runner 会比较 state 中的 SHA-256；文件缺失或指纹变化时停止，不会静默发现另一个文件继续跑。

## 备选用法（脚本/硬编码流程）

### 已准备查询文件：直接运行

```bash
# 显式查询文件优先，并复制到当前 run 的 input/queries.json
python scripts/run_pipeline.py --topic "主题" --query-file ./queries.json --publish-dir ./review-deliverables
```

### 两步式：先准备，再恢复

```bash
# 步骤 1：只建立工作区与查询模板
python scripts/pipeline_runner.py --topic "主题" --work-dir ./review-run --prepare-only

# 步骤 2：填充 ./review-run/input/queries.json 后，从检索阶段继续
python scripts/pipeline_runner.py --resume ./review-run --resume-from 1 --publish-dir ./review-deliverables
```

### 显式单查询后备

```bash
# 仅用于外部编排器临时兼容；原因会进入 state 与 Search Log
python scripts/run_pipeline.py --topic "主题" --allow-single-query-fallback --fallback-reason "暂未提供多查询文件"
```

### 校验流程

- 阶段：`0_setup → 0.5_subtopics（写作前由 AI 给出并记录） → 1_search → 2_dedupe → 3_score → 4_select → 4.5_word_budget → 5_write → 6_validate（含结构、摘要可用性与已有预算校验） → 7_export`
- 校验：`validate_counts.py`（字数/引用 min/max）、`validate_review_tex.py`（必需章节 + cite/bib 对齐）
- 导出：`compile_latex_with_bibtex.py {topic}_review.tex {topic}_review.pdf`；`convert_latex_to_word.py ...`；`--template` 只追加资源搜索路径，不替换稿件版式。新稿用 `render_review_template.py` 应用原生学术模板；自定义完整 TeX 直接编译。

### 文件隔离

- `output/artifacts/` 保存候选库、评分、选文、字数预算、证据卡和校验 JSON；`output/reference/` 保存数据抽取表；`output/deliverables/` 保存内部生成的 PDF/Word，`output/deliverables/supporting/` 保存源码与支持性文件。
- `input/queries.json` 保存当前 run 的规范化查询输入；不要从其他 run 猜测或复用未声明路径。
- 正式目录由 `--publish-dir` 接收白名单文件，默认复制 PDF/Word、TeX、Bib、工作条件、验证报告及实际引用的相对图表/片段；内置和系统 BST 不随包复制；`--readers-only` 显式只交 PDF/Word，`--include-supporting` 保留兼容。缺必需文件、越界依赖或目标冲突会在写入前停止。
- 历史 `.systematic-literature-review/` 目录只能通过显式 resume/整理/迁移处理，不再作为新运行的默认路径。

## 关键文件
- `SKILL.md`：工作流、输入输出、最高原则与硬校验
- `config.yaml`：查询数量/后备策略、档位字数/参考范围和搜索默认参数
- `scripts/query_contract.py`：查询 schema、共享 stem 和 SHA-256 指纹
- `references/ai_scoring_prompt.md`：宿主 AI 直接评分与数据抽取，不提供关键词脚本评分后备
- `scripts/select_references.py`：按相关性阈值、证据角色和软预算选文，生成 Bib 与不足说明
- `scripts/plan_word_budget.py`：三次采样生成字数预算 run1/2/3 + final（含无引用空 ID 行）
- `scripts/validate_word_budget.py`：已生成预算时校验列/覆盖率/总和
- `scripts/update_working_conditions_data_extraction.py`：记录 score/subtopic 到数据抽取表

## 注意事项
- 默认章节：摘要、引言、3–7 个主体主题、讨论、展望、结论；用户或期刊另有要求时同步调整结构检查参数。
- 结构、计数、引文 key、摘要可用性和已有预算是自动检查；不再用任意成功字符、旧完成状态或文件存在性推断整体质量。语义证据核验与目视检查仍需执行者实际完成。
- 输出文件仍采用 LaTeX-first：`{topic}_review.tex/.bib → .pdf/.docx`。
- 字数不足时先检查遗漏的问题、比较与证据，必要时回到补检和规划阶段；不以重复限制句填字数，不得篡改文献事实/数字/元数据。
- resume 时查询文件缺失或 SHA-256 指纹变化会停止确认；不会静默换成另一查询来源。中文主题缺少英文 token 时仍会按既有搜索策略提示。

## 维护与回归测试

以下命令从仓库根目录执行。Skill 自带回归测试：

```bash
PYTHONDONTWRITEBYTECODE=1 python -m unittest discover -s skills/research-literature-review/scripts -p 'test_*.py'
```

联合运行仓库级回归时，将 `<本轮任务工作区>` 替换为当前任务目录：

```bash
PYTHONDONTWRITEBYTECODE=1 python -m pytest tests/test_review_quality_regression.py skills/research-literature-review/scripts tests/research-literature-review -q --basetemp <本轮任务工作区>/test-output -o cache_dir=<本轮任务工作区>/pytest-cache
```

真实导出测试需要 XeLaTeX、BibTeX 和 Pandoc；缺依赖时应报告跳过，不计为导出通过。版式变更还需渲染 PDF/Word 核对标题、中文、图表和参考文献；自动回归不能代替内容核验或真实长篇写作质量评估。

## WHICHMODEL - 模型选择最佳实践

本节由 `which-model` skill 自动调研生成，最后更新：2026-01-03

### 场景一：文献检索与相关性评分
- **推荐模型**：Claude Sonnet 4.5
- **推荐参数**：
  - 推理强度：medium
  - Thinking 模式：开
  - Temperature：0.3（确保评分稳定性）
  - Max Tokens：8192
- **理由**：文献评分需要理解学术论文的标题和摘要，进行语义相关性判断（1-10分）和子主题分组。Sonnet 4.5 在学术文本理解上表现优异，且性价比高，适合批量处理（50-200篇文献）。[来源：Anthropic 官方文档 - Claude Sonnet 4.5 在代码分析和学术理解上的性能提升]

### 场景二：综述正文写作（资深专家风格）
- **推荐模型**：Claude Opus 4.5
- **推荐参数**：
  - 推理强度：high
  - Thinking 模式：开
  - Temperature：0.7（平衡学术严谨性与表达流畅性）
  - Max Tokens：16384（支持长文本生成）
- **理由**：综述写作需要深度合成（Synthesis）、批判性评估和逻辑架构能力。Opus 4.5 在复杂推理和长文本生成上性能最强，能确保学术质量和连贯性。[来源：Claude AI in Academic Writing - Opus 在复杂学术任务上的优势]

### 场景三：引用一致性核查
- **推荐模型**：Claude Sonnet 4.5
- **推荐参数**：
  - 推理强度：medium
  - Thinking 模式：开
  - Temperature：0.1（最小化随机性，确保一致性）
  - Max Tokens：4096
- **理由**：引用对齐需要精确的语义匹配（正文片段 vs 题目/摘要），不需要复杂推理。Sonnet 4.5 在语义相似度任务上表现优异，且速度更快。[来源：Semantic Evaluation with Embeddings - Sonnet 在文本匹配任务上的表现]

### 场景四：快速调研（Basic 档位）
- **推荐模型**：Claude Haiku 4.5
- **推荐参数**：
  - 推理强度：low
  - Thinking 模式：关
  - Temperature：0.5
  - Max Tokens：4096
- **理由**：Basic 档位（3000-6000字，30-60篇文献）对深度要求较低，Haiku 4.5 能提供快速、经济的解决方案。[来源：Choosing the right model - 从 Haiku 开始的渐进式升级策略]

### 通用原则
1. **评分阶段用 Sonnet**：批量文献评分（50-200篇）需要平衡速度与准确性，Sonnet 4.5 是最佳选择
2. **写作阶段用 Opus**：综述正文生成需要最强推理能力和连贯性，Opus 4.5 值得额外成本
3. **核查阶段用 Sonnet**：语义匹配任务不需要最强推理，Sonnet 4.5 足够且更快
4. **快速任务用 Haiku**：Basic 档位或早期验证可用 Haiku 4.5 节省成本
5. **Thinking 模式建议**：学术任务（评分、写作、核查）都建议开启 Thinking 模式，以确保推理质量

### 更新记录
- 2026-01-03：初始调研，基于 Anthropic 官方文档和第三方评测

## 多语言支持

### 概述

research-literature-review 支持将综述正文翻译为多种语言，并尝试处理 LaTeX 渲染错误；输出仍须经过导出检查和人工目视复核。

### 支持的语言

| 语言 | 代码 | 关键词 |
|------|------|--------|
| 英语 | en | 英语、英文、English、en |
| 中文 | zh | 中文、汉语、Chinese、zh |
| 日语 | ja | 日语、日文、Japanese、ja |
| 德语 | de | 德语、德文、German、de、Deutsch |
| 法语 | fr | 法语、法文、French、fr、Français |
| 西班牙语 | es | 西班牙语、Spanish、es、Español |

### 使用示例

#### 日语综述
```
请用 research-literature-review 做"AI for protein design"的日语综述，旗舰级。
```

#### 德语综述
```
请用 research-literature-review 做"Transformer in NLP"的德语综述，标准级。
```

#### 法语综述
```
请做"癌症免疫治疗"的法语综述，旗舰级，12000-14000 字。
```

### 工作流程

1. **语言检测**：从用户输入中自动检测目标语言
2. **AI 翻译**：翻译正文内容，保留所有 `\cite{key}` 引用和 LaTeX 结构
3. **备份原文**：自动备份为 `{topic}_review.tex.bak`
4. **覆盖原 tex**：翻译后覆盖原 `{topic}_review.tex`
5. **智能修复编译**：循环编译直到成功或触发终止条件
6. **导出 PDF/Word**：成功后生成两种格式

### 错误处理

- **可修复错误**：自动修复或提示 AI 修复（缺少宏包、字体缺失、语法错误等）
- **不可修复错误**：立即停止并报告（文件权限、内存溢出等）
- **循环检测**：避免重复无效修复
- **超时保护**：单次编译 5 分钟，总计 30 分钟
- **失败兜底**：输出错误报告 + broken 文件，可恢复备份

### 恢复原文

如果翻译或编译失败，可以恢复原文：

```bash
python scripts/multi_language.py --tex-file review.tex --restore
```

### 详细文档

详见 [`references/multilingual-guide.md`](references/multilingual-guide.md)
