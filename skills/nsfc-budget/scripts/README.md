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
- `--project-type`：`general|local|youth`
- `--total-budget-wan`：总预算，单位万元
- `--target-chars`：目标字数中心值（默认 900）
- `--template-id`：模板 ID（默认 `01`）
- `--output-dirname`：结果目录名（默认 `budget_output`）
- `--material`：可重复传入，用于复制材料快照到隐藏目录

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

- `<workdir>/budget_output/`：LaTeX 项目
- `<workdir>/budget_output/budget.pdf`：最终 PDF（若未 `--skip-compile`）
- `<run_dir>/validation_report.md` / `validation_report.json`：校验报告
