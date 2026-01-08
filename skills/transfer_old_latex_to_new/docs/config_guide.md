# Config Guide（配置指南）

配置文件：`skills/transfer_old_latex_to_new/config.yaml`

## 只看这几个块就够用

- `profiles`：`quick/balanced/thorough` 三档预设（影响 AI 并发、缓存、优化轮次等）。
- `migration`：迁移轮次、默认策略、占位符文本、资源处理方式等。
- `quality_thresholds`：相似度阈值、最小字数、引用/编译错误阈值等。
- `compilation`：编译引擎与 4 步法序列、超时等（默认 `xelatex → bibtex → xelatex → xelatex`）。
- `output`：`verbose` 控制进度/日志输出。
- `workspace.runs_dir`：默认 runs 子目录名（相对 skill 根目录）。

## runs 输出隔离（推荐）

配置层面可改 `workspace.runs_dir`，但更推荐运行时用 `--runs-root`：

```bash
python skills/transfer_old_latex_to_new/scripts/run.py analyze \
  --old /path/to/old --new /path/to/new \
  --runs-root /path/to/runs
```

这样不用改配置，就能把“迁移产物/日志/快照”完全隔离到指定目录（尤其适合测试或批处理）。

## 配置校验（P1）

在运行迁移前，建议先跑一次配置校验：

```bash
python skills/transfer_old_latex_to_new/scripts/validate_config.py
```

常见可提前发现的问题包括：
- 数值阈值越界（如相似度/超时）
- 轮次配置不合理（`max_rounds < min_rounds`）
- 编译序列不符合推荐 4 步法（会给出警告）

## 可选依赖：rich 进度条

本技能会尝试使用 `rich` 显示更美观的进度条；若环境未安装 `rich`，会自动回退到纯文本进度显示，不影响功能。
