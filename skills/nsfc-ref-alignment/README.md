# nsfc-ref-alignment — 用户使用指南

本 README 面向**使用者**：如何触发并正确使用 `nsfc-ref-alignment` skill。  
执行边界与硬性规范在 `SKILL.md`；默认参数在 `config.yaml`。

---

## 你会得到什么

- 一份**只读审查报告**（默认输出到 `./references/`）：`NSFC-REF-ALIGNMENT-v*.md`
- 一个可复现的“证据包”（强制隔离到标书目录下）：`{project_root}/.nsfc-ref-alignment/run_*/`

该技能默认**不修改**任何标书正文或参考文献（`*.tex/*.bib`），只生成报告供你人工复核。

---

## 快速开始（推荐）

### 用法 1：最推荐（只读核查 + 报告输出到 ./references）

把 `projects/NSFC_General` 替换成你的标书目录：

```
请使用 nsfc-ref-alignment 检查以下标书引用是否可靠：
标书路径：projects/NSFC_General
输出：只生成报告，默认写入 ./references
约束：全程只读，不修改任何 .tex/.bib/.cls/.sty
```

### 用法 2：开启 DOI 在线核验（更严格，但更慢）

```
请使用 nsfc-ref-alignment 检查 projects/NSFC_General 的引用真实性；
对 DOI 做在线核验，标注疑似伪造/不一致条目；
仍然只输出报告，不修改任何文件。
```

### 用法 3：把报告输出到指定目录（避免污染仓库根目录 references）

```
请使用 nsfc-ref-alignment 检查 projects/NSFC_General；
将报告输出到 skills/nsfc-ref-alignment/tests/out；
全程只读。
```

---

## 设计理念（为什么是“只读 + 报告制”）

在 NSFC 标书里，改正文或改参考文献通常牵一发而动全身。本技能默认采用更稳的策略：

1) 脚本做**确定性抽取与校验**（引用清单、bibkey 是否存在、BibTeX 字段与 DOI 格式等）  
2) 宿主 AI 再做**启发式/语义核查**（“这句话是否真的在引用这篇论文”）  
3) 最终只交付**报告**，由你人工确认后再决定是否要改正文/改 bib

---

## 输出文件说明

### 1) 中间产物（强制，写入标书目录）

位于：`{project_root}/.nsfc-ref-alignment/run_*/`

典型文件：
- `ai_ref_alignment_input.json`：结构化输入（引用位置 + 句子上下文 + 文献元信息 + 校验结果）
- `ref_integrity_report.md`：确定性报告（缺失 bibkey/重复条目/字段缺失/DOI 格式/可选在线核验摘要）
- `citations.csv`：逐条引用明细（file/line/bibkey/sentence）
- `bib_inventory.json`：被引用条目的 BibTeX 清单（含重复与缺失标注）

### 2) 最终交付（默认写入 ./references）

- `NSFC-REF-ALIGNMENT-vYYYYMMDDHHMMSS.md`（如同秒重复运行会追加 `-2/-3/...`）

---

## 备选用法（脚本/硬编码流程）

如果你希望不依赖对话触发，也可以直接运行脚本（仍然只读）：

```bash
# 在仓库根目录运行
python3 skills/nsfc-ref-alignment/scripts/run_ref_alignment.py \
  --project-root "projects/NSFC_General" \
  --main-tex "main.tex" \
  --report-dir "references" \
  --prepare

# 可选：开启 DOI 在线核验（会更慢）
python3 skills/nsfc-ref-alignment/scripts/run_ref_alignment.py \
  --project-root "projects/NSFC_General" \
  --main-tex "main.tex" \
  --report-dir "references" \
  --prepare \
  --verify-online
```

---

## 参数与配置

参数默认值以 `skills/nsfc-ref-alignment/config.yaml` 为准，常用项：

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `project_root` | （必填） | 标书项目根目录 |
| `main_tex` | `main.tex` | 主入口 tex（相对 `project_root`） |
| `report_dir` | `references` | 交付报告输出目录（相对当前工作目录） |
| `verify_online` | `false` | 是否在线核验 DOI（Crossref/OpenAlex） |

---

## 常见问题（FAQ）

### Q1：报告提示 “Missing BibKeys（P0）”，我该怎么办？

这通常意味着正文里出现了 `\cite{somekey}`，但 `.bib` 里找不到 `somekey`。  
建议你先用 `nsfc-bib-manager` 补齐或核对 BibTeX 条目，再决定是否要改正文引用。

### Q2：为什么有时会提示缺少 bibtexparser？

脚本会优先使用 `bibtexparser` 提高 BibTeX 解析鲁棒性；如果环境里没有该包，会自动降级为“best-effort 手写解析器”。  
降级不影响“缺失 bibkey/重复 key/部分字段检查”的核心能力，但复杂嵌套括号的字段解析可能不如 bibtexparser 稳定。

### Q3：报告里说“语义不匹配风险（P0/P1）”，会自动帮我改正文吗？

默认不会。本技能只输出报告。你如果希望修复引用或改写句子，建议先让 AI 在报告里给出**修改计划**，你确认后再执行最小化修改。

---

## WHICHMODEL（模型选择建议）

### 结论（怎么选）

该 skill 的”确定性抽取/校验”由脚本完成，LLM 主要负责两件事：
1) **语义核查**：判断”包含引用的句子”是否真的在引用该文献（高风险、需要强推理、必须克制幻觉）
2) **报告写作**：把确定性结果组织成可审阅的 P0/P1 清单与证据链

**唯一推荐组合：GPT-5.2 high + Codex**

其他模型（GPT-4o、GPT-4o mini、o4-mini、Claude 系列等）均不推荐用于本 skill。原因：语义引用核查对推理深度和幻觉抑制要求极高，低于 GPT-5.2 high 的模型在”不确定时倾向编造论文内容”的风险不可接受。

### 参数建议
- **temperature**：建议偏低（例如 0–0.3），降低”乱补细节/过度自信”的概率
- **工作方式**：先让模型只做”判定 + 证据 + 风险等级”，不要先让它改正文；等你确认后再进入”修改计划/最小化修复”阶段
