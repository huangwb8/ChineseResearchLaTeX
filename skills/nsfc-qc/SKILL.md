---
name: nsfc-qc
version: 0.1.1
description: 当用户明确要求"标书QC/质量控制/润色前质检/引用真伪核查/篇幅与结构检查"时使用。对 NSFC 标书进行只读质量控制：并行多线程独立检查文风生硬、引用假引/错引风险、篇幅与章节分布、逻辑清晰度等，最终输出标准化 QC 报告；所有中间文件归档到工作目录的 .nsfc-qc/。
author: Bensz Conan
metadata:
  author: Bensz Conan
  short-description: NSFC 标书只读 QC（多线程 + 标准化报告）
  keywords:
    - nsfc-qc
    - 标书质检
    - 质量控制
    - 引用核查
    - 篇幅检查
    - 逻辑通顺
    - 文风优化建议
  triggers:
    - QC
    - 质量控制
    - 质检
    - 标书检查
    - 引用核查
    - 假引
    - 错引
    - 篇幅
    - 章节分布
config: skills/nsfc-qc/config.yaml
references: skills/nsfc-qc/references/
---

# NSFC 标书质量控制（nsfc-qc）

## 目标输出（契约）

- **只读**：对标书内容完全只读（不修改任何 `.tex/.bib/.cls/.sty`）。
- **隔离**：所有中间产物必须写入 `project_root/.nsfc-qc/`（包含 parallel-vibe 生成的 `.parallel_vibe/`）。
- **交付物（标准化）**：
  - `.nsfc-qc/runs/{run_id}/final/nsfc-qc_report.md`
  - `.nsfc-qc/runs/{run_id}/final/nsfc-qc_metrics.json`
  - `.nsfc-qc/runs/{run_id}/final/nsfc-qc_findings.json`

## 输入参数（建议显式提供）

最少必须给：
- `project_root`：如 `projects/NSFC_Young`

建议同时给：
- `main_tex`：默认 `main.tex`
- `threads`：默认 5
- `execution`：默认 `serial`（串联）；用户明确要求并行时才改 `parallel`

参数默认值见 `config.yaml`。

## 硬约束（必须遵守）

- **禁止写入标书源文件**：包括但不限于 `*.tex/*.bib/*.cls/*.sty`。
- **禁止“为了优化而直接改文”**：本技能只产出 QC 报告与可执行建议；后续是否修改由人工复核或其它写作类 skill 执行。
- **不编造引用**：任何“引用真伪/是否错引”的结论，必须给出证据链（bib 条目、论文题目/DOI、来源链接或检索失败说明）；不确定时标记为“需人工复核（uncertain）”。

## 工作流（强制）

### 0) 定位输入与 run 目录

1. 校验 `project_root` 存在；`main_tex` 默认 `main.tex`，若不存在则在 `project_root` 下优先探测 `main.tex`，否则列出候选 `*.tex` 并让用户确认。
2. 生成 `run_id = vYYYYMMDDHHMMSS`（本地时间）并创建：
   - `project_root/.nsfc-qc/runs/{run_id}/`
   - `project_root/.nsfc-qc/runs/{run_id}/final/`
   - `project_root/.nsfc-qc/runs/{run_id}/artifacts/`（放脚本输出、提取结果、日志）

> 可选：运行 `scripts/nsfc_qc_precheck.py` 生成确定性“预检指标”，供多线程 QC 参考。

### 1) 只读预检（确定性）

目标：先用脚本完成“不会错”的检查，减少 AI 幻觉与漏检。

最小预检清单：
- 引用 key 是否都能在 `.bib` 中找到（缺失即 P0）
- `.bib` 条目是否明显不完整（缺 title/author/year 等，或占位符，标 P1）
- 章节/文件级篇幅分布（字符数/粗略字数）
-（可选）编译得到 PDF 页数（软约束：原则上不超过 30 页；过长标 P2，过短标 P1）

产物落点（示例）：
- `.../artifacts/precheck.json`
- `.../artifacts/citations_index.csv`
- `.../artifacts/tex_lengths.csv`

### 2) 多线程独立 QC（parallel-vibe；默认 5 threads；默认串联）

你必须使用 `parallel-vibe` 来“多线程独立 QC”，但为了满足“所有中间文件都在 `.nsfc-qc/`”的约束：

- `parallel-vibe --out-dir project_root/.nsfc-qc/runs/{run_id}/`
  - 这样 `.parallel_vibe/` 会被创建在 `.nsfc-qc/` 内部
- `parallel-vibe --src-dir project_root`
  - 每个 thread 的 workspace 都是标书的**独立拷贝**，天然满足“对原标书只读”

并行策略：
- 默认 `serial`（串联执行 threads）
- 用户明确要求“并行跑”时才启用 `--parallel --max-parallel <k>`

#### Thread 统一任务（每个 thread 做同样的 QC）

每个 thread 的 `RESULT.md` 必须覆盖同一份检查清单（允许发现点不同），至少包括：
1. **文风与可读性**：生硬句、口语/堆砌、AI 味/模板味、冗长句；给“最小改写建议”（只写建议，不改文件）。
2. **引用真伪与错引风险**：
   - P0：引用 key 缺失、明显虚构条目（无法检索且 bib 信息异常）
   - P1：可能错引（正文断言与论文题目/摘要方向明显不符）、元信息疑点（年份/期刊/作者异常）
   - 逐条给出证据锚点：`bibkey`、所在句子（原文片段 ≤ 50 字）、bib 条目、可核验链接/检索关键词
3. **篇幅与结构分布**：
   - 总体是否过短/过长（页数优先；无 PDF 时用字符数近似）
   - 各章节比例是否合理（例如：立项依据/研究内容/研究基础的分配是否失衡）
4. **逻辑与论证**：论证链是否闭合（科学问题→假说→目标→方法→验证→预期），是否存在跳步、歧义、概念偷换、缺对照/缺指标。
5. **其它 QC**（至少 3 项）：例如术语一致性、缩略语首次定义、图表/公式编号与引用、风险与备选方案、创新点可验证性、夸大措辞等。

> 注意：thread 工作区内也**禁止修改**任何标书源文件；如需记录建议，写在 `RESULT.md` 或 thread 内新增的 `notes/*.md`（不改原文件）。

### 3) 汇总聚合（主线程）

你需要把 5 个 threads 的 `RESULT.md` 汇总为**一份**最终 QC 报告，并确保：
- 去重合并：同类问题合并，证据保留最强的 1-2 条
- 冲突处理：如果 threads 结论冲突，报告中明确指出并给出“为何选择/为何不确定”
- 优先级分级：P0（必须修复）/ P1（重要建议）/ P2（可选优化）
- 输出“可执行修改建议清单”：按文件/章节定位 + 建议改法 + 预计收益

### 4) 输出标准化报告（强制格式）

最终报告写入：
- `project_root/.nsfc-qc/runs/{run_id}/final/nsfc-qc_report.md`

报告必须包含以下固定章节（标题名保持一致）：
1. `执行摘要`
2. `范围与只读声明`
3. `硬性问题（P0）`
4. `重要建议（P1）`
5. `可选优化（P2）`
6. `引用核查清单`
7. `篇幅与结构分布`
8. `建议的最小修改路线图`
9. `附录：复现信息（命令/路径/产物索引）`

同时输出两份 JSON（用于后续人工复核/自动化处理）：
- `nsfc-qc_metrics.json`：页数、字符数、章节分布、引用数量、缺失引用数量、编译是否成功等
- `nsfc-qc_findings.json`：结构化问题列表（id/severity/location/evidence/recommendation/status）

你可以使用 `templates/` 下的模板文件（可选，但推荐）：
- `templates/REPORT_TEMPLATE.md`
- `templates/FINDINGS_SCHEMA.json`

## 快捷脚本（可选，但推荐）

若希望可追溯与少出错，可运行（只写入 `.nsfc-qc/`）：

1) 预检（引用/篇幅/章节分布；可选编译页数）

```bash
python3 skills/nsfc-qc/scripts/nsfc_qc_precheck.py \
  --project-root projects/NSFC_Young \
  --main-tex main.tex \
  --out projects/NSFC_Young/.nsfc-qc/runs/vYYYYMMDDHHMMSS/artifacts \
  --compile
```

2) 生成 parallel-vibe plan 并运行（默认串联 5 threads）

```bash
python3 skills/nsfc-qc/scripts/run_parallel_qc.py \
  --project-root projects/NSFC_Young \
  --run-id vYYYYMMDDHHMMSS \
  --threads 5 \
  --execution serial
```

3) 生成标准化 final 输出骨架（即使 threads 尚未运行也可执行）

```bash
python3 skills/nsfc-qc/scripts/materialize_final_outputs.py \
  --project-root projects/NSFC_Young \
  --run-id vYYYYMMDDHHMMSS
```

## 降级策略（必须提供）

若 `parallel-vibe` 不可用（脚本缺失或 runner CLI 不可用），仍需完成 QC：
- 用单线程完成同一份 QC 清单
- 仍然输出同样的标准化报告与 JSON
- 并在 `附录：复现信息` 中写明：未启用 parallel-vibe 的原因与环境限制
