# nsfc-qc 变更日志

本文档记录 `nsfc-qc/` 的重要变更。格式遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)。

## [Unreleased]

（暂无）

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
