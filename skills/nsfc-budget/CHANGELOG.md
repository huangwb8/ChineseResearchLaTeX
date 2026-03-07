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
