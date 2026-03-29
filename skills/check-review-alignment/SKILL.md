---
name: check-review-alignment
description: 当用户明确要求"核查/优化综述 `{主题}_review.tex` 的正文引用"或"运行 check-review-alignment"时使用。通过宿主 AI 的语义理解逐条核查引用是否与文献内容吻合，只在发现致命性引用错误时对"包含引用的句子"做最小化改写，并复用 `systematic-literature-review` 的渲染脚本输出 PDF/Word。核心原则：不为了改而改，无法确定是否为致命性错误时保留原样并在报告中警告。⚠️ 不适用：用户只是想生成系统综述正文（应使用 systematic-literature-review）；用户只是想新增/核对 BibTeX 条目（应使用专门的 bib 管理流程）。

metadata:
  author: Bensz Conan
  short-description: AI 驱动的综述引用语义核查与自动渲染
  keywords:
    - check-review-alignment
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

## 与 bensz-collect-bugs 的协作约定

- 当用户环境中出现因本 skill 设计缺陷导致的 bug 时，优先使用 `bensz-collect-bugs` 按规范记录到 `~/.bensz-skills/bugs/`，严禁直接修改用户本地 Claude Code / Codex 中已安装的 skill 源码。
- 若 AI 仍可通过 workaround 继续完成用户任务，应先记录 bug，再继续完成当前任务。
- 当用户明确要求“report bensz skills bugs”等公开上报动作时，调用本地 `gh` 与 `bensz-collect-bugs`，仅上传新增 bug 到 `huangwb8/bensz-bugs`；不要 pull / clone 整个 bug 仓库。

## 定位

- 用于检查已有 `{主题}_review.tex` 的正文引用是否真的与对应论文内容一致。
- 只在确认存在致命错误时最小化改写“包含该引用的句子”。
- 渲染 PDF/Word 依赖 `systematic-literature-review`；准备结构化输入不依赖该 skill。

## 输入

- `work_dir`：包含 `*_review.tex` 与 `.bib`
- 可选 `--tex`：指定 tex 文件名

## 输出

- `{work_dir}/.check-review-alignment/ai_alignment_report.md`
- `{work_dir}/.check-review-alignment/ai_alignment_input.json`
- 修改后的 `{主题}_review.tex`
- 新生成的 `{主题}_review.pdf`
- 新生成的 `{主题}_review.docx`

## 修改边界

- P0：必须修，允许最小改写或修正错误 bibkey
- P1：仅警告，不改写
- P2：完全跳过
- 禁止：
  - 改写未包含引用的句子
  - 整段重写
  - 引入新 bibkey（除非修复错误 key）
  - 伪造论文内容

## 工作流

### 1. 依赖检查

- 只有执行渲染时才强制检查 `systematic-literature-review`
- 若只是 `--prepare`，不要求渲染依赖可用

### 2. 预检与定位

- 找到 `*_review.tex` 与对应 `.bib`
- 缺任何核心文件时立即停止

### 3. 结构化上下文抽取

```bash
cd /path/to/check-review-alignment
python3 scripts/run_ai_alignment.py --work-dir "/path/to/work_dir" --prepare
```

- 生成 `ai_alignment_input.json`
- 输入中至少包含：句子、bibkey、文献元信息、DOI/URL、PDF 摘要段或 BibTeX 摘要

### 4. AI 语义核查

- 证据优先级：PDF 摘要段 > BibTeX abstract/title > 仅从句子推断
- 每条引用都要判断是否为：
  - `fake_citation`
  - `wrong_citation`
  - `contradictory_citation`
  - `weak_support`
  - `overclaim`
  - `style_issue`
- 无法确认时保持原样，并记录到 Warnings

### 5. 报告

- 报告至少包含：
  - Summary
  - 具体细节
  - Critical Fixes (P0)
  - Warnings (P1)
  - Rendering Result
- 每条引用的细节至少包含：标题、DOI、原句、文献实际内容、合理性评估、问题级别

### 6. 渲染

```bash
cd /path/to/check-review-alignment
python3 scripts/run_ai_alignment.py --work-dir "/path/to/work_dir" --render
```

## 核心原则

- 不为了改而改
- 无法确认时不动
- 只改必要句子
- 保留所有 LaTeX 命令结构

## 参考与验证

- 配置见 `config.yaml`
- 脚本入口：`scripts/run_ai_alignment.py`
- 渲染依赖：`systematic-literature-review`
