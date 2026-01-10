# v202601100803 轻量测试计划（nsfc-justification-writer）

目标：验证按 `plans/v202601100803.md` 落地后的 `skills/nsfc-justification-writer` 能正常运行，并确保测试产生的中间文件全部落在本目录下。

## 范围

- `validate-config`：允许 `terminology.dimensions: {}` 等空配置；Prompt/日志重构后仍能通过校验
- `diagnose`：在最小可运行项目上完成 Tier1 诊断，并可输出 JSON
- `wordcount`：输出字数统计 JSON
- `terms`：生成跨章节术语一致性（legacy 路径）
- `coach`：生成写作教练 markdown（不依赖 AI）
- `pytest`：运行 `skills/nsfc-justification-writer/tests/`（覆盖异常收紧、Prompt 单一来源、日志口径统一等改动的回归风险）

## 约束

- 不启用 AI（避免产生 `.cache/ai`、联网请求等不确定因素）
- 所有输出（JSON/Markdown/pytest cache）均写入 `tests/v202601100803/`

## 测试准备

- Fixture 项目：`tests/v202601100803/fixture_project/`
  - `extraTex/1.1.立项依据.tex`（含 4 个 `\\subsubsection`）
  - `extraTex/2.1.研究内容.tex`、`extraTex/3.1.研究基础.tex`（用于术语一致性）
  - `references/test.bib`（用于 `\\cite{...}` 校验）
- 覆盖配置：`tests/v202601100803/override.yaml`
  - `ai.enabled=false`
  - `quality.enable_ai_judgment=false`
  - `terminology.enable_ai_semantic_check=false`
  - `writing_coach.enable_ai_stage_inference=false`
  - 设置 `limits.*` 为非默认值，用于验证读取生效

## 执行命令（在仓库根目录）

1) 配置校验

`env PYTHONDONTWRITEBYTECODE=1 NSFC_JUSTIFICATION_WRITER_DISABLE_USER_OVERRIDE=1 NSFC_JUSTIFICATION_WRITER_RUNS_DIR=tests/v202601100803/tmp/runs python3 skills/nsfc-justification-writer/scripts/run.py --no-user-override --override tests/v202601100803/override.yaml validate-config`

2) Tier1 诊断（输出 JSON）

`env PYTHONDONTWRITEBYTECODE=1 NSFC_JUSTIFICATION_WRITER_DISABLE_USER_OVERRIDE=1 NSFC_JUSTIFICATION_WRITER_RUNS_DIR=tests/v202601100803/tmp/runs python3 skills/nsfc-justification-writer/scripts/run.py --no-user-override --override tests/v202601100803/override.yaml diagnose --project-root tests/v202601100803/fixture_project --json-out tests/v202601100803/out/diagnose.json`

3) 字数统计

`env PYTHONDONTWRITEBYTECODE=1 NSFC_JUSTIFICATION_WRITER_DISABLE_USER_OVERRIDE=1 NSFC_JUSTIFICATION_WRITER_RUNS_DIR=tests/v202601100803/tmp/runs python3 skills/nsfc-justification-writer/scripts/run.py --no-user-override --override tests/v202601100803/override.yaml wordcount --project-root tests/v202601100803/fixture_project > tests/v202601100803/out/wordcount.json`

4) 术语一致性

`env PYTHONDONTWRITEBYTECODE=1 NSFC_JUSTIFICATION_WRITER_DISABLE_USER_OVERRIDE=1 NSFC_JUSTIFICATION_WRITER_RUNS_DIR=tests/v202601100803/tmp/runs python3 skills/nsfc-justification-writer/scripts/run.py --no-user-override --override tests/v202601100803/override.yaml terms --project-root tests/v202601100803/fixture_project --out tests/v202601100803/out/terms.md`

5) 写作教练

`env PYTHONDONTWRITEBYTECODE=1 NSFC_JUSTIFICATION_WRITER_DISABLE_USER_OVERRIDE=1 NSFC_JUSTIFICATION_WRITER_RUNS_DIR=tests/v202601100803/tmp/runs python3 skills/nsfc-justification-writer/scripts/run.py --no-user-override --override tests/v202601100803/override.yaml coach --project-root tests/v202601100803/fixture_project --out tests/v202601100803/out/coach.md`

6) 单测（pytest）

`env PYTHONDONTWRITEBYTECODE=1 NSFC_JUSTIFICATION_WRITER_DISABLE_USER_OVERRIDE=1 NSFC_JUSTIFICATION_WRITER_RUNS_DIR=tests/v202601100803/tmp/runs python3 -m pytest skills/nsfc-justification-writer/tests -q --cache-dir tests/v202601100803/tmp/pytest_cache > tests/v202601100803/out/pytest.txt`

## 预期结果

- 命令均返回退出码 0
- `tests/v202601100803/out/` 产生对应输出文件
- 仓库其他位置不产生测试产物（尤其是 `skills/nsfc-justification-writer/runs/`、`skills/nsfc-justification-writer/.cache/`、`skills/nsfc-justification-writer/.pytest_cache/`）

