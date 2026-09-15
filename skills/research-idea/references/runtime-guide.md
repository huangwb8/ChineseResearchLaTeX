# State / Verifier 与 BSK 协作

## 职责与运行前提

本 Skill 维护五个领域 State、两个 required 语义 Verifier、一个原子启动入口和一个阶段入口。Agent 负责科研工作与语义判断；项目约定的 latest 托管 BSK 负责 run、State visit、active attempt、action authorization、handoff、Gate、transition、事件和状态快照。配置只声明 Kernel 包名，不保留旧式精确版本或静态 `required_capabilities` 清单；启动入口按实际运行时 capability 检查所需能力。

使用 Python 3.11+，并确保 `python` 与 `bsk` 来自同一解释器环境。启动入口按 capability 核对 `state_visit_identity`、`atomic_target_identity_handoff`、`attempt_supersede`、`state_bound_verifier_gate` 和 `state_bound_action_authorization`。任一缺失、解释器错配或期望 Skill 版本不符都在创建工作区前拒绝。

## 原子启动

先公开并锁定唯一任务目录，然后只调用 `start_workflow.py`。普通运行不再手工拼接 `bsk workspace init`、`init_workspace.py` 和裸初始 transition。

```bash
python "$IDEA_SKILL/scripts/start_workflow.py" \
  --project-root . \
  --task-root ".bensz-api/task-YYYYMMDD-HHMM-topic" \
  --input-label topic \
  --run-id idea-run-1 \
  --initial-attempt-id literature-a1
```

入口先完成依赖、Kernel capability、解释器和参数预检，再准备工作区，并让 BSK 建立 literature 的 v2 target identity；只有身份成功后才初始化 manifest、候选空模板和运行快照。返回 `status=initialized` 且同时包含非空 `run_id`、`state_visit_id`、`attempt_id` 才能开始业务。

运行快照位于 `research-idea/log/runtime-snapshot.json`，记录实际 Skill 版本、关键脚本/State/Verifier 哈希、Kernel 版本与 capabilities、解释器指纹和首次身份；不记录本机绝对路径。阶段入口会重算关键哈希，发生安装副本或源码漂移时返回 `skill_runtime_drift`。

`--agents`、`--rounds`、`--output-dir`、`--allow-custom-name` 仍由启动入口转交资料初始化。`--skip-dependency-check` 仅用于开发测试。

## 阶段门控

| action | 当前 State → 目标 State |
| --- | --- |
| `literature` | literature → candidates |
| `candidates` | candidates → review |
| `review` | review → reporting |
| `reporting` | reporting → completed |

每阶段开始业务前先执行 start 模式。它核对当前 v2 visit/active attempt，向 BSK 请求并立即消费单次 State-bound action authorization；只有 `status=authorized` 才能调度该阶段下游 Skill或写入标准阶段产物。

```bash
python "$IDEA_SKILL/scripts/phase_entry.py" \
  --project-root . --task-root "$IDEA_TASK" \
  --mode start --action literature
```

完成业务产物后，把 `context` 和非空 `evidence` 写入当前任务 `research-idea/input/`，再执行 finish。首次 finish 返回 required Verifier 的原生 handoff；Agent 必须读取真实来源并返回完整绑定结果，其中包括 `run_id`、`state_visit_id` 和 `attempt_id`。

```bash
python "$IDEA_SKILL/scripts/phase_entry.py" \
  --project-root . --task-root "$IDEA_TASK" \
  --mode finish --action literature \
  --input "$IDEA_TASK/research-idea/input/literature-evidence.json"

python "$IDEA_SKILL/scripts/phase_entry.py" \
  --project-root . --task-root "$IDEA_TASK" \
  --mode finish --action literature \
  --input "$IDEA_TASK/research-idea/input/literature-evidence.json" \
  --submissions "$IDEA_TASK/research-idea/input/literature-results.json"
```

全部 required 结果 completed 且 pass 时，Kernel 生成同 source visit/attempt 的 allow Gate；入口随后用 `source_identity` 离站，并为目标 State 创建新的 visit 和 initial attempt。任何缺失、错绑、非通过、超时或异常均保持当前 State。

## 重试与恢复

Verifier 失败、证据变化或需要重审时，在当前 visit 内显式 supersede attempt；旧 handoff、Gate、action authorization 和完成索引随 active attempt 变化而失效。新 attempt 建立后必须重新执行 start 和 finish。

```bash
python "$IDEA_SKILL/scripts/phase_entry.py" \
  --project-root . --task-root "$IDEA_TASK" \
  --mode retry --action literature \
  --new-attempt-id literature-a2 \
  --reason "evidence changed"
```

恢复时读取 manifest、运行快照、领域 meta-state 和 `bsk status` 投影。`legacy_state_identity`、`runtime_snapshot_missing`、`skill_runtime_drift`、`kernel_interpreter_mismatch`、`action_not_authorized`、Verifier 非通过和 transition 失败分别保留首个错误，不继续调度下游。旧任务不补写 run/visit/attempt、Gate 或运行快照，也不能获得新的 completed 资格。

State 图保留返工边供 BSK 生命周期表达；普通入口当前只实现表中四条前向 action。需要跨 State 回退时先保留原因与受影响证据，不手工改写事件或 meta-state。

## 完成证据

`validate_report.py` 只检查报告结构。正式 completed 还必须通过 `check_completion.py`：逐段核对已消费的 action authorization、同 source identity 的 required Verifier/Gate、source/target identity 转移链和 completed 当前身份。

新索引写入 `research-idea/output/completion-evidence.json`，使用 `schema: research-idea-completion-v4`；其顶层 `run_id`、`state_visit_id`、`attempt_id` 与 `authoritative_attempt` 必须从 BSK 当前 completed 快照派生。依赖产物保留内容快照与稳定来源；独立 reviewer 除 RESULT 文件外还必须记录 `thread_status: completed`、`runner_status: completed`、线程/模型、输入输出哈希及开始结束时间。只有内容而没有完成回执不能计入 required independent review。

```bash
python "$IDEA_SKILL/scripts/check_completion.py" \
  --project-root . --task-root "$IDEA_TASK" --report "{最终报告路径}"
```

`insufficient`、`degraded` 和 `bounded_recommendation` 可按其语义交付，但不能伪装为 completed。旧 completion-v2/v3 仅用于历史读取，不可回填成 v4。

## 开发验证

```bash
PYTHONDONTWRITEBYTECODE=1 python3.12 -m pytest tests/research-idea skills/research-idea/tests -q \
  -o cache_dir="$IDEA_TASK/research-idea/log/pytest-cache"
```

合成回传只证明身份、绑定、Gate 与 transition 协议，不证明科研内容真实或充分。
