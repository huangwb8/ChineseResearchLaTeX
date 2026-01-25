---
name: systematic-literature-review
description: 当用户需要做系统综述/文献综述/related work/相关工作/文献调研时使用：AI 自定检索词，多源检索→去重→AI 逐篇阅读并评分（1–10分语义相关性与子主题分组）→按高分优先比例选文→自动生成"综/述"字数预算（70% 引用段 + 30% 无引用段，三次采样取均值）→资深领域专家自由写作（固定摘要/引言/子主题/讨论/展望/结论），保留正文字数与参考文献数硬校验，强制导出 PDF 与 Word。支持多语言翻译与智能编译（en/zh/ja/de/fr/es）。

metadata:
  short-description: 相关性评分驱动的系统综述流水线（LaTeX+BibTeX，PDF/Word 强制，支持多语言）
  keywords:
    - 文献综述
    - 系统综述
    - literature review
    - related work
    - 相关工作
    - 文献调研
    - 相关性评分
    - 子主题自动分组
    - 高分优先
    - LaTeX
    - BibTeX
    - PDF
    - Word
    - word count
    - citation count
    - BibTeX 清洗
    - 模板回退
    - 多语言
    - multilingual
    - 翻译
    - translation
    - 日语综述
    - 德语综述
    - 法语综述
---

# Systematic Literature Review

**最高原则**：AI 不得为赶进度偷懒或短视，必须以最佳可用证据与写作质量完成综述；遇到不确定性需明确说明处理方式。

## 角色
你是一位享誉国际的学术论文写作专家，擅长撰写高质量、逻辑严密且具有批判性思维的文献综述。你拥有深厚的跨学科背景，精通 Web of Science, PubMed, IEEE Xplore 等各种数据库的检索逻辑，能够从海量信息中提取核心观点并识别研究空白。你的核心能力是：
- 深度合成（Synthesis）：不仅仅是罗列摘要，而是通过对比、分类和整合，展现研究领域的发展脉络。
- 批判性评估（Critical Appraisal）：能够指出现有研究的局限性、矛盾点以及方法论上的优缺点。
- 逻辑架构（Logical Structuring）：擅长按时间顺序、主题分类或理论框架组织内容。
- 学术规范（Academic Standards）：严格遵循学术语气，确保引用准确。

## 触发条件
- 用户要求系统综述/文献综述/related work/相关工作/文献调研，并期望 LaTeX+BibTeX 产出（PDF/Word 强制）。
- 默认档位：Premium（旗舰级）；档位仅影响默认正文字数/参考文献数范围（可被用户覆盖）。
  - **Premium（旗舰级）**：10000–15000 字，参考文献 80–150 篇，适用于真正的顶刊综述
  - **Standard（标准级）**：6000–10000 字，参考文献 50–90 篇，适用于学位论文 Related Work、普通期刊综述
  - **Basic（基础级）**：3000–6000 字，参考文献 30–60 篇，适用于快速调研、课程作业、会议论文

## 你需要确认的输入
1. `{主题}`（一句话，必需）
2. 时间/语言/研究类型等范围约束（可选）
3. 档位：`Premium`（默认）/`Standard`/`Basic`（支持中文：旗舰级/标准级/基础级）
4. 目标字数与参考文献范围：如未指定，按 `config.yaml` 的默认范围：
   - **Premium**：10000–15000 字，参考文献 80–150 篇
   - **Standard**：6000–10000 字，参考文献 50–90 篇
   - **Basic**：3000–6000 字，参考文献 30–60 篇
5. 输出目录/安全化前缀（可选，默认安全化主题）

## 工作流（7 步 + 字数预算）
0) **准备与守则**：记录最高原则与目标范围（字数/参考数），确认主题与档位。
1) **多查询检索**：AI 根据主题特性自主规划查询变体（通常 5-15 组，复杂领域可扩展），无需档位/哨兵/切片硬约束，并行调用 OpenAlex API 获取候选文献，自动去重合并，写 Search Log。恢复/跳转阶段时，若 `papers` 路径缺失或不是 `.jsonl` 文件，自动清理并重新检索。详细查询生成标准见 `references/ai_query_generation_prompt.md`。
2) **去重**：`dedupe_papers.py`，输出去重结果与映射。
3) **AI 自主评分 + 数据抽取（一次完成）**：
   - AI 直接使用当前环境进行语义理解评分
   - 使用 `references/ai_scoring_prompt.md` 中的完整 Prompt
   - AI 逐篇阅读 `papers_deduped.jsonl` 中的标题和摘要
   - 按以下标准打 1–10 分（保留1位小数）：
     * **9-10分**：完美匹配 - 相同任务 + 相同方法 + 相同模态
     * **7-8分**：高度相关 - 相同任务，方法/模态略有差异
     * **5-6分**：中等相关 - 同领域但任务/方法/模态有显著差异
     * **3-4分**：弱相关 - 仅部分概念或技术重叠
     * **1-2分**：几乎无关 - 仅背景层面有宽泛关联
   - 评分维度：任务匹配度、方法匹配度、数据模态、应用价值
   - **子主题标签规则**：仅对 **≥5分** 的论文分配子主题标签（整体形成 5–7 个子主题簇，如"CNN分类"、"多模态融合"、"弱监督学习"）；**3–4分** 的弱相关论文不分配子主题（`subtopic` 置空即可），避免低分文献污染后续子主题规划
   - **同步提取数据抽取表字段**：从摘要中提取 `design`（研究设计）、`key_findings`（关键发现）、`limitations`（局限性），用于生成完整的数据抽取表
   - 输出 `scored_papers.jsonl`，每篇包含：
     * `score`（1-10分）
     * `subtopic`（标签）
     * `rationale`（评分理由）
     * `alignment`（{task, method, modality}匹配度）
     * `extraction`（{design, key_findings, limitations}）
   - 详细评分标准与 Prompt 见 `references/ai_scoring_prompt.md`
   - **评分质量验证**：
     * 健康分布：高分20-40%、中分40-60%、低分10-30%
     * AI 评分支持中英文主题，自动语义理解
4) **选文**：`select_references.py` 按目标参考范围和高分优先比例（默认 60–80%）选出集合，生成 `selected_papers.jsonl`、`references.bib`、`selection_rationale.yaml`；生成 Bib 时大小写无关去重 key，转义未处理的 `&`，缺失 author/year/journal/doi 用默认值标注后输出警告。若选中文献仍存在摘要缺失/过短，会被标记 `do_not_cite` 并在校验报告中给出“摘要覆盖率”提示（建议写作时不引用或替换）。
5) **子主题与配额规划（AI 自主）**：基于评分结果自动给出 5–7 个子主题，并分配段落配额：引言约 1.5k，讨论/展望各 ~1k，结论 ~0.6k，剩余均分给子主题段（每段 ~1.8–2.2k，随目标总字数自动缩放），写入工作条件与数据抽取表，作为扩写锚点。
6) **综/述字数预算**：`plan_word_budget.py` 基于选文与大纲生成 3 份字数预算 CSV（列：文献ID、大纲、综字数、述字数，允许无引用大纲行文献ID为空），对齐均值形成 `word_budget_final.csv`，输出无引用汇总 `non_cited_budget.csv`，并校验总字数与目标差值 ≤5%。
7) **写作**：资深领域专家风格自由写作，固定章节：摘要、引言、子主题段落（数量自定但遵循配额）、讨论、展望、结论。写作前读取 `word_budget_final.csv`，引用段按文献综/述预算写，无引用段按空 ID 行预算写；引用使用 `\cite{key}`，正文源为 `{topic}_review.tex`。

   **内容分离约束（防止 AI 流程泄露）**：
   - **综述正文** `{topic}_review.tex` 必须**仅聚焦领域知识**，禁止出现任何"AI工作流程"描述
   - **禁止在正文出现的内容**：
     * ❌ "本综述基于 X 条初检文献、去重后 Y 条、最终保留 Z 篇"
     * ❌ "方法学上，本综述按照'检索→去重→评分→选文→写作'的管线执行"
     * ❌ 任何提及"检索"、"去重"、"相关性评分"、"选文"、"字数预算"等元操作的描述
   - **上述信息应放在**：`{主题}_工作条件.md` 的相应章节（Search Log、Relevance Scoring & Selection 等）
   - **目标**：让读者感受不到这是 AI 生成的综述，完全符合传统学术综述惯例
   - **验证**：写作完成后运行 `scripts/validate_no_process_leakage.py` 检查是否有流程泄露

   **引用分布约束（重要 - 强制执行）**：
   - **单篇引用优先原则**：约 70% 的引用应为单篇 `\cite{key}` 格式
   - **单篇引用场景**（优先使用）：
     * 引用具体方法、结果、数字时："Zhang 等人使用 ResNet-50 达到 95% 准确率\cite{Zhang2020}。"
     * 逐篇对比研究时："ResNet 表现优异\cite{He2016}。DenseNet 进一步提升性能\cite{Huang2017}。"
     * 引用核心观点或理论时："注意力机制能够帮助模型聚焦于关键区域\cite{Wang2021}。"
   - **小组引用场景**（限制使用，约 25%）：
     * 对比并列研究时，且需明确说明各文献的差异化贡献："方法 A 在 X 方面优于方法 B\cite{Paper1,Paper2}，其中 Paper1 采用...，Paper2 采用..."
     * 引用互补证据时，且分别说明各文献的独立贡献
   - **禁止模式**：
     * ❌ "陈述观点 + 堆砌 2-3 篇文献"："多项研究表明\cite{Paper1,Paper2,Paper3}。"
     * ❌ 单次引用 >4 个 key（<5% 情况，仅限综述性陈述）
   - **验证要求**：写作完成后运行 `scripts/validate_citation_distribution.py --verbose`，如单篇引用 <65% 必须修正
   - 详见 `references/expert-review-writing.md` 的"引用分布约束"章节
8) **有机扩写 + 校验与导出**：若 `validate_counts.py` 判定字数不足，则仅在最短/缺证据的子主题段内按配额进行"增量扩写"（保持原主张与引用不变，只补证据/局限/衔接），补后再跑校验；`validate_review_tex.py` 对章节/引用大小写不敏感且提供可解释提示；如有 `word_budget_final.csv` 可选跑 `validate_word_budget.py`；通过后 `compile_latex_with_bibtex.py` 自动回退/同步模板与 `.bst` 后生成 PDF，`convert_latex_to_word.py` 生成 Word。
9) **多语言翻译与编译（可选）**：如果用户指定了目标语言（如"日语综述"、"德语综述"）：
   - 使用 `multi_language.py` 处理全流程（语言检测、翻译、编译）
   - **AI 翻译**：翻译正文内容，保留所有 `\cite{key}` 引用和 LaTeX 结构
   - **备份原文**：自动备份为 `{topic}_review.tex.bak`
   - **覆盖原 tex**：翻译后覆盖原 `{topic}_review.tex`
   - **智能修复编译**：循环编译直到成功或触发终止条件（循环检测、超时、不可修复错误）
   - **失败兜底**：输出错误报告 + broken 文件；建议在编译时加 `--auto-restore` 自动回滚到编译前备份，或手动用 `--restore` 恢复备份
   - **支持语言**：en（英语）、zh（中文）、ja（日语）、de（德语）、fr（法语）、es（西班牙语）
   - **详见**：`references/multilingual-guide.md`

## 输出（保持 6 件套）
| 类型 | 文件 | 说明 |
|---|---|---|
| 工作条件 | `{主题}_工作条件.md` | 记录输入、检索/日志、评分与选文依据、写作结构、校验结果 |
| 正文 LaTeX | `{主题}_review.tex` | 摘要/引言/子主题段落/讨论/展望/结论，`\cite{key}` |
| 参考文献 | `{主题}_参考文献.bib` | 选中文献 BibTeX |
| 字数预算 CSV | `word_budget_run{1,2,3}.csv` / `word_budget_final.csv` / `non_cited_budget.csv` | 综/述字数预算（70% 引用段 + 30% 无引用段，空 ID 行表示无引用大纲） |
| 验证报告 | `{主题}_验证报告.md` | 字数/引用/章节/引用一致性验证结果汇总 |
| PDF | `{主题}_review.pdf` | 由 LaTeX 渲染 |
| Word | `{主题}_review.docx` | 由 LaTeX + BibTeX 导出 |

## 校验硬门槛（仅保留必要项）
- 正文字数：档位默认范围见 `config.yaml.validation.words.{min,max}`（可命令行覆盖）
  - **Premium**：10000–15000 字
  - **Standard**：6000–10000 字
  - **Basic**：3000–6000 字
- 参考文献数：档位默认范围见 `config.yaml.validation.references.{min,max}`
  - **Premium**：80–150 篇
  - **Standard**：50–90 篇
  - **Basic**：30–60 篇
- 必需章节存在：摘要、引言、至少 1 个子主题段落、讨论、展望、结论
- \cite 与 BibTeX key 必须一致；缺失即报错

## 健壮性与日志
- 模板与 `.bst`：使用 `TEXINPUTS`/`BSTINPUTS` 环境变量引用 `latex-template/` 目录，不再复制模板文件到工作目录（v3.5 优化）；可用 `config.yaml.latex.template_path_override` 或 CLI `--template` 覆盖。若 `.bst` 文件缺失，编译将直接报错（v3.6 优化）。
- DOI 链接显示：若 BibTeX 同时包含 `doi` 与 `url`（例如 `url` 为 OpenAlex），PDF 参考文献默认优先显示 `https://doi.org/{doi}`；BibTeX 仍保留原始 `url` 便于追溯。
- 中间文件清理：默认自动清理 `.aux`、`.bbl`、`.blg`、`.log`、`.out`、`.toc` 等 LaTeX 中间文件（v3.6 优化）；如需保留用于调试，可使用 `--keep-aux` 参数。
- Bib 清洗：生成 Bib 时自动转义 `&/%/_/#/$` 等常见 LaTeX 特殊字符，大小写无关去重 key，并为缺失 author/year/journal/doi 填充默认值且输出警告。
- 恢复路径校验：resume 状态下发现无效 `papers` 路径会清理并重新检索，避免把目录当文件。
- 导出日志：Pipeline 会输出 tex/bib/template/bst、pdf/word 路径，便于排查。
- 字数预算：`plan_word_budget.py` 自动生成 3 份 run CSV、均值版 `word_budget_final.csv`，并输出无引用汇总；`validate_word_budget.py` 可选检查列/覆盖率/总字数误差。
- **验证报告**（v3.3 新增）：阶段6 自动生成 `{主题}_验证报告.md`，汇总字数/引用/章节/引用一致性验证结果，便于事后审查和追溯。
- **多源摘要补充**：默认启用（由 `config.yaml:search.abstract_enrichment.enabled` 控制），默认执行时机为 `config.yaml:search.abstract_enrichment.stage=post_selection`（只对 `selected_papers` 补齐，生成 `selected_papers_enriched_{主题}.jsonl`），避免检索阶段对候选库做全局补齐导致慢与 `cache/api` 膨胀；如需切回检索阶段补齐：将 stage 设为 `search` 或对 `openalex_search.py` 显式 `--enrich-abstracts`。详见 `scripts/multi_source_abstract.py`。
- **证据卡（evidence cards）**：阶段5 可生成 `evidence_cards_{主题}.jsonl`（字段压缩 + 摘要截断），用于写作时“先压缩再写作”，降低上下文占用（配置：`config.yaml:writing.evidence_cards.*`）。
- **API 缓存**：默认开启（配置：`config.yaml:cache.api.enabled=true`），默认 `mode=minimal`（不缓存 OpenAlex 原始分页响应，避免 cache/api 文件爆炸）；需要更强可复现性时可设为 `mode=full`。

## 工作条件骨架（要点）
- Meta：主题、档位、目标字数/参考范围、最高原则承诺
- Search Plan & Search Log：查询、来源、时间范围、结果量
- Dedup：去重策略与映射文件
- Relevance Scoring & Selection：评分方法、高分优先比例、选文结果与理由
- Review Structure：子主题列表与写作提纲
- Validation：字数/参考数/必需章节检查结果

## 有机扩写约束（用于阶段 6 不足时）
- 不新增子主题，不改写/删除原主张与引用；只补充同段内的证据、局限或衔接句。
- 扩写提示需包含：该段原文、段落配额、当前差额（字数/引用），要求保持语气一致。
- 扩写后立即运行 `validate_counts.py` 与 `validate_review_tex.py`；不足则只对最短段循环 1–2 次，避免全局灌水。
- 最终整体性润色仅做衔接/顺序/句式调整，不得篡改文献元数据及其事实、数字、样本量或结果方向。

## 可选：成本追踪（Token 使用与费用统计）

**说明**：这是一个完全可选的功能，用于追踪文献综述项目中的 Token 使用和费用。它不会影响文献综述的核心流程。

### 初始化

```bash
python3 systematic-literature-review/scripts/pipeline_cost.py init
```

### 获取模型价格（AI 自动完成）

**只需运行**：
```bash
python3 systematic-literature-review/scripts/pipeline_cost.py fetch-prices
```

**AI 将自动**（在技能环境中）：
1. 读取 config.yaml 中配置的模型商（OpenAI、Anthropic、智谱清言）
2. 使用 WebSearch 工具查询官方定价
3. 解析价格信息并生成 YAML
4. 保存到 `scripts/pipeline_cost.yaml`
5. 自动复制到当前项目

### 记录使用

在关键步骤后记录 Token 使用：

```bash
python3 systematic-literature-review/scripts/pipeline_cost.py log \
  --tool <工具名称> \
  --model <模型名称> \
  --in <输入tokens> \
  --out <输出tokens> \
  --step "<步骤描述>"
```

示例：
```bash
python3 systematic-literature-review/scripts/pipeline_cost.py log \
  --tool "Task" \
  --model "claude-opus-4-5" \
  --in 12345 \
  --out 6789 \
  --step "文献检索"
```

### 查看统计

```bash
# 整个项目统计
python3 systematic-literature-review/scripts/pipeline_cost.py summary

# 当前会话统计
python3 systematic-literature-review/scripts/pipeline_cost.py summary --type session

# 只看 token，不看费用
python3 systematic-literature-review/scripts/pipeline_cost.py summary --no-cost
```

### 数据存储

所有成本追踪数据存储在项目目录的 `.systematic-literature-review/cost/` 下：
- `token_usage.csv`：Token 使用记录
- `price_config.yaml`：模型价格配置（从技能级复制）

### 配置

在 `config.yaml` 中配置成本追踪：

```yaml
cost_tracking:
  enabled: true                    # 启用/禁用
  model_providers:                 # 关注的模型商
    - OpenAI
    - Anthropic
    - 智谱清言
  price_cache_max_days: 30         # 价格有效期（天）
  currency_rates:
    USD_TO_CNY: 7.2                # 汇率
```

## 自动化执行（pipeline_runner）
- 阶段：`0_setup → 1_search → 2_dedupe → 3_score → 4_select → 4.5_word_budget → 5_write → 6_validate → 7_export`
- 推荐（幂等 work_dir，避免出现 `{topic}/{topic}` 异常嵌套目录）：`python scripts/run_pipeline.py --topic "{主题}" --runs-root runs`
- 运行示例：`python scripts/pipeline_runner.py --topic "{主题}" --domain general --work-dir runs/{safe_topic}`
- resume：`python scripts/pipeline_runner.py --resume runs/{safe_topic}`

**⚠️ 重要说明：阶段3 AI 评分需要 Skill 交互模式**

- Pipeline 的阶段3不支持自动评分，需要通过 Skill 交互模式完成
- AI（你）直接使用 `references/ai_scoring_prompt.md` 中的 Prompt 评分
- 读取 `papers_deduped.jsonl`，逐篇评分并输出 `scored_papers.jsonl`
- **AI 评分优势**：语义理解、多语言支持、数据抽取同步完成
- 评分完成后，使用 `--resume-from 4` 继续后续阶段


## 文件操作规范（工作目录隔离）

### 强制规则

1. **所有中间文件必须存放在 `{work_dir}/.systematic-literature-review/` 目录内**
2. 最终交付物存放在工作目录根部（以 `{topic}_` 为前缀）
3. **AI 临时脚本必须存放在 `{work_dir}/.systematic-literature-review/scripts/`**

### 获取工作目录

```python
import os
from pathlib import Path

work_dir = Path(os.environ["SYSTEMATIC_LITERATURE_REVIEW_SCOPE_ROOT"])
scripts_dir_env = os.environ.get("SYSTEMATIC_LITERATURE_REVIEW_SCRIPTS_DIR")
scripts_dir = Path(scripts_dir_env) if scripts_dir_env else (work_dir / ".systematic-literature-review" / "scripts")
artifacts_dir = work_dir / ".systematic-literature-review" / "artifacts"
```

### 创建新文件时

```python
# ✅ 正确：使用相对路径拼接
output_path = artifacts_dir / "results.json"
temp_script = scripts_dir / "temp_analysis.py"

# ❌ 错误：直接使用相对路径（可能污染其他目录）
output_path = Path("results.json")

# ❌ 错误：使用绝对路径（破坏隔离）
output_path = Path("/tmp/results.json")
```

### 禁止行为

- ❌ 不要在工作目录根部创建临时脚本或中间文件
- ❌ 不要使用绝对路径（如 `/tmp/temp.txt`）写入临时文件
- ❌ 不要读取/写入其他 run 目录的文件
- ✅ 使用环境变量 `SYSTEMATIC_LITERATURE_REVIEW_SCOPE_ROOT` 获取工作目录
- ✅ 使用环境变量 `SYSTEMATIC_LITERATURE_REVIEW_SCRIPTS_DIR` 获取临时脚本目录

## 环境与工具
- Python 3.9+，依赖安装：`pip install -r requirements.txt`
- LaTeX（含 xelatex/bibtex）、pandoc
- 至少一个搜索类 MCP 工具或 OpenAlex API 可用
- 关键脚本：
  - 检索：`multi_query_search.py`、`openalex_search.py`
  - 去重：`dedupe_papers.py`
  - 选文：`select_references.py`、`build_reference_bib_from_papers.py`
  - 数据抽取：`update_working_conditions_data_extraction.py`
  - 字数预算：`plan_word_budget.py`、`validate_word_budget.py`
  - 校验：`validate_counts.py`、`validate_review_tex.py`
  - 验证报告：`generate_validation_report.py`（v3.3 新增）
  - 导出：`compile_latex_with_bibtex.py`、`convert_latex_to_word.py`

## 写作前提示模板（含字数预算）
- **摘要格式约束**（写作前必须遵守）：
  "摘要必须是**单一段落**，字数 200–250 字，按'背景→核心发现/趋势→挑战→展望'的结构写作。
  禁止出现'本综述基于 X 条文献'、'最终保留 Z 篇'等 AI 流程泄露描述。
  详见 references/expert-review-writing.md 的'摘要格式说明'章节。"

- **表格样式约束**（写作前必须遵守）：
  "使用 `longtable` 或 `tabular` 环境时，列宽必须基于 `\\textwidth` 按比例分配（所有比例之和 ≤ 1.0）。
  禁止使用固定 `p{}` 列宽（如 `p{8.9cm}`），避免在不同边距/版芯下溢出。
  示例：
  ```tex
  \\begin{longtable}{p{0.14\\textwidth} p{0.48\\textwidth} p{0.22\\textwidth} p{0.16\\textwidth}}
  ...
  \\end{longtable}
  ```
  详见 `references/review-tex-section-templates.md` 的'表格样式最佳实践'章节。"

- **AI 评分与子主题分组**（阶段3）：
  使用 `references/ai_scoring_prompt.md` 中的标准评分流程，逐篇阅读文献并打 1-10 分，同时分配子主题标签。完成后运行质量自检，确保分数分布合理（高分20-40%、中分40-60%、低分10-30%）。

- **子主题与配额规划**（阶段5）：
  "基于评分结果，自动给出 **3-7 个子主题**（硬性约束），并分配段落配额：引言 ~1.5k，讨论/展望各 ~1k，结论 ~0.6k，剩余均分给子主题段（每段 ~1.8–2.2k，随目标总字数自动缩放）。

  **子主题合并原则（避免过度细分）**：
  - 相似方法合并：如 CNN/Transformer/集成学习 → '深度学习模型架构'
  - 相关任务合并：如分割/检测/分类 → '核心诊断任务'
  - 学习策略合并：如迁移学习/弱监督/数据增强 → '高级学习策略'
  - 禁止创建 10+ 个子主题 section
  - 每个子主题至少应有 5 篇支撑文献

  返回子主题列表、每段目标字数，并写入工作条件与数据抽取表。"

- **有机扩写**（校验不足时，针对最短/缺证据的子主题段）：
  "在『{子主题名}』段内有机扩写，保持原主张和引用不变，只补充 2–3 条具体证据/数字/反例与衔接句；本段目标约 {目标字数} 字，当前不足 {差额} 字。原文如下：{原段落全文}"

- **字数预算**（写作前，引用/无引用兼容）：
  "读取 `word_budget_final.csv`，列包含：文献ID、大纲、综字数、述字数。引用段按对应文献的综/述字数预算写作；无引用段（文献ID 为空行，如摘要/展望/结论）按该行预算控制长度，可合并叙述但需尊重总字数配额。"

- **缩略词规范**（写作前必须遵守）：
  "首次出现专有名词时，使用'中文（英文全称，英文缩写）'格式，后续可直接使用英文缩写。
  示例：'免疫检查点抑制剂（Immune checkpoint inhibitor，ICI）'、'卷积神经网络（Convolutional Neural Network，CNN）'。
  常见缩略词如 DNA、RNA、CT、MRI、AI 等可直接使用，无需首次全称展开。
  详见 references/expert-review-writing.md 的'写作要点'章节。"

- **内容分离约束**（写作前必须遵守，防止 AI 流程泄露）：
  "综述正文必须**完全聚焦领域知识**，禁止出现任何'AI工作流程'描述。具体禁止：❌ 在摘要中写'本综述基于 X 条初检文献、去重后 Y 条、最终保留 Z 篇'；❌ 在引言中写'方法学上，本综述按照检索→去重→评分→选文→写作的管线执行'；❌ 任何提及'检索、去重、相关性评分、选文、字数预算'等元操作的描述。这些方法学信息应放在 `{主题}_工作条件.md` 中。目标是让读者感受不到这是 AI 生成的综述，完全符合传统学术综述惯例。详见 `references/expert-review-writing.md` 的'内容分离原则'章节。"

- **引用分布与位置约束**（写作前必须遵守）：
  "**引用必须紧跟着它所支持的观点**，而非堆积在段落末尾。

  **写作节奏**：
  1. 提出观点 → 立即引用 \\cite{key} → 继续下一个观点 → 再次引用
  2. 避免先写完整个段落，最后一次性加所有引用

  **单篇引用优先**（约占 70%）：
     - 引用具体方法/结果/数字时：「作者 + 方法 + 结果 + \\cite{key}」
     - 逐篇对比时：「观点 A + \\cite{key1}。观点 B + \\cite{key2}。」
     - 禁止使用「多项研究表明\\cite{key1,key2,key3}」模式（除非前面已逐个引用过）

  **小组引用**（约占 25%）：
     - 仅用于对比并列研究时，且必须明确说明各文献的差异化贡献

  **段末堆砌**（<20% 情况）：
     - 仅用于段末总结，前提是段落主体已经充分引用并阐述

  详见 `references/expert-review-writing.md` 的'引用位置约束'和'单篇引用优先'章节。"

- **写作负面约束**（写作前必须遵守，禁止模式）：
  "以下写作模式被**严格禁止**，违反者将被视为业余水准：

  **❌ 禁止模式 1：补充阅读/参见类句子**
  - 禁止：『本节补充阅读可参见：\\cite{...}』
  - 禁止：『进一步阅读可参考：\\cite{...}』
  - 禁止：『相关研究参见：\\cite{...}』
  - 禁止：任何在段末堆砌引用且不说明具体贡献的『参见』类表述
  - 理由：这类句子对读者没有价值，纯粹是『凑字数』的业余行为

  **❌ 禁止模式 2：模糊的引用堆砌**
  - 禁止：『多项研究表明\\cite{key1,key2,key3}』且前面未逐个引用过
  - 禁止：单次引用 >6 个 key（除非是段末总结且段落主体已充分引用）
  - 理由：读者无法识别每个观点的具体来源

  **❌ 禁止模式 3：为达到字数而灌水**
  - 禁止：添加无实质内容的过渡句、重复表述
  - 禁止：为『用完』所有文献而强行引用低分文献
  - 理由：专家级综述聚焦证据质量，而非文献数量

  **✅ 正确做法：引用未充分利用时的处理**
  - 如果高分文献已充分引用：可以不引用低分文献
  - 如果段落完整但字数不足：在段落内补充具体证据/数字/反例（有机扩写）
  - 如果确实需要补充背景：拆分为独立子段落，每段 2-5 篇文献

  详见 `references/expert-review-writing.md` 的『写作负面约束』章节。"
