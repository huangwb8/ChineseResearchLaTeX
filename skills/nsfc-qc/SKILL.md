---
name: nsfc-qc
version: 0.2.0
description: 当用户明确要求"标书QC/质量控制/润色前质检/引用真伪核查/篇幅与结构检查"时使用。对 NSFC 标书进行只读质量控制：并行多线程独立检查文风生硬、引用假引/错引风险、篇幅与章节分布、逻辑清晰度等，最终输出标准化 QC 报告；中间文件默认归档到“交付目录内的隐藏工作区（.nsfc-qc/）”，并兼容 legacy `.nsfc-qc/`。
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
- **隔离（推荐）**：使用“交付目录 + sidecar 工作区”组织产物，默认不污染标书根目录：
  - 交付目录（面向人读）：`{deliver_dir}/`
  - 工作区（面向复现/归档）：`{deliver_dir}/.nsfc-qc/`（包含 runs/snapshot/.parallel_vibe/artifacts/final）
- **兼容（legacy）**：仍支持把工作区写入 `project_root/.nsfc-qc/`（旧用法）。
- **交付物（标准化）**：
  - `{run_dir}/final/nsfc-qc_report.md`
  - `{run_dir}/final/nsfc-qc_metrics.json`
  - `{run_dir}/final/nsfc-qc_findings.json`
  - `{run_dir}/final/validation.json`（结构一致性校验结果）

## 输入参数（建议显式提供）

最少必须给：
- `project_root`：如 `projects/NSFC_Young`

建议同时给：
- `main_tex`：默认 `main.tex`
- `threads`：默认 5
- `execution`：默认 `serial`（串联）；用户明确要求并行时才改 `parallel`
- `deliver_dir`：推荐提供（例如 `.../QC/vYYYYMMDDHHMMSS`），用于“实例隔离”

参数默认值见 `config.yaml`。

## 硬约束（必须遵守）

- **禁止写入标书源文件**：包括但不限于 `*.tex/*.bib/*.cls/*.sty`。
- **禁止“为了优化而直接改文”**：本技能只产出 QC 报告与可执行建议；后续是否修改由人工复核或其它写作类 skill 执行。
- **不编造引用**：任何“引用真伪/是否错引”的结论，必须给出证据链（bib 条目、论文题目/DOI、来源链接或检索失败说明）；不确定时标记为“需人工复核（uncertain）”。

## 工作流（强制）

### 0) 定位输入与 run 目录

1. 校验 `project_root` 存在；`main_tex` 默认 `main.tex`，若不存在则在 `project_root` 下优先探测 `main.tex`，否则列出候选 `*.tex` 并让用户确认。
2. 生成 `run_id = vYYYYMMDDHHMMSS`（本地时间），并优先采用“实例隔离”布局：
   - `deliver_dir = project_root/QC/{run_id}/`（可由用户显式提供）
   - `workspace_dir = {deliver_dir}/.nsfc-qc/`
   - `run_dir = {workspace_dir}/runs/{run_id}/`

> 若用户明确要求 legacy（或不方便创建交付目录），才使用 `project_root/.nsfc-qc/runs/{run_id}/`。

> 可选：运行 `scripts/nsfc_qc_precheck.py` 生成确定性“预检指标”，供多线程 QC 参考。

### 1) 只读预检（确定性）

目标：先用脚本完成“不会错”的检查，减少 AI 幻觉与漏检。

最小预检清单：
- 引用 key 是否都能在 `.bib` 中找到（缺失即 P0）
- `.bib` 条目是否明显不完整（缺 title/author/year 等，或占位符，标 P1）
- 引用真伪/错引的“证据包”（硬编码抓取）：对每个被引用的 bibkey，尽最大努力获取论文标题/摘要（可选获取 OA PDF 并抽取正文片段），并同时提取标书内的引用上下文；供后续 AI 做语义判断（不确定就标 uncertain）
- 章节/文件级篇幅分布（字符数/粗略字数）
- 中文排版易错项（确定性）：检测直引号 `"免疫景观"` 这类写法，并给出替换建议（推荐 TeX 引号 ``免疫景观''）

产物落点（示例）：
- `.../artifacts/precheck.json`
- `.../artifacts/citations_index.csv`
- `.../artifacts/tex_lengths.csv`
- `.../artifacts/quote_issues.csv`
- `.../artifacts/abbreviation_issues.csv`
- `.../artifacts/abbreviation_issues_summary.json`
- `.../artifacts/reference_evidence.jsonl`
- `.../artifacts/reference_evidence_summary.json`

### 2) 多线程独立 QC（parallel-vibe；默认 5 threads；默认串联）

你必须使用 `parallel-vibe` 来“多线程独立 QC”，但为了满足“所有中间文件都在 `.nsfc-qc/`”的约束：

- `parallel-vibe --out-dir {run_dir}/`
  - 这样 `.parallel_vibe/` 会被创建在 run 内部（无论 legacy 还是 workspace 模式）
- `parallel-vibe --src-dir {run_dir}/snapshot/`
  - 每个 thread 的 workspace 都是 snapshot 的**独立拷贝**；snapshot 为“最小化副本”（通常仅 `*.tex/*.bib` + `./.nsfc-qc/input/` 证据包）

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
   - 总体是否过短/过长（用字符数与章节分布做近似判断）
   - 各章节比例是否合理（例如：立项依据/研究内容/研究基础的分配是否失衡）
4. **逻辑与论证**：论证链是否闭合（科学问题→假说→目标→方法→验证→预期），是否存在跳步、歧义、概念偷换、缺对照/缺指标。
5. **缩略语规范**：
   - 读取预检产物 `abbreviation_issues.csv`（或 `abbreviation_issues_summary.json`）作为起点
   - 对每条 P1 问题（`bare_first_use` / `missing_english_full`）做语义判断：
     - 确认是否为真正的“重要专业术语”（领域常识词如 DNA/RNA 可豁免）
     - 确认首次出现位置是否确实缺少“中文全称（English Full Name, ABBR）”格式
   - 对 P2 问题（`missing_chinese_full` / `repeated_expansion`）：确认是否确实缺中文全称/是否真的多次重复展开
   - 过滤误报：LaTeX 标签、图表编号、数学变量等不是缩写
   - 输出：按文件/行号定位的可执行建议（只写建议，不改文件）
6. **其它 QC**（至少 3 项）：例如术语一致性、图表/公式编号与引用、风险与备选方案、创新点可验证性、夸大措辞等。

> 注意：thread 工作区内也**禁止修改**任何标书源文件；如需记录建议，写在 `RESULT.md` 或 thread 内新增的 `notes/*.md`（不改原文件）。

### 3) 汇总聚合（主线程）

你需要把 5 个 threads 的 `RESULT.md` 汇总为**一份**最终 QC 报告，并确保：
- 去重合并：同类问题合并，证据保留最强的 1-2 条
- 冲突处理：如果 threads 结论冲突，报告中明确指出并给出“为何选择/为何不确定”
- 优先级分级：P0（必须修复）/ P1（重要建议）/ P2（可选优化）
- 输出“可执行修改建议清单”：按文件/章节定位 + 建议改法 + 预计收益

### 4) 输出标准化报告（强制格式）

最终报告写入：
- `{run_dir}/final/nsfc-qc_report.md`（脚本会生成“底线版”报告骨架 + 确定性 findings）

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
- `nsfc-qc_metrics.json`：字符数、章节分布、引用数量、缺失引用数量、预检信号聚合等
- `nsfc-qc_findings.json`：结构化问题列表（id/severity/location/evidence/recommendation/status）

你可以使用 `templates/` 下的模板文件（可选，但推荐）：
- `templates/REPORT_TEMPLATE.md`
- `templates/FINDINGS_SCHEMA.json`

### 5) 非目标：编译检查

`nsfc-qc` 的定位是“内容质量 QC”（标书写得怎么样）。PDF 能否编译成功属于环境/工程质量，不在本技能范围内；请你在自己的 TeX/Overleaf 环境自行验证。

## 快捷脚本（可选，但推荐）

若希望可追溯与少出错，推荐优先使用“一键实例隔离”脚本：

0) 一键运行（推荐：交付目录 + sidecar 工作区）

```bash
python3 skills/nsfc-qc/scripts/nsfc_qc_run.py \
  --project-root projects/NSFC_Young \
  --main-tex main.tex \
  --deliver-dir projects/NSFC_Young/QC/vYYYYMMDDHHMMSS \
  --threads 5 \
  --execution serial
```

> 输出：交付目录内会有 `nsfc-qc_report.md/nsfc-qc_metrics.json/nsfc-qc_findings.json/validation.json` + `artifacts/`（选取的确定性证据）。

也支持 legacy/拆分式调用（只写入 `project_root/.nsfc-qc/`）：

1) 预检（引用/篇幅/章节分布 + 引用证据包）

```bash
python3 skills/nsfc-qc/scripts/nsfc_qc_precheck.py \
  --project-root projects/NSFC_Young \
  --main-tex main.tex \
  --out projects/NSFC_Young/.nsfc-qc/runs/vYYYYMMDDHHMMSS/artifacts \
  --resolve-refs
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
