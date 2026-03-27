# 脚本职责矩阵

本文件说明 `make-latex-model` 当前有哪些脚本能力，以及它们分别适合什么任务。

## 跨产品线辅助脚本

以下脚本可作为通用辅助工具使用：

- `scripts/check_state.py`
  用于识别项目产品线、检查初始化标记、基线与官方构建入口。
- `scripts/plan_package_regression.py`
  用于在修改 `packages/bensz-*` 前生成回归矩阵。
- `scripts/analyze_pdf.py`
  用于提取 PDF 基线参数，不限定产品线。
- `scripts/compare_headings.py`
  用于标题文本或格式比对。
- `scripts/compare_pdf_pixels.py`
  用于像素级 PDF 对比。
- `scripts/optimize_heading_linebreaks.py`
  用于根据 PDF 基线优化标题换行。

## NSFC 专项工具

以下脚本主要服务 NSFC 参数对齐、批量校验或基于模板配置的专项分析：

- `scripts/validate.sh`
- `scripts/validate.bat`
- `scripts/benchmark.sh`
- `scripts/benchmark.bat`
- `scripts/optimize.sh`
- `scripts/optimize.bat`
- `scripts/optimize.py`
- `scripts/enhanced_optimize.py`
- `scripts/run_ai_optimizer.py`
- `scripts/intelligent_adjust.py`
- `scripts/sync_config.py`
- `templates/nsfc/*.yaml`
- `core/config_loader.py`

这些工具适合下列场景：

1. 目标明确是 `projects/NSFC_*`。
2. 任务需要做 NSFC 参数级调优、批量实验或基于模板 YAML 的专项分析。
3. 官方产品线脚本已覆盖主构建，但你还需要额外的 NSFC 诊断能力。

## 使用约束

- 不要拿 NSFC 专项工具替代 `paper_project_tool.py`、`thesis_project_tool.py` 或 `cv_project_tool.py`。
- 不要把 thesis / paper / cv 强行解释成“只要改 `@config.tex` 就行”的问题。
- 对任何产品线，官方构建脚本始终优先于本目录的分析脚本。
