# nsfc-qc 变更日志

本文档记录 `nsfc-qc/` 的重要变更。格式遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)。

## [Unreleased]

（暂无）

## [0.1.5] - 2026-02-17

### Changed（变更）
- `scripts/nsfc_qc_run.py`：默认工作区从 `QC/{run_id}.nsfc-qc/` 调整为交付目录内的隐藏目录 `QC/{run_id}/.nsfc-qc/`（更优雅，且更符合“交付目录内隐藏中间产物”的直觉）
- `scripts/nsfc_qc_run.py`：交付目录不再复制预检/编译等中间 artifacts（这些文件保留在工作区 run 目录下），交付目录只保留最终报告与结构化输出
- `SKILL.md`、`README.md`、`config.yaml`：同步更新默认产物布局说明与版本号

## [0.1.4] - 2026-02-17

### Added（新增）
- `scripts/nsfc_qc_run.py`：新增“一键实例隔离”运行器，默认输出到 `QC/{run_id}/` + sidecar 工作区 `QC/{run_id}.nsfc-qc/`，避免污染标书根目录
- `scripts/validate_final_outputs.py`：新增 final 输出一致性校验脚本（报告固定章节 + findings JSON 与表格行一致）
- `final/validation.json`：final 目录新增结构一致性校验结果（由 `materialize_final_outputs.py` 生成）

### Changed（变更）
- `scripts/run_parallel_qc.py`：支持 `--workspace-dir` 重定向所有中间产物；run_id 冲突自动后缀 `r1/r2...`；parallel-vibe 不可用/plan-only 也会落盘 final 输出
- `scripts/materialize_final_outputs.py`：支持 `--run-dir` 模式；metrics/artifacts 路径改为相对 run_dir（更可搬运）；把 precheck/compile 的确定性信号映射为“底线 findings”，并注入报告 P0/P1/P2 表格
- `scripts/nsfc_qc_precheck.py`、`scripts/nsfc_qc_compile.py`：compile.json 相关路径字段优先输出相对 out_dir（同时保留 *_abs），提升搬运一致性
- `SKILL.md`、`README.md`、`config.yaml`：更新默认产物布局与脚本用法说明

## [0.1.2] - 2026-02-16

### Added（新增）
- `scripts/nsfc_qc_precheck.py`：新增直引号排版预检，检测 `"免疫景观"` 这类写法并输出 `quote_issues.csv` 与结构化统计（建议替换为 TeX 引号 ``免疫景观''）

### Changed（变更）
- `scripts/materialize_final_outputs.py`：metrics 聚合时纳入 `typography` 预检信息，并补齐 `quote_issues.csv` 产物索引
- `SKILL.md`/`README.md`/`references/qc_checklist.md`：补齐“中文双引号/直引号”排版检查项说明

## [0.1.3] - 2026-02-16

### Added（新增）
- `scripts/nsfc_qc_precheck.py`：新增“引用证据包”硬编码抓取（题目/摘要/可选 OA PDF 片段）+ 标书内引用上下文提取，输出 `reference_evidence.jsonl`/`reference_evidence_summary.json`，供 AI 做语义核查
- `scripts/nsfc_qc_compile.py`：新增“4 步法隔离编译”脚本（xelatex→bibtex→xelatex→xelatex），作为 QC 的最后一步执行，并回填 metrics

### Changed（变更）
- `scripts/run_parallel_qc.py`：默认先跑预检并把证据包复制到 snapshot 的 `./.nsfc-qc_input/`，thread 可只读使用；可选 `--compile-last` 作为最后一步更新编译信息
- `SKILL.md`/`README.md`/`references/qc_checklist.md`：明确“引用真伪=硬编码证据 + AI 语义判断”“4 步法编译=QC 最后一步”

## [0.1.1] - 2026-02-16

### Changed（变更）
- `scripts/nsfc_qc_precheck.py`：`--compile` 在缺少 TeX 工具链时自动降级并记录 `missing_tools`，不再崩溃
- `scripts/run_parallel_qc.py`：thread prompt 以 cwd 为根（`project_root=.`），避免引导绝对路径越界；移除用户目录硬编码，支持 `PARALLEL_VIBE_SCRIPT` 覆盖
- `scripts/run_parallel_qc.py`：snapshot 文件去写权限（目录保留可写），强化“只读 QC”约束落地
- `SKILL.md`：修正文档与产物命名不一致（`tex_lengths.csv`）

### Added（新增）
- `scripts/materialize_final_outputs.py`：确定性落盘标准化 final 输出骨架（report/metrics/findings），即使 threads 尚未运行也可生成

## [0.1.0] - 2026-02-16

### Added（新增）
- 新增 `nsfc-qc`：NSFC 标书只读质量控制 skill（多线程并行 QC + 标准化报告输出）
- `SKILL.md`：定义只读边界（不修改 `.tex/.bib/.cls/.sty`）、中间文件归档到 `.nsfc-qc/`、固定报告结构与 P0/P1/P2 分级
- `config.yaml`：提供默认参数（threads=5、execution=serial、page_limit_soft=30 等）与输出契约
- `scripts/nsfc_qc_precheck.py`：确定性预检（引用 key 完整性、粗略篇幅统计；可选隔离编译以估算页数）
- `scripts/run_parallel_qc.py`：在 `.nsfc-qc/` 内运行 parallel-vibe，并生成确定性 plan（各 thread 执行同一份 QC 清单）
- `templates/`：提供标准化报告模板与 findings JSON schema
- `references/qc_checklist.md`：给多线程 QC 的统一检查清单参考
