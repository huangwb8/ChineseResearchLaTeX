---
name: check-review-alignment
description: 当用户明确要求"核查/优化综述 `{主题}_review.tex` 的正文引用"或"运行 check-review-alignment"时使用。通过宿主 AI 的语义理解逐条核查引用是否与文献内容吻合，只在发现致命性引用错误时对"包含引用的句子"做最小化改写，并复用 `systematic-literature-review` 的渲染脚本输出 PDF/Word。核心原则：不为了改而改，无法确定是否为致命性错误时保留原样并在报告中警告。⚠️ 不适用：用户只是想生成系统综述正文（应使用 systematic-literature-review）；用户只是想新增/核对 BibTeX 条目（应使用专门的 bib 管理流程）。

metadata:
  short-description: AI 驱动的综述引用语义核查与自动渲染
  keywords:
    - 引用优化
    - BibTeX
    - LaTeX
    - review.tex
    - 语义核查
  dependencies:
    - skill: systematic-literature-review
      required: true
      reason: "LaTeX → PDF/Word 渲染"
---

# Check Review Alignment

## 适用场景
- 已有 `{主题}_review.tex` 与对应 `.bib`，需要核查正文每条引用是否“真的在引用该论文”，并在必要时最小化改写以消除错配/幻觉引用。
- 需要在优化后自动渲染生成 PDF 与 Word。

## 输入
- `work_dir`：综述工作目录（包含 `{主题}_review.tex` 与 `.bib`，可含 PDF）。
- 可选：`--tex` 指定 tex 文件名（默认取目录下首个 `*_review.tex`；若目录内存在多个候选，脚本会给出 warning 并提示使用 `--tex` 明确指定）。

## 输出
- `{work_dir}/.check-review-alignment/ai_alignment_report.md`：单一报告，包含 Summary / Critical Fixes (P0) / Warnings (P1) / Rendering Result（末尾附 PDF/Word 路径或错误摘要）。
- `{work_dir}/.check-review-alignment/ai_alignment_input.json`：脚本生成的"引用 + 文献元信息（含 DOI/URL） + PDF 摘要段"结构化输入，便于宿主 AI 快速核查。
- 已优化的 `{主题}_review.tex`（保存在 `work_dir` 根目录）；新生成的 `{主题}_review.pdf` 与 `{主题}_review.docx`（保存在 `work_dir` 根目录）。

## 工作流

### 步骤 0：依赖检查（仅渲染路径强制）

本技能支持两类确定性动作：
- `--prepare`：生成结构化输入（不依赖渲染 skill）
- `--render`：渲染 PDF/Word（强制依赖 `systematic-literature-review`）

**当且仅当你需要执行渲染（步骤 5 或 `--render`）时，必须检查以下依赖**：

- [ ] `systematic-literature-review` skill 是否可用？
  - 如果不可用：立即停止，并提示：
    `❌ 缺少依赖：check-review-alignment 依赖 systematic-literature-review skill 进行 PDF/Word 渲染。请先安装 systematic-literature-review skill。`
  - 如果可用：继续执行

### 步骤 1：预检与文件定位
1) 在 `work_dir` 内定位 `*_review.tex` 与对应 `.bib`（或用 `--tex` 指定）。
2) 若缺项：停止并说明缺失文件。

### 步骤 2：提取结构化上下文（推荐）
运行脚本生成 `ai_alignment_input.json`，用于宿主 AI 快速、可追溯地逐条核查：

```bash
# 进入 skill 根目录（安装后通常是 ~/.codex/skills/check-review-alignment 或 ~/.claude/skills/check-review-alignment）
cd /path/to/check-review-alignment
python3 scripts/run_ai_alignment.py --work-dir "/path/to/work_dir" --prepare
```

### 步骤 3：AI 语义核查与优先级分级
对每条引用（bibkey）进行核查：

1) **识别错误类型**：判断属于 P0（致命性）/ P1（警告）/ P2（禁止）
2) **证据来源**：按优先级使用 PDF 摘要段 > BibTeX abstract/title > 仅从句子推断（最低优先级）
3) **按优先级处理**：
   - P0：以**最小改动**改写“包含该引用”的句子以恢复一致性（必要时仅可改写同段内紧邻且也包含该引用的句子；禁止整段重写）
   - P1：仅记录到 Warnings，不改写
   - P2：跳过，不触碰
4) **强制约束**：
   - 保留 LaTeX 命令完整性（`\cite{}`、`\ref{}`、`\label{}` 等）
   - 不引入新 bibkey（除非是修复错误 bibkey）
   - 不伪造论文内容
   - 禁止改写未包含引用的句子
   - 无法确定时保留原样（“不动如山”原则）

### 步骤 4：生成报告
在 `{work_dir}/.check-review-alignment/ai_alignment_report.md` 生成报告，必须包含以下章节：

- **Summary**：段落数、引用数、P0 修改数、P1 警告数、P2 跳过数等统计
- **具体细节**（强制）：每条引用的详细核查记录，包含：
  - 引用：文献标题 `{title}`；DOI 号 `{DOI}`（如无则标注"无 DOI"）
  - 原文内容：包含该引用的句子原文
  - 文献实际：该论文的实际内容（从 PDF 摘要段 / BibTeX abstract / title 提取）
  - 引用合理性评估：语义一致性分析，说明原文描述是否准确反映文献内容
  - 问题级别：P0（致命）/ P1（警告）/ P2（禁止）/ 无问题
- **Critical Fixes (P0)**：必须修复的致命性错误（原句/原因/新句/行号/优先级）
- **Warnings (P1)**：仅警告的问题（原句/原因/建议/行号/优先级）
- **Rendering Result**：PDF/Word 路径或错误摘要

**具体细节章节格式示例**：

```markdown
## 具体细节

### 引用：[bibkey]

| 字段 | 内容 |
|------|------|
| 文献标题 | {title} |
| DOI | {DOI 或 "无 DOI"} |
| 原文内容 | {包含该引用的句子原文} |
| 文献实际 | {从 PDF/BibTeX 提取的论文实际内容} |
| 引用合理性评估 | {语义一致性分析} |
| 问题级别 | P0 / P1 / P2 / 无问题 |
```

### 步骤 5：渲染 PDF/Word
在完成 tex 修改后渲染：

```bash
cd /path/to/check-review-alignment
python3 scripts/run_ai_alignment.py --work-dir "/path/to/work_dir" --render
```

## 修改边界与优先级

### 必须修复（P0）

以下情况**必须修改**（最小改动）：

1) **虚假引用**（`fake_citation`）
   - 表现：引用的文献根本不存在（.bib 中缺失或 bibkey 错误）
   - 处理：在报告中标记 `missing_in_bib: true` 并说明，建议用户检查 bibkey

2) **错误引用**（`wrong_citation`）
   - 表现：引用命令中的 bibkey 与文意不符（张冠李戴）
   - 处理：改写句子使其与该 bibkey 的文献内容一致，或更换正确 bibkey

3) **矛盾引用**（`contradictory_citation`）
   - 表现：正文描述与论文内容矛盾（如论文说男性，文写女性）
   - 处理：改写句子使其与论文内容一致

### 仅警告不改（P1）

以下情况**仅记录到报告 Warnings，不改写**：

1) **支撑弱**（`weak_support`）：建议用户补充更强引用
2) **定位偏差**（`overclaim`）：建议用户降低表述强度（如避免“首创/首次/核心”）

### 禁止修改（P2）

以下情况**完全禁止触碰**：

1) **文体优化**（`style_issue`）：语序/措辞/润色
2) **未引用句子**：不包含任何 `\cite{}` 的句子
3) **段落重写**：即使段落内所有引用都修复，也不得重写整段

### 修改原则

- **最小改动原则**：只改写必要句子，不改写相邻无关句或整段
- **不动如山原则**：无法确定是否为致命性错误时，保留原样并记录到 Warnings
- **证据优先原则**：判断依据优先级：PDF 摘要段 > BibTeX abstract/title > 仅从句子推断

## 配置（见 `check-review-alignment/config.yaml`）

- `citation_commands`：识别的引用命令
- `pdf.*`：是否抽取 PDF 文本及页数上限
- `render.*`：依赖 skill 名称与覆盖策略
- `ai.input_limits.*`：结构化输入（`ai_alignment_input.json`）的文本截断上限
- `ai.modification.*`：修改策略（由宿主 AI 执行；脚本仅打包进 `ai_alignment_input.json`）
  - `ai.modification.error_priority`：P0/P1/P2 分级（只改 P0；P1 仅警告；P2 跳过）
  - `ai.modification.non_fatal_handling`：P1/P2 的处理策略
- `ai.paragraph_optimization.*`：段落优化策略（由宿主 AI 执行；默认关闭，避免文体改写）

## 快速使用

```bash
cd /path/to/check-review-alignment
# 1) 生成结构化输入（推荐）
python3 scripts/run_ai_alignment.py --work-dir "/path/to/work_dir" --prepare
# 2) 宿主 AI 按本 SKILL.md 工作流完成核查与 tex 改写，并写 ai_alignment_report.md
# 3) 渲染 PDF/Word
python3 scripts/run_ai_alignment.py --work-dir "/path/to/work_dir" --render
```

## 依赖
- Python 包：`PyYAML`、`bibtexparser`（读取 config/bib）、`pdfplumber` 或 `PyPDF2`（PDF 抽取）。缺少时会降级（不会中断）。
- **AI 功能无需额外依赖**：AI 由 Agent Skills 宿主环境（Claude/Codex）提供；脚本不在本地直接调用 LLM API。
- 参考目录：当前 `check-review-alignment/references/` 为空（如未来引入更详细的策略/模板，会在该目录补充）。

## 验证清单（静态自检）
- `{work_dir}/.check-review-alignment/ai_alignment_report.md` 已生成，且每条修改包含：原句/原因/新句/定位信息。
- `{work_dir}/.check-review-alignment/ai_alignment_input.json` 已生成，包含结构化的引用与文献信息。
- 修改后的 tex 可编译无错误，且引用命令（`\cite{}` 等）完整保留。
- 渲染后的 PDF/Word 路径与状态已写入报告。

## 安全原则

本技能遵循以下原则，确保“不为了改而改”：

| 原则 | 说明 | 实现 |
|------|------|------|
| **确定性脚本边界** | 脚本只做解析/抽取/渲染，不做语义判断 | 脚本不调用 LLM API |
| **优先级分级** | P0 修复 / P1 警告 / P2 跳过 | `ai.modification.error_priority` |
| **不动如山** | 无法确定时保留原样 | 工作流强制约束 + Warnings |
| **最小改动** | 只改必要句子，不整段重写 | `max_edits_per_sentence` + 禁止段落重写 |
| **LaTeX 完整性** | 保留所有 LaTeX 命令结构 | `preserve_citations: true` |
