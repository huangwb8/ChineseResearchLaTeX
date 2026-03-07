# Changelog

本文件记录 `nsfc-budget` skill 的变更历史。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)。

## [0.1.2] - 2026-03-07

### Fixed

- `init_budget_run.py` / `render_budget_project.py`：拒绝将 `output_dirname` 设为工作目录根路径或与 `.nsfc-budget/` 隐藏工作区重叠，修复 `--force` 可能误删工作目录/活动 run 的高风险边界
- `init_budget_run.py`：重复初始化同秒 run 时自动避让目录名冲突，修复隐藏工作区会话互相覆盖的问题
- `render_budget_project.py`：允许写入已存在但为空的输出目录，避免“空目录也报 File exists”导致的伪失败
- `render_budget_project.py`：校验失败时在终端直接输出首批错误摘要和 `validation_report.md` 路径，降低排障成本
- `render_budget_project.py`：新增 `meta.project_type` / 金额 / 字数 / 容差等非负与枚举校验，拒绝非法 spec 漏网通过
- `render_budget_project.py`：写入段落时自动转义 `%`、`#`、`&`、`_`、`{`、`}` 等常见 LaTeX 特殊字符，修复自然语言正文导致的编译失败

### Changed

- `config.yaml`：将项目类型、预算模式、预算口径集中到配置中，减少 `SKILL.md` / README / 脚本的枚举分叉
- `SKILL.md` / `README.md` / `scripts/README.md`：同步安全约束、目录覆盖规则、特殊字符转义行为与配置引用口径

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
