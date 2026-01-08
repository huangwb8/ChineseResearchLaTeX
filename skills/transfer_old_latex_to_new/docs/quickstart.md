# Quickstart（快速开始）

> 本目录是 `transfer_old_latex_to_new` 的“拆分文档”。核心入口仍是 `scripts/run.py`。

## 一句话理解

给你一个“旧版标书 LaTeX 项目”和一个“已调好样式的新版模板 LaTeX 项目”，本技能只迁移**内容**到新版项目的 `extraTex/*.tex`（严格避开 `main.tex` / `extraTex/@config.tex` / `.cls` / `.sty`）。

## 最快用法：一键迁移

```bash
bash skills/transfer_old_latex_to_new/scripts/migrate.sh \
  --old /path/to/NSFC_2025 \
  --new /path/to/NSFC_2026
```

如需把所有 runs 产物隔离到指定目录（推荐：测试/CI）：

```bash
bash skills/transfer_old_latex_to_new/scripts/migrate.sh \
  --old /path/to/NSFC_2025 \
  --new /path/to/NSFC_2026 \
  --runs-root /path/to/runs
```

## 标准用法：run.py 四步闭环

```bash
python skills/transfer_old_latex_to_new/scripts/run.py analyze \
  --old /path/to/NSFC_2025 \
  --new /path/to/NSFC_2026

python skills/transfer_old_latex_to_new/scripts/run.py apply \
  --run-id <run_id> \
  --old /path/to/NSFC_2025 \
  --new /path/to/NSFC_2026

python skills/transfer_old_latex_to_new/scripts/run.py compile \
  --run-id <run_id> \
  --new /path/to/NSFC_2026

python skills/transfer_old_latex_to_new/scripts/run.py restore \
  --run-id <run_id> \
  --new /path/to/NSFC_2026
```

### 关键参数速查

- `--no-ai`：禁用 AI（会自动走启发式/保守回退，保证能跑通）。
- `--strategy smart|conservative|aggressive|fallback`：迁移策略（fallback 强制不用 AI）。
- `--allow-low`：允许执行“低置信度”任务（谨慎）。
- `--optimize`：迁移后对已复制文件做内容优化（需在配置启用）。
- `--adapt-word-count`：迁移后做字数适配（需在配置启用）。
- `--runs-root /path/to/runs`：将 runs 产物输出到指定目录（用于隔离输出/测试）。

## 输出目录（runs）

默认输出在 `skills/transfer_old_latex_to_new/runs/<run_id>/`；如果使用了 `--runs-root`，则输出在你指定的目录。

```
runs/<run_id>/
├── input_snapshot/
├── analysis/
├── plan/
├── backup/
├── logs/
│   └── latex_aux/
└── deliverables/
```

交付物（Markdown 报告）主要在 `deliverables/`，编译相关日志在 `logs/`。

