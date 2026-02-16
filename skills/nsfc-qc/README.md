# nsfc-qc — 用户使用指南

本 README 面向**使用者**：如何触发并正确使用 `nsfc-qc` skill。  
执行规范与硬性约束见 `SKILL.md`；默认参数见 `config.yaml`。

## 你会得到什么

对 NSFC 标书做**只读质量控制（QC）**，输出一份可审核、可追溯的**标准化 QC 报告**（P0/P1/P2 分级）：

- ✍️ **文风与可读性**：生硬/模板味/冗长句 → 给“最小改写建议”（只写建议，不改稿）
- 📚 **引用核查**：假引/错引/缺失 bibkey/元信息异常 → 给证据链 + 复核路径
- 🧪 **引用证据包（硬编码 + AI）**：先用脚本抓取“题目/摘要/（可选）OA PDF 片段”并提取标书引用上下文，再由 AI 做语义判断（不确定就标 uncertain）
- 📏 **篇幅与结构**：总页数（软约束 30 页）与章节分布是否失衡（建议性优化）
- 🧠 **逻辑与论证链**：是否闭环、是否跳步/歧义/概念偷换、关键对照与指标是否缺失
- 🧹 **其它 QC**：术语一致性、缩略语首次定义、图表/交叉引用、夸大措辞等
- 🧾 **中文排版易错项（确定性预检）**：检测直引号 `"免疫景观"` 这类写法，建议替换为 TeX 引号 ``免疫景观''

## 只读声明（重要）

`nsfc-qc` **不会修改你的标书内容**（不改任何 `.tex/.bib/.cls/.sty`）。  
所有中间文件与报告都会写入 `project_root/.nsfc-qc/`（包含 parallel-vibe 产物），便于后续审核与追溯。

## 快速开始（最推荐）

把下面这段原样发给 Codex：

```text
请用 nsfc-qc 对 projects/NSFC_Young 做一次质量控制（只读）。要求：
- 开 5 个 thread（默认串联模式）
- 每个 thread 做同一份 QC 清单（文风/引用/篇幅/结构/逻辑等）
- 汇总输出标准化 QC 报告（P0/P1/P2）
- 严禁修改标书任何内容；只输出报告与建议
```

## 常见用法（Prompt 模板）

### 1) 指定主入口 tex

```text
请用 nsfc-qc 检查 projects/NSFC_Young，主文件是 main.tex（只读）。输出标准化 QC 报告。
```

### 2) 重点核查“引用真伪/错引”（更严格）

```text
请用 nsfc-qc 对 projects/NSFC_Young 做 QC（只读），并把“引用真伪/错引风险”作为最高优先级：
- P0：缺失 bibkey / 明显虚构条目 / 明显错引
- P1：疑似错引或支撑弱（不确定就标 uncertain 并给复核路径）
```

### 3) 你明确要求并行（否则默认串联）

```text
请用 nsfc-qc 对 projects/NSFC_Young 做 QC（只读）：5 threads，并行跑（最多同时 3 个）。
```

## 输出文件（你会在磁盘上看到什么）

每次运行会创建一个 run 目录（`run_id` 为时间戳）：

| 产物 | 路径（相对 project_root） | 说明 |
|---|---|---|
| 最终报告 | `.nsfc-qc/runs/{run_id}/final/nsfc-qc_report.md` | 人类可读，含 P0/P1/P2 与路线图 |
| 指标 | `.nsfc-qc/runs/{run_id}/final/nsfc-qc_metrics.json` | 页数/字符数/引用统计/编译信息等 |
| 结构化问题清单 | `.nsfc-qc/runs/{run_id}/final/nsfc-qc_findings.json` | 便于后续人工审核或二次处理 |
| parallel-vibe 产物（如启用） | `.nsfc-qc/runs/{run_id}/.parallel_vibe/...` | 每个 thread 的 workspace 与 RESULT.md |
| 预检排版问题索引（可选） | `.nsfc-qc/runs/{run_id}/artifacts/quote_issues.csv` | 直引号等中文排版易错项（确定性扫描） |
| 引用证据包（可选） | `.nsfc-qc/runs/{run_id}/artifacts/reference_evidence.jsonl` | 每个 bibkey：标书引用上下文 +（尽力）论文题目/摘要/（可选）PDF 片段 |
| 编译日志（可选，最后一步） | `.nsfc-qc/runs/{run_id}/artifacts/compile.log` | 4 步法隔离编译日志（xelatex→bibtex→xelatex→xelatex） |

## 设计理念（为什么这样做）

- **只读**：QC 报告通常要进一步审核；“先报告、后改稿”更可控。
- **中间产物隔离**：所有过程文件集中到 `.nsfc-qc/`，不污染标书工程。
- **多线程独立**：同一份清单多视角复核，减少漏检；最后再聚合去重。
- **确定性优先**：能用脚本做的（引用 key 缺失、篇幅统计、引用证据包抓取）先脚本做，降低 AI 幻觉风险。
- **编译放最后**：4 步法隔离编译依赖环境且耗时，放在 QC 最后一步更稳健。
- **中文排版先扫雷**：直引号等“看起来没错但不规范/不美观”的问题，先确定性列出再人工改。

## WHICHMODEL

> 最后更新：2026-02-16  
> 覆盖厂商：Anthropic、OpenAI  
> 适用前提：你使用 `parallel-vibe` 跑多 thread QC（或由 Codex/Claude CLI 驱动）。

### 一句话选择

- **引用真伪/错引 + 逻辑闭环**这类“高歧义、要证据链”的 QC：优先用**更强推理/更高能力**的模型（必要时牺牲速度/成本）。OpenAI 的建议是：复杂、模糊、需要大量判断的任务更适合其 *reasoning* 系列模型。  
  参考：OpenAI《Reasoning best practices》。https://platform.openai.com/docs/guides/reasoning-best-practices
- **工具/多步骤工作流（含文件扫描、生成结构化报告）**：Anthropic 的建议是：复杂工具与歧义查询优先用 Opus/Sonnet，简单直接任务可用 Haiku。  
  参考：Anthropic《Tool use / Choosing a model》。https://docs.anthropic.com/en/docs/agents-and-tools/tool-use/implement-tool-use

实操建议：优先用 `runner_profile=fast|default|deep` 表达“强度档位”，避免在 README 里硬编码具体 `model_id`（模型名与可用性会随时间/账号/环境变化）。

### 按 nsfc-qc 的阶段选模型

| 阶段 | 你在做什么 | 推荐模型倾向 | 取舍理由（证据导向） |
|---|---|---|---|
| 预检（脚本） | 引用 key/篇幅/（可选）页数 | 不需要 LLM | 确定性检查更可靠；优先脚本 |
| 单个 thread QC | 找问题、给证据链与建议 | 中高能力（Sonnet/Opus；或 OpenAI 高能力/推理模型） | 需要“少误报 + 能解释证据链” |
| 汇总聚合（synthesis） | 去重、冲突消解、形成路线图 | 最强能力优先（Opus；或 OpenAI 更强推理/旗舰） | 需要稳健决策与一致性 |

### Anthropic 的通用选型法（强证据）

Anthropic 官方建议从**能力/速度/成本**三者权衡，并提供两种常见起步策略：  
1) 先用更快更省的模型快速迭代，不够再升级；2) 复杂任务从最强模型起步，再逐步降档优化。  
参考：Anthropic《Choosing the right model》。https://docs.anthropic.com/en/docs/about-claude/models/choosing-a-model

### OpenAI 的通用选型法（强证据）

OpenAI 将模型区分为 *reasoning* 与非 *reasoning*（GPT）两类，并强调：*reasoning* 更适合复杂规划/决策/歧义信息处理；同时建议对 reasoning 模型“提示词更直接、更少花活”。  
参考：OpenAI《Reasoning best practices》。https://platform.openai.com/docs/guides/reasoning-best-practices

## 备选用法（脚本/硬编码流程）

如果你想先做一次“确定性预检”，再让 AI 去做深度 QC：

### 1) 预检（只写入 `.nsfc-qc/`；包含“引用证据包”）

```bash
# 在 repo 根目录运行
python3 skills/nsfc-qc/scripts/nsfc_qc_precheck.py \
  --project-root projects/NSFC_Young \
  --main-tex main.tex \
  --out projects/NSFC_Young/.nsfc-qc/runs/vYYYYMMDDHHMMSS/artifacts \
  --resolve-refs
```

### 2) 运行 parallel-vibe（只写入 `.nsfc-qc/`；可选最后一步隔离编译）

```bash
# 生成 snapshot + plan，并把 parallel-vibe 产物落在 projects/NSFC_Young/.nsfc-qc/ 下
python3 skills/nsfc-qc/scripts/run_parallel_qc.py \
  --project-root projects/NSFC_Young \
  --run-id vYYYYMMDDHHMMSS \
  --threads 5 \
  --execution serial \
  --compile-last
```

### 3) 生成标准化 final 输出骨架（只写入 `.nsfc-qc/`）

```bash
# 即使 threads 尚未运行，也可以先把标准输出文件落盘（供后续人工/AI 填充与审核）
python3 skills/nsfc-qc/scripts/materialize_final_outputs.py \
  --project-root projects/NSFC_Young \
  --run-id vYYYYMMDDHHMMSS
```

## FAQ

### Q1：它真的不会修改我的标书吗？

A：不会。本 skill 的设计边界是“只读 QC”：只产出报告与建议，不允许修改 `.tex/.bib/.cls/.sty`。

### Q2：为什么默认串联跑 threads？

A：串联更省资源、降低限流/失败率；只有你明确要求并行时才建议并行跑。

### Q3：如果没有 `parallel-vibe` 或 runner CLI 怎么办？

A：会降级为单线程 QC，但仍输出同样的标准化报告，并在附录说明无法并行的原因。
