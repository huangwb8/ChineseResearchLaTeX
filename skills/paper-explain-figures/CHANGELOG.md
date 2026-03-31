# paper-explain-figures - 变更日志

本文档记录 `paper-explain-figures/` skill 的重要变更。格式遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)。

## [Unreleased]

## [0.2.0] - 2026-03-26

### Changed（变更）

- skill 正式从 `explain-figures` 更名为 `paper-explain-figures`；目录名、元数据、README、Prompt 示例与项目级索引同步切换到新名称。
- 默认中间产物目录从 `.explain-figures/` 调整为 `.paper-explain-figures/`，默认最终报告文件从 `explain-figures_report.md` 调整为 `paper-explain-figures_report.md`。
- 主入口脚本从 `scripts/explain_figures.py` 重命名为 `scripts/paper_explain_figures.py`，相关命令示例、测试说明与引用路径同步更新。
- 为满足“除最终结果文件外，所有中间文件必须严格收纳到 `.paper-explain-figures/`”的硬约束：禁用 `shell` runner；`codex`/`claude`/`local` runner 与图片转换器的 `HOME/TMP/XDG` 运行时目录统一重定向到 job 内 `_runtime/`；任务结束前新增当前工作目录泄露审计与自动清理。
- 为降低 `codex exec`/`claude -p` 在受限工作区下读取“绝对路径 figure”的失败概率：每个 job 会复制一份原始 figure 到 job 目录，并在 prompt 中优先引用工作区内的副本与 `figure.jpg`（报告仍引用用户原始绝对路径）。
- `--code-path` 输入增强校验：必须为存在的绝对文件路径。
- 并发上限以 `config.yaml:defaults.max_parallel` 为单一真相来源：当 CLI 传入更大值时自动降级并记录到 `run.json`。
- 源代码检索准确性与安全性增强：增加 `code_search_min_stem_len` 限制短 stem 的弱匹配误报，并在写入 prompt 前对代码片段做常见密钥/Token 模式的最小化脱敏。
- `SKILL.md` 补充 `--runner shell` 风险提示，避免误把“可编排”当成“安全沙箱”。

### Fixed（修复）

- 修复源代码检索在 figure 位于文件系统根附近时可能误扫到根目录导致运行卡住的问题（不再扫描 `/` 等文件系统 root）。
- 修复 `--out` 非法时“先跑一轮再失败”的问题：现在会在运行前 fail-fast，并强制报告输出路径必须位于当前工作目录内（避免意外写到任意绝对路径）。
- 修复 `local` runner 的离线测试可追溯性：现在会从 `job.json` 读取 `orig_path/code_ref` 输出到 `analysis.md`，确保多图合并与报告引用可验证。

## [0.1.0] - 2026-03-02

### Added（新增）

- 初始化 `paper-explain-figures`：支持多 figure 输入、`.paper-explain-figures/` 中间目录硬约束、自动源代码检索、使用 `codex exec`/`claude -p` 进程级隔离解读、最终合并输出 `paper-explain-figures_report.md`。
