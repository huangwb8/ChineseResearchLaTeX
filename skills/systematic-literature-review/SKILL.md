---
name: systematic-literature-review
description: 当用户明确要求"做系统综述/文献综述/related work/相关工作/文献调研"时使用。AI 自定检索词，多源检索→去重→AI 逐篇阅读并评分（1–10分语义相关性与子主题分组）→按高分优先比例选文→自动生成"综/述"字数预算→资深领域专家自由写作（固定摘要/引言/子主题/讨论/展望/结论），保留正文字数与参考文献数硬校验，强制导出 PDF 与 Word。支持多语言翻译与智能编译（en/zh/ja/de/fr/es）。

metadata:
  author: Bensz Conan
  short-description: 相关性评分驱动的系统综述流水线（LaTeX+BibTeX，PDF/Word 强制，支持多语言）
  keywords:
    - systematic-literature-review
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

## 与 bensz-collect-bugs 的协作约定

- 当用户环境中出现因本 skill 设计缺陷导致的 bug 时，优先使用 `bensz-collect-bugs` 按规范记录到 `~/.bensz-skills/bugs/`，严禁直接修改用户本地 Claude Code / Codex 中已安装的 skill 源码。
- 若 AI 仍可通过 workaround 继续完成用户任务，应先记录 bug，再继续完成当前任务。
- 当用户明确要求“report bensz skills bugs”等公开上报动作时，调用本地 `gh` 与 `bensz-collect-bugs`，仅上传新增 bug 到 `huangwb8/bensz-bugs`；不要 pull / clone 整个 bug 仓库。

## 定位

- 目标：在一个隔离工作目录内完成“检索 → 去重 → 评分 → 选文 → 写作 → 校验 → PDF/Word 导出”的完整综述流水线。
- 适用：用户明确要系统综述、文献综述、related work、文献调研，并希望得到 LaTeX + BibTeX + PDF/Word 产物。
- 不适用：只想补单条参考文献、只想润色已有正文、只想写普通摘要或与综述无关的文章。
- 最高原则：以最佳可用证据和写作质量完成综述；不确定时说明处理方式，不为赶进度牺牲可信度。

## 输入

最少需要：

1. `{主题}`：一句话主题。
2. 可选范围：时间、语言、研究类型、数据库偏好等。
3. 档位：`Premium` / `Standard` / `Basic`；未指定时读取 `config.yaml` 默认值。
4. 目标字数与参考文献范围：未指定时按 `config.yaml.scoring.default_*_range`。
5. 输出目录或安全化前缀：未指定时使用安全化主题名。

## 输出

默认交付以下核心文件：

- `{主题}_工作条件.md`：输入、检索、评分、选文、结构与校验记录。
- `{主题}_review.tex`：正文唯一 LaTeX 源文件。
- `{主题}_参考文献.bib`：选中文献 BibTeX。
- `word_budget_run{1,2,3}.csv`、`word_budget_final.csv`、`non_cited_budget.csv`：综/述字数预算。
- `{主题}_验证报告.md`：字数、章节、引用一致性等验证结果。
- `{主题}_review.pdf`
- `{主题}_review.docx`

必要中间产物包括：

- `papers*.jsonl`
- `scored_papers.jsonl`
- `selected_papers.jsonl`
- `selection_rationale.yaml`
- 可选 `evidence_cards_{主题}.jsonl`

## 硬约束

- 强制导出 PDF 与 Word；只有明确失败并记录原因时才允许缺失。
- 正文字数与参考文献数必须落在当前档位范围内；可由用户覆盖，默认值以 `config.yaml` 为准。
- 正文固定包含：摘要、引言、至少 1 个子主题段、讨论、展望、结论。
- `\cite{key}` 必须与 BibTeX key 一致；缺失即报错。
- 正文禁止泄露 AI 工作流，例如“检索/去重/评分/选文/字数预算”等元叙事只能写入 `{主题}_工作条件.md`。
- 摘要必须为单段，避免方法学流水账；表格宽度与样式约束见 `references/review-tex-section-templates.md`。
- 不为凑引用而堆砌低分文献；无法确认时优先不改、不引。

## 主流程

### 0. 准备

- 记录主题、档位、字数/参考范围与输出目录。
- 开始前优先阅读：
  - `references/ai_query_generation_prompt.md`
  - `references/ai_scoring_prompt.md`
  - `references/expert-review-writing.md`
  - `references/review-tex-section-templates.md`
  - 涉及翻译时再读 `references/multilingual-guide.md`

### 1. 多查询检索

- AI 为主题自主规划查询变体，通常 5-15 组。
- 优先用 OpenAlex，必要时按 `config.yaml.search.provider_priority` 自动降级。
- 检索结果写 Search Log；resume 时若 `papers` 路径失效，应清理后重检。

### 2. 去重

- 用 `dedupe_papers.py` 生成去重结果与映射。
- 所有后续流程只读取去重后的候选集。

### 3. AI 评分与数据抽取

- AI 按 `references/ai_scoring_prompt.md` 逐篇阅读标题与摘要，输出 `scored_papers.jsonl`。
- 每篇至少包含：`score`、`subtopic`、`rationale`、`alignment`、`extraction`。
- 评分范围固定为 1-10 分；仅对 `>=5` 分文献分配子主题，避免弱相关论文污染子主题规划。
- 自检分布是否健康：高分约 20-40%，中分 40-60%，低分 10-30%。

### 4. 选文与 Bib 生成

- `select_references.py` 按目标参考范围和高分优先比例选出最终集合。
- 生成 `selected_papers.jsonl`、`references.bib`、`selection_rationale.yaml`。
- Bib 清洗必须保留：大小写无关去重 key、LaTeX 特殊字符转义、缺失字段警告。
- 摘要缺失或过短的条目标记 `do_not_cite`，并在报告中提示摘要覆盖率风险。

### 5. 子主题与配额规划

- AI 基于评分结果规划 3-7 个子主题，并给出段落配额。
- 默认思路：引言约 1.5k、讨论/展望各约 1k、结论约 0.6k，其余分给子主题段。
- 结果写入工作条件与数据抽取表，作为写作锚点。

### 6. 字数预算

- 用 `plan_word_budget.py` 生成 3 份预算 CSV，再汇总为 `word_budget_final.csv`。
- 引用段与无引用段预算均需覆盖；总字数误差必须控制在 `config.yaml.word_budget.tolerance` 内。

### 7. 写作

- 正文章节固定为：摘要、引言、子主题段、讨论、展望、结论。
- 写作前读取 `word_budget_final.csv`，按文献综/述预算组织证据。
- 默认采用单篇引用优先；引用要紧跟所支撑的观点，避免段末堆砌。
- 如需详细写作规范，直接遵循：
  - `references/expert-review-writing.md`
  - `references/review-tex-section-templates.md`

### 8. 有机扩写与验证

- 若字数不足，只允许在最短或证据不足的子主题段内做增量扩写，不新增子主题，不改原主张和引用。
- 依次运行：
  - `validate_counts.py`
  - `validate_review_tex.py`
  - 可选 `validate_word_budget.py`
  - `generate_validation_report.py`

### 9. 导出与多语言

- 通过 `compile_latex_with_bibtex.py` 生成 PDF。
- 通过 `convert_latex_to_word.py` 生成 Word。
- 如用户要求多语言版本，使用 `multi_language.py` 翻译正文并智能编译；失败时保留错误报告与 broken 文件，并优先支持恢复备份。

## 工作目录与文件隔离

- 所有中间文件必须写入 `{work_dir}/.systematic-literature-review/`。
- 最终交付物放在工作目录根部。
- AI 临时脚本必须放到 `{work_dir}/.systematic-literature-review/scripts/`。
- 不要把临时文件写到工作目录根部，不要用绝对路径写 `/tmp/*`，也不要读写其他 run 目录。
- 以环境变量 `SYSTEMATIC_LITERATURE_REVIEW_SCOPE_ROOT` 和 `SYSTEMATIC_LITERATURE_REVIEW_SCRIPTS_DIR` 为准。

## 关键命令

```bash
# 推荐主入口
python3 scripts/run_pipeline.py --topic "{主题}" --runs-root runs

# 旧入口 / resume
python3 scripts/pipeline_runner.py --topic "{主题}" --domain general --work-dir runs/{safe_topic}
python3 scripts/pipeline_runner.py --resume runs/{safe_topic}

# 阶段 3 评分后，从第 4 阶段继续
python3 scripts/pipeline_runner.py --resume runs/{safe_topic} --resume-from 4
```

## 环境与脚本

- 运行环境：Python 3.9+、LaTeX（`xelatex`/`bibtex`）、pandoc。
- 关键脚本：
  - 检索：`multi_query_search.py`、`openalex_search.py`
  - 去重：`dedupe_papers.py`
  - 选文：`select_references.py`、`build_reference_bib_from_papers.py`
  - 数据抽取：`update_working_conditions_data_extraction.py`
  - 字数预算：`plan_word_budget.py`、`validate_word_budget.py`
  - 校验：`validate_counts.py`、`validate_review_tex.py`、`generate_validation_report.py`
  - 导出：`compile_latex_with_bibtex.py`、`convert_latex_to_word.py`

## 可选：成本追踪

- 初始化：`python3 systematic-literature-review/scripts/pipeline_cost.py init`
- 抓取定价：`python3 systematic-literature-review/scripts/pipeline_cost.py fetch-prices`
- 记录 token：`pipeline_cost.py log ...`
- 汇总：`pipeline_cost.py summary`
- 所有成本数据写到 `.systematic-literature-review/cost/`

## 参考材料

- `references/ai_query_generation_prompt.md`
- `references/ai_scoring_prompt.md`
- `references/expert-review-writing.md`
- `references/review-tex-section-templates.md`
- `references/multilingual-guide.md`
- `references/development-validation-guide.md`
