# Systematic Literature Review（相关性驱动版）— 用户使用指南

本 README 面向**使用者**：如何触发并正确使用 `systematic-literature-review` skill。执行指令与硬性规范在 `SKILL.md`；默认参数在 `config.yaml`。

## 快速开始

```
请用 systematic-literature-review 这个skill写一篇"xxx主题"的Premium级综述。 参考文献以近2023-2025年为主，更早之前的文献，如果特别相关、特别重要的，也可以纳入。要有一个小节，专门讨论出未来3年较有前景的研究方向。工作目录名为 XXX-01。
```

> 💡 **示例**：查看 [examples/](examples/) 目录，包含本 skill 实际生成的专家级综述示例，可参考输出格式和质量标准。

## 设计理念
- AI 自定检索词 → 去重 → 标题/摘要 1–10 分相关性与子主题自动分组 → 高分优先选文 → **自动生成"综/述"字数预算（70% 引用段 + 30% 无引用段，3 次采样均值，空 ID 行支持无引用大纲）** → 资深领域专家自由写作。
- 档位仅影响默认字数/参考范围（可覆盖），支持三档：**Premium（旗舰级）**、**Standard（标准级）**、**Basic（基础级）**。
- 强制导出 PDF/Word；硬校验：必需章节、字数 min/max、参考文献数 min/max、\cite 与 bib 对齐；可选校验字数预算覆盖率/总和。
- **最高原则**：AI 不得偷懒或短视地为了速度做错误事；不确定必须说明；最终润色仅做衔接与结构调整，不得改动文献题目/摘要所含事实/数字。
- **稳健性**：恢复状态时校验 `papers` 路径；Bib 自动转义 `&`、补充缺失字段并大小写无关去重 key；模板/`.bst` 缺失会自动回退同步。
- **多语言支持**（v4.0 新增）：支持将综述翻译为多种语言（en/zh/ja/de/fr/es），自动修复 LaTeX 渲染错误，保留引用和结构不变。详见[多语言支持](#多语言支持)。

## 字数预算的设计哲学

`word_budget_final.csv` 采用**柔性指导**而非**刚性约束**的设计：

- **为什么不严格限制？** 如果 AI 被强制按每篇文献的精确字数写作，会产生机械、割裂的文本，失去学术综述应有的流畅性和连贯性。
- **实际作用**：字数预算作为 AI 写作时的**重要参考**，帮助 AI 理解各章节的相对权重和文献的重要性排序，但允许 AI 根据内容需要灵活调整。
- **预期偏差**：各章节实际字数与预算偏差 ±30% 是正常的，这正是"资深领域专家自由写作"的体现。
- **硬性约束**：只有**总字数范围**（如 6000-10000）和**参考文献数范围**（如 50-90）是硬性校验，确保综述的整体规模符合档位要求。

这种设计让 AI 既有章法可循，又保留了人类专家写作时的自然节奏和判断力。

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
请用 systematic-literature-review 做主题"AI for protein design"的文献综述，基础级，近五年英文。
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
请读取 runs/{safe_topic}/.systematic-literature-review/artifacts/word_budget_final.csv，引用段按每篇文献的“综/述”字数预算写，无引用段（文献ID为空，如摘要/结论/展望）按该行预算控制长度；可合并引用但需贴近预算总字数。
```

## 运行与校验（维护者）
- 自动流程：`python scripts/pipeline_runner.py --topic "主题" --work-dir runs/主题`  
  阶段：`0_setup → 0.5_subtopics（写作前由 AI 给出并记录） → 1_search → 2_dedupe → 3_score → 4_select → 4.5_word_budget → 5_write → 6_validate（含有机扩写与可选预算校验） → 7_export`
- 校验：`validate_counts.py`（字数/引用 min/max）、`validate_review_tex.py`（必需章节 + cite/bib 对齐）
- 导出：`compile_latex_with_bibtex.py {topic}_review.tex {topic}_review.pdf`；`convert_latex_to_word.py ...`；如需自定义模板可在 `config.yaml.latex.template_path_override` 或 CLI `--template` 指定路径（缺失会回退到内置模板并同步 `.bst`）。

## 关键文件
- `SKILL.md`：工作流、输入输出、最高原则与硬校验
- `config.yaml`：档位字数/参考范围、高分优先比例、搜索默认参数
- `scripts/score_relevance.py`：子主题自动分组 + 1–10 分
- `scripts/select_references.py`：按高分优先比例和目标数量选文，生成 Bib
- `scripts/plan_word_budget.py`：三次采样生成字数预算 run1/2/3 + final（含无引用空 ID 行）
- `scripts/validate_word_budget.py`：可选校验预算列/覆盖率/总和
- `scripts/update_working_conditions_data_extraction.py`：记录 score/subtopic 到数据抽取表

## 注意事项
- 必需章节：摘要、引言、>=1 个子主题段落、讨论、展望、结论。
- 只有字数/参考数与引用一致性是硬门槛；其余结构/密度不再强制。
- 输出文件仍采用 LaTeX-first：`{topic}_review.tex/.bib → .pdf/.docx`。
- 字数不足时优先在最短/缺证据的子主题段内做“有机扩写”，不新增子主题，不改原主张与引用；最终整体润色仅做衔接与结构优化，不得篡改文献事实/数字/元数据。
- resume 时若 `papers` 路径无效会自动清理并重新检索；中文主题缺少英文 token 会降级为字母/原始主题匹配并提示。

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

systematic-literature-review 现在支持将综述正文翻译为多种语言，并自动修复 LaTeX 渲染错误，确保 PDF 和 Word 正确输出。

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
请用 systematic-literature-review 做"AI for protein design"的日语综述，旗舰级。
```

#### 德语综述
```
请用 systematic-literature-review 做"Transformer in NLP"的德语综述，标准级。
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
