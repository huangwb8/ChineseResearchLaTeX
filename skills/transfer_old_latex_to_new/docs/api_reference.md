# API Reference（接口参考）

> 面向二次开发/排障：理解内部模块与核心产物（JSON/Markdown）。

## CLI（scripts/run.py）

- `analyze`：解析旧新项目结构，生成 `analysis/structure_diff.json` 与 `plan/migration_plan.json`。
- `apply`：按计划写入新项目（默认跳过低置信度/需人工任务），并生成 `deliverables/change_summary.md`。
- `compile`：对新项目执行 4 步编译，日志隔离到 `logs/latex_aux/`，并生成 `logs/compile_summary.json`。
- `restore`：将新项目恢复到 apply 前快照（`backup/`）。

通用建议参数：
- `--runs-root /path/to/runs`：指定 runs 输出根目录（用于隔离输出/测试/批处理）。

## 关键产物（格式）

### `analysis/structure_diff.json`

结构差异与映射推断结果（one-to-one / new_added / removed / low_confidence 等）。

### `plan/migration_plan.json`

迁移任务列表（`copy_one_to_one` / `placeholder_new_added` / `needs_manual`）。

### `logs/apply_result.json`

apply 执行结果（applied/skipped/warnings/resources/references/optimization/adaptation）。

## 核心模块

- `core/project_analyzer.py`：解析 `main.tex` 与 `\\input{}` 链路，提取 headings/labels/refs/cites。
- `core/mapping_engine.py`：生成结构差异；可选走 `core/ai_integration.py`，不可用时回退启发式。
- `core/migration_plan.py`：由 diff 生成计划（任务类型、备注、置信度等）。
- `core/migrator.py`：执行迁移 +（可选）内容优化 +（可选）字数适配 + 资源复制 + 引用完整性检查。
- `core/compiler.py`：编译 4 步法；中间文件隔离到 `logs/latex_aux/`，成功后复制 `main.pdf` 回项目根目录。
- `core/security_manager.py`：写入白名单校验（禁止触碰模板系统文件）。

