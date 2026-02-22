# Changelog

All notable changes to this skill will be documented in this file.

The format is based on Keep a Changelog, and this skill adheres to Semantic Versioning.

## [Unreleased]

### Added
- 轻量测试会话：新增 `tests/硬编码与AI规划-人工优化-v202602212332/`，验证“报告产物可完全落在 tests 目录内（--out-dir / 默认输出）”且章节级统计可用。

### Changed
- `SKILL.md`：明确“步骤 2 → 读取报告 → 步骤 3”的显式交接指令，避免跳过报告直接改写。
- `SKILL.md`：补充章节级统计（`sections`）的使用口径，指导在文件内做定点改写而非平均删改。
- `SKILL.md`：在改写步骤末尾增加强制复检提示，强化闭环。
- `SKILL.md`：为“三部分该瘦/该厚清单”增加按 `delta` 触发的使用方式，降低泛化建议风险。

## [0.3.0] - 2026-02-21

### Added
- `scripts/check_length.py`：新增 LaTeX “主入口解析”能力：当输入目录可识别 `main.tex`（或其他包含 `\documentclass` + `\begin{document}` 的入口文件）时，沿 `\input/\include/\subfile` 依赖树收集“实际会编译进 PDF 的文件”，并忽略被注释掉的 `\input{...}`（避免把可选章节误计入篇幅）。
- `scripts/check_length.py`：章节切分改为“支持跨行 + 嵌套花括号”的最小解析器（更贴近 `NSFC_Young` / `NSFC_General` 模板的 `\texorpdfstring{...}{...}` 等写法）。
- `templates/LENGTH_REPORT_TEMPLATE.md`：报告总览新增“文件发现模式 / main.tex”字段，便于解释统计范围（filesystem 扫描 vs latex_inputs）。

### Changed
- `config.yaml`：默认只统计 `*.tex`（避免把同目录 README/笔记等 Markdown 误计入篇幅）；并新增 `checker.latex.follow_inputs=auto` 以适配 NSFC_Young / NSFC_General 模板的真实编译结构。
- `README.md` / `SKILL.md`：补充针对 NSFC_Young / NSFC_General 模板的推荐用法说明。

### Fixed
- `scripts/check_length.py`：当默认输出目录不可写（例如模板仓库只读）时，给出明确错误与 `--out-dir` 提示并以退出码=2 退出（避免直接抛 traceback）。

## [0.2.1] - 2026-02-21

### Changed
- `config.yaml`：补充“创新/计划拆分成独立文件时需从研究内容预算等额扣除”的口径，避免双重计量导致误判。
- `SKILL.md`：新增 2026 三部分（立项依据/研究内容/研究基础）“该瘦/该厚”优先级清单，便于按差距快速定位改写方向。

## [0.2.0] - 2026-02-21

### Added
- `scripts/check_length.py`：新增 `--pdf`（可选）统计 PDF 页数；在报告中输出页数预算（建议 max / 硬上限 hard_max）与页数偏差。

### Changed
- `config.yaml`：默认篇幅口径对齐 2026 调研建议（三大部分 + 总预算区间），新增 `length_standard.pages`（页数硬约束）。
- `scripts/check_length.py`：`length_standard.overall` 支持 `min/max`；并在 JSON/MD 报告中结构化输出 overall/page 预算信息。
- `templates/LENGTH_REPORT_TEMPLATE.md`：总览补齐 PDF/页数预算与偏差信息，明确“页数硬约束、字符预算为可复检代理指标”的口径。
- `references/DEFAULT_STANDARD_NOTES.md` / `README.md` / `SKILL.md`：同步更新 2026+ 页数优先策略与使用说明。

### Fixed
- `scripts/check_length.py`：`checker.latex.section_commands` 真正生效；跳过空章节段，避免 “(no section)” 噪音。
- `scripts/check_length.py`：复检时默认排除 `_artifacts/`，避免把旧报告计入篇幅；glob 匹配兼容 `**/` 前缀与 root-relative 路径，确保排除规则生效。

## [0.1.0] - 2026-02-21

### Added
- 初始化 `nsfc-length-aligner` demo：内置示例篇幅标准、篇幅检查脚本、差距报告模板与使用说明。
