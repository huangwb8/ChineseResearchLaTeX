# nsfc-justification-writer 轻量测试计划（v202601101300）

## 目标

- 验证 `skills/nsfc-justification-writer` 在修复 P0-P2 后可正常导入与运行。
- 确认 `style.mode` 风格开关能贯通到 `coach` 与 `review` 的 AI Prompt（至少不报错，且能在回退路径中体现）。
- 所有测试产物（输出/日志/临时文件）仅落在 `tests/v202601101300/` 目录下。

## 测试约束

- 不修改任何 `projects/*` 下的 LaTeX 正文与模板文件（仅只读）。
- 禁用 AI（避免网络与缓存写入），仅验证“优雅降级/回退路径”可运行。

## 运行配置

- 统一使用 `--override tests/v202601101300/override.yaml`
- 统一设置环境变量：`NSFC_JUSTIFICATION_WRITER_RUNS_DIR=../../tests/v202601101300/runs`

## 测试用例

### TC1：Python 语法/可导入性（P0 回归）

- 命令：对 `skills/nsfc-justification-writer/**/*.py` 执行 `py_compile`
- 预期：无 `SyntaxError`
- 产物：`tests/v202601101300/out_py_compile.txt`

### TC2：配置校验

- 命令：`scripts/run.py --override ... validate-config`
- 预期：输出 `✅ 配置有效`
- 产物：`tests/v202601101300/out_validate_config.txt`

### TC3：运行自检（不依赖 AI）

- 命令：`scripts/run.py --override ... check-ai`
- 预期：明确提示 AI 被关闭或处于降级模式，但命令正常退出
- 产物：`tests/v202601101300/out_check_ai.txt`

### TC4：核心只读命令链路（coach / diagnose / review / terms）

- 命令：
  - `scripts/run.py --override ... coach --project-root projects/NSFC_Young --stage auto`
  - `scripts/run.py --override ... diagnose --project-root projects/NSFC_Young --json-out ...`
  - `scripts/run.py --override ... review --project-root projects/NSFC_Young`
  - `scripts/run.py --override ... terms --project-root projects/NSFC_Young`
- 预期：
  - 命令均能运行并输出（无异常堆栈）
  - `coach` 输出中包含“写作导向”相关文字（来自 `style_preamble` 注入或回退路径）
  - `diagnose --json-out` 生成 JSON 文件
- 产物：
  - `tests/v202601101300/out_coach.txt`
  - `tests/v202601101300/out_diagnose.txt`
  - `tests/v202601101300/diagnose.json`
  - `tests/v202601101300/out_review.txt`
  - `tests/v202601101300/out_terms.txt`
