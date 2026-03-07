# Changelog

本文件记录 `nsfc-budget` skill 的变更历史。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)。

## [0.1.0] - 2026-03-07

### Added

- 初始版本：新增 `nsfc-budget` skill，用于基于 NSFC 标书正文/补充材料生成预算说明书 LaTeX 项目并渲染 `budget.pdf`
- 新增模板元数据：`skills/nsfc-budget/models/01/.template.yaml`，为后续多模板扩展预留接口
- 新增初始化脚本：`skills/nsfc-budget/scripts/init_budget_run.py`，统一创建 `.nsfc-budget/run_xxx/` 隐藏工作区与 `budget_spec.json`
- 新增渲染脚本：`skills/nsfc-budget/scripts/render_budget_project.py`，负责校验预算结构、写入 `extraTex/*.tex`、生成校验报告并编译 PDF
- 新增参考文档：`skills/nsfc-budget/references/info_form.md` 与 `skills/nsfc-budget/references/budget-writing-rules.md`
- 新增回归测试：`skills/nsfc-budget/tests/test_render_budget_project.py`

## [0.1.1] - 2026-03-07

### Fixed

- `render_budget_project.py`：补齐 `output_dirname`、`template_id`、`--spec` 与模板元数据路径的安全校验，防止越界写入或读取
- `render_budget_project.py`：改为从 `config.yaml` / `.template.yaml` 读取 `section_files`、`zero_text`、`compile_runs`、`latex_entry`、`pdf_name`，消除关键配置硬编码
- `render_budget_project.py`：强制校验 `budget.*_wan` 与 `sections.*.amount_wan` 一致，并在 `--skip-compile` 时明确返回 `pdf: null`
- `render_budget_project.py`：`xelatex` 缺失时给出明确错误信息，便于排障
- `init_budget_run.py`：改为从 `config.yaml` 读取默认值与中间目录名，并拒绝不安全的 `output_dirname` / `template_id`

### Added

- 新增运行时公共工具：`skills/nsfc-budget/scripts/runtime_utils.py`
- 新增路径安全与一致性回归测试：覆盖 `output_dirname` 越界、`spec` 越界、金额不一致、`template_id` 越界、`--skip-compile` manifest 等场景
