---
name: nsfc-ref-alignment
description: 检查 NSFC 标书正文引用与参考文献的一致性与真实性风险（只读）：核查 bibkey 是否存在、BibTeX 字段与 DOI 等格式问题，并生成结构化输入供宿主 AI 逐条评估“正文表述是否真的在引用该文献”；默认仅输出审核报告，不直接修改标书或 .bib（除非用户明确要求）。

metadata:
  author: Bensz Conan
  short-description: NSFC 标书引用/参考文献一致性核查（只读 + 报告制）
  keywords:
    - NSFC
    - LaTeX
    - BibTeX
    - 引用核查
    - 语义一致性
  related_skills:
    - check-review-alignment
    - nsfc-bib-manager
---

# NSFC Ref Alignment

## 适用场景
- 你有一份 NSFC 标书（LaTeX 项目），希望检查：
  - `.tex` 里所有 `\cite{...}` / `\citep{...}` / `\citet{...}` 等引用的 bibkey 是否都存在于 `.bib`
  - `.bib` 条目的基础字段是否完备、格式是否明显错误（如 DOI 非法、年份缺失）
  - 引用所在句子的“语义主张”是否与该文献（至少从 title/author/year/venue/DOI 等元信息）相匹配，是否存在乱引/过度主张/张冠李戴风险
- 你希望**只得到一份报告**先人工审核（改 `.bib` / 改正文属于大事）。

## 不适用
- 你希望“自动替换 bibkey / 自动改写正文”——本 skill 默认禁止直接修改（除非你明确要求）。
- 你只是想补齐 BibTeX 条目：优先使用 `nsfc-bib-manager`。

## 输入
- `project_root`：标书项目根目录（如 `projects/NSFC_General`）
- 可选：`main_tex`：主入口 tex（默认 `main.tex`）
- 可选：`report_dir`：报告输出目录（默认 `./references`，相对你运行 skill 的当前目录）
- 可选：`verify_online`：是否进行在线核验（默认 false；仅做确定性查询，失败降级）

## 输出（只读 + 可复现）

### 中间产物（强制）
**所有中间文件**必须托管在：

`{project_root}/.nsfc-ref-alignment/run_{YYYYMMDDHHMMSS}/`

其中 `run_{YYYYMMDDHHMMSS}` 为时间戳；如同秒重复运行，脚本会追加 `-2/-3/...`，确保多次分析不冲突。

该目录至少包含：
- `ai_ref_alignment_input.json`：结构化输入（引用位置 + 句子上下文 + 文献元信息 + 校验结果），供宿主 AI 做语义判断
- `ref_integrity_report.md`：确定性报告（缺失 bibkey、重复条目、字段缺失、DOI 格式问题等）
- `citations.csv`：逐条引用清单（file/line/bibkey/sentence）
- `bib_inventory.json`：BibTeX 清单（被引用条目与问题标注）

### 最终交付（默认）
仅输出一份**供用户审核的报告**（默认写入 `./references/`；用户可指定其他目录）：
- `NSFC-REF-ALIGNMENT-vYYYYMMDDHHMMSS.md`（如同秒重复运行，脚本会追加 `-2/-3/...` 避免覆盖）

该报告必须是“只读审查报告”，不得直接修改标书正文或 `.bib`。

## 工作流（推荐）

### 步骤 1：预检与定位
1) 确认 `project_root` 存在且包含 `main_tex`。
2) 自动解析 `main_tex` 的 `\input{}` / `\include{}` 依赖树，收集所有涉及的 `.tex` 文件。
3) 自动发现 `\bibliography{...}` / `\addbibresource{...}` 指向的 `.bib` 文件；若发现 0 个 `.bib`，则回退为在 `project_root` 下搜索 `*.bib` 并给出 warning。

### 步骤 2：确定性抽取（脚本执行）
运行脚本生成结构化输入与确定性报告：

```bash
cd /path/to/ChineseResearchLaTeX
python3 skills/nsfc-ref-alignment/scripts/run_ref_alignment.py \
  --project-root "projects/NSFC_General" \
  --main-tex "main.tex" \
  --report-dir "references" \
  --prepare
```

如需在线核验（建议只对最终稿/重点条目开启）：

```bash
python3 skills/nsfc-ref-alignment/scripts/run_ref_alignment.py \
  --project-root "projects/NSFC_General" \
  --main-tex "main.tex" \
  --report-dir "references" \
  --prepare \
  --verify-online
```

### 步骤 3：宿主 AI 语义核查（本 skill 的核心）
宿主 AI 在读取 `{run_dir}/ai_ref_alignment_input.json` 后，逐条核查：

1) **真实性/存在性**（P0）
   - bibkey 缺失：正文引用了不存在的条目
   - DOI/URL 明显无效或在线核验失败且元信息严重不一致

2) **语义不匹配风险**（P0/P1）
   - P0：句子对文献作出了“强断言”，但从元信息看高度不可能（如年份矛盾、领域完全不相关、明显张冠李戴）
   - P1：可疑但证据不足（元信息不足、缺少 DOI/缺少 title/作者信息不全）

3) **过度主张/弱支撑**（P1）
   - 例如“首次/唯一/最优/显著优于”但缺乏足够支撑或疑似需要更强引用

> 证据优先级（强制）：
> 在线核验结果（若开启） > BibTeX 的 title/abstract > 仅从句子推断（最低优先级）。

### 步骤 4：生成最终报告（只读）
在 `report_dir` 写入最终报告 `NSFC-REF-ALIGNMENT-vYYYYMMDDHHMMSS.md`，必须包含：

- Summary：总引用数、唯一 bibkey 数、缺失条目数、重复条目数、P0/P1 数
- P0（必须处理）：缺失 bibkey、明显伪造/错误元信息、严重语义错配
- P1（建议处理）：字段不全（缺 DOI/缺 year）、弱支撑/过度主张、需要人工复核
- 附录：逐条引用明细（至少包含 file/line、原句、bib 条目关键字段、风险判断与理由）

## 修改边界（强制）
- 默认**不修改**任何标书内容与配置：
  - 禁止修改：`**/*.tex`、`**/*.bib`、`**/*.cls`、`**/*.sty`
- 允许写入：
  - `{project_root}/.nsfc-ref-alignment/**`（中间产物）
  - `./references/**`（最终报告；可由用户改到别处）
- 若用户明确要求“修复引用/修复 bib”，必须先在报告里给出**修改计划**与影响面，再执行最小化修改（默认不做）。

## 与 check-review-alignment 的关系（经验复用）
- 共同点：脚本只做确定性抽取；“语义是否匹配”的判断由宿主 AI 完成；输出可追溯的结构化输入与报告。
- 不同点：本 skill 面向**标书项目**（多文件 `\input{}` 结构），且默认**不做任何自动改写**（只输出审查报告）。

## 验证清单（静态自检）
- `{project_root}/.nsfc-ref-alignment/run_{timestamp}/` 存在且包含 4 个核心产物（json/md/csv/json）。
- 最终报告写入 `report_dir`，且没有任何 `.tex/.bib` 文件被修改。
- 报告对每个 P0/P1 给出：定位（file/line）+ 原句 + 依据 + 建议动作。
