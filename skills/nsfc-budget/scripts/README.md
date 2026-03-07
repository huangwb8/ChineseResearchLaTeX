# nsfc-budget scripts

## `init_budget_run.py`

用途：在用户工作目录下创建隐藏工作区 `.nsfc-budget/run_xxx/`，并生成 `budget_spec.json` 骨架。

示例：

```bash
python3 skills/nsfc-budget/scripts/init_budget_run.py \
  --workdir ./projects/NSFC_General \
  --project-type general \
  --material ./projects/NSFC_General/main.tex
```

常用参数：

- `--workdir`：工作目录，必需
- `--project-type`：合法值见 `skills/nsfc-budget/config.yaml`
- `--total-budget-wan`：总预算，单位万元
- `--target-chars`：目标字数中心值（默认值见 `skills/nsfc-budget/config.yaml`）
- `--template-id`：模板 ID（默认值见 `skills/nsfc-budget/config.yaml`）
- `--output-dirname`：结果目录名（默认值见 `skills/nsfc-budget/config.yaml`）
- `--material`：可重复传入，用于复制材料快照到隐藏目录

约束：

- `--output-dirname` 只能是工作目录下的相对安全路径，且不能是 `.` 或与 `.nsfc-budget/` 重叠
- `--template-id` 只能指向 `skills/nsfc-budget/models/` 下的模板目录
- 同秒重复初始化时，脚本会自动避让目录名冲突

## `render_budget_project.py`

用途：读取 `budget_spec.json`，校验预算结构与文本长度，写入 LaTeX 项目并编译 `budget.pdf`。

示例：

```bash
python3 skills/nsfc-budget/scripts/render_budget_project.py \
  --spec ./projects/NSFC_General/.nsfc-budget/run_20260307120000/budget_spec.json
```

常用参数：

- `--spec`：`budget_spec.json` 路径，必需
- `--force`：若输出目录已存在，则先删除再重建
- `--skip-compile`：只生成 LaTeX 项目，不编译 PDF

输出：

- `<workdir>/<output_dirname>/`：LaTeX 项目
- `<workdir>/<output_dirname>/budget.pdf`：最终 PDF（若未 `--skip-compile`）
- `<run_dir>/validation_report.md` / `validation_report.json`：校验报告

额外说明：

- `--spec` 必须位于 `<workdir>/.nsfc-budget/` 内，否则会被拒绝
- 目录为空时可直接渲染；目录非空时需显式传 `--force`
- `deliverables_manifest.json` 在 `--skip-compile` 时会返回 `"pdf": null` 与 `"pdf_generated": false`
- 运行时公共工具位于 `skills/nsfc-budget/scripts/runtime_utils.py`
- 常见 LaTeX 特殊字符（`%`、`#`、`&`、`_` 等）会在写入段落时自动转义
