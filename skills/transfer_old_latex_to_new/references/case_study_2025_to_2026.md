# Case Study（2025 → 2026 迁移示例）

> 目标：把一个“2025 旧标书项目”的科学内容迁移到“2026 已调好格式的新模板项目”，并且 **不破坏新模板样式**。

## 场景假设

- 旧项目：`/path/to/NSFC_2025`（包含 `main.tex` 与若干 `extraTex/*.tex` 内容文件）
- 新项目：`/path/to/NSFC_2026`（同样包含 `main.tex`，但章节文件名/编号可能变化）

## 推荐执行方式

### 1) （可选）先校验配置

```bash
python skills/transfer_old_latex_to_new/scripts/validate_config.py
```

### 2) 迁移（建议隔离 runs 输出）

```bash
python skills/transfer_old_latex_to_new/scripts/run.py analyze \
  --old /path/to/NSFC_2025 \
  --new /path/to/NSFC_2026 \
  --runs-root /path/to/runs
```

得到 `run_id=<...>` 后：

```bash
python skills/transfer_old_latex_to_new/scripts/run.py apply \
  --run-id <run_id> \
  --old /path/to/NSFC_2025 \
  --new /path/to/NSFC_2026 \
  --runs-root /path/to/runs
```

### 3) 查看交付物（建议检查顺序）

- 结构差异：`runs/<run_id>/analysis/structure_diff.json`
- 迁移计划：`runs/<run_id>/plan/migration_plan.json`
- 变更摘要：`runs/<run_id>/deliverables/change_summary.md`
- 未映射旧内容清单：`runs/<run_id>/deliverables/unmapped_old_content.md`

### 4) 编译验证（可选，但建议）

```bash
python skills/transfer_old_latex_to_new/scripts/run.py compile \
  --run-id <run_id> \
  --new /path/to/NSFC_2026 \
  --runs-root /path/to/runs
```

编译中间文件会被隔离到 `runs/<run_id>/logs/latex_aux/`，不会在项目目录产生 `.aux/.log/.bbl` 等文件。

### 5) 不满意就回滚

```bash
python skills/transfer_old_latex_to_new/scripts/run.py restore \
  --run-id <run_id> \
  --new /path/to/NSFC_2026 \
  --runs-root /path/to/runs
```

## 迁移后最小验收清单

- `apply` 完成后：新项目只出现 `extraTex/*.tex` 内容变更（模板文件未动）
- `unmapped_old_content.md` 已人工确认（无遗漏关键科学内容）
- `compile` 可生成 PDF（允许警告，但不应有致命错误）

