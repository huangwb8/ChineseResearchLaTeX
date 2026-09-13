# State / Verifier 与 bsk 的协作

## 职责与环境

本 Skill 仅维护五个 [STATE.md](states/index.json)、两个 required 语义 Verifier（[阶段就绪](verifiers/stage-readiness/VERIFIER.md)、[科学假设价值](verifiers/hypothesis-merit/VERIFIER.md)）和领域报告检查。Agent 读取契约、执行研究、核验证据；bsk 负责 Pack 解析、结果绑定、Gate、事件和状态持久化。不要另写 Skill 运行时、锁、检查点或事件重放器。

使用 Python 3.11+ 和满足 `config.yaml.dependencies.kernel` 最低版本的 `bensz-skill-kernel`。在项目已有合适环境中运行，或用 `.bensz-api/.venv` 安装声明的依赖；包名不是 `bsk`。先核对 `python --version`、`python -m pip show bensz-skill-kernel`、`bsk --version` 及 CLI 实际路径属于同一环境。当前兼容路径在 Kernel 2.1.0 验证；后续版本需重跑定向检查，不能仅凭版本更高推断兼容。

最低版本放在 `dependencies.kernel`；`runtime` 只声明 State、required Verifier 和阶段入口兼容模式，交给原生加载器。Kernel 2.1.0 的事件投影和 State 进入身份校验是当前入口的最低真实接口；Skill 不自行增加版本解析或 State visit 实现。

## 初始化与阶段

### 轻量 BSK 阶段入口

`phase_entry.py` 只把容易遗漏的 BSK 调用收敛到一个命令，不维护第二套运行时。action 固定对应四条前向边：

| action | 当前 State → 目标 State |
| --- | --- |
| `literature` | literature → candidates |
| `candidates` | candidates → review |
| `review` | review → reporting |
| `reporting` | reporting → completed |

每个阶段完成业务产物后，将 `context` 和非空 `evidence` 数组写入本 Skill `input/` 下的 JSON。首次调用不带 `--submissions`，入口通过 Kernel 快照与事件投影核对当前 State 及其进入身份，从 Skill 声明加载全部 required Verifier，并返回 BSK 原生 handoff：

```bash
python "$IDEA_SKILL/scripts/phase_entry.py" \
  --project-root . --task-root "$IDEA_TASK" --action literature \
  --input "$IDEA_TASK/research-idea/input/literature-evidence.json"
```

Agent 必须读取真实来源并按 handoff 生成绑定的 component-result；把一个结果对象或 `{ "submissions": [...] }` 保存到本 Skill `input/` 后，用相同 action/input 再次调用并增加 `--submissions`。入口继续使用当前 State 的权威进入身份，批量提交全部 required Verifier，由 Kernel 计算 Gate；非 allow 返回拒绝，allow 后直接执行 BSK transition，并同时检查返回 `status=transitioned` 与目标快照。

入口不写 attempt/handoff/rejection/provenance 私有记录，不手工解析 `meta-state.json` 或扫描 `events.ndjson`，只消费 `TaskWorkspace` 与 `EventLog.projection()` 的公开结果。BSK 的 State、绑定、Gate 和事件是唯一事实源；完成收敛检查是 Agent 绕过入口时的第二道防线。

先公开并固定唯一任务目录。在项目根运行，以下 shell 变量需替换为本轮真实路径；`python` 与 `bsk` 使用同一环境：

```bash
export IDEA_SKILL="$(pwd)/skills/research-idea"
export IDEA_TASK=".bensz-api/task-YYYYMMDD-HHMM-topic"
export IDEA_RUN="idea-run-1"
export IDEA_ATTEMPT="idea-run-attempt-1"
bsk workspace init . --task-root "$IDEA_TASK"
python "$IDEA_SKILL/scripts/init_workspace.py" --cwd . --task-root "$IDEA_TASK" --input-label topic
bsk state transition "$IDEA_TASK" research-idea bensz.research-ideation.literature \
  --skill-root "$IDEA_SKILL" --run-id "$IDEA_RUN" --attempt-id "$IDEA_ATTEMPT"
```

安装后将 `IDEA_SKILL` 改为实际安装路径。`init_workspace.py` 只生成 `research-idea/input/manifest.json`（研究参数和正式报告路径）及 `output/candidate-schema.json`（空候选池与独立示例）；不生成状态、事件或科研结论。用户指定人数/轮次时增加 `--agents N --rounds N`，自定义文件名时增加 `--allow-custom-name`。`--skip-dependency-check` 仅用于开发测试。

State 的初始入口复用内置 `bensz.workspace.ready`。当前正式入口只执行以下四条前进边：

| 当前 → 目标 | Agent 必须核对的证据角色 |
| --- | --- |
| literature → candidates | theme、radar、interpretation、map |
| candidates → review | candidates、novelty（含零候选淘汰/不适用依据） |
| review → reporting | review、synthesis（达到约定轮次/人数，保留分歧） |
| reporting → completed | report、validate_report 结果及前置证据一致性 |

阶段充分性的详细判据维护在 `stage-readiness/VERIFIER.md`；候选科学价值、创新性、颠覆潜力和无合格结论充分性维护在 `hypothesis-merit/VERIFIER.md`。各业务 Skill 的产物归本任务各自 `input/output/log`，research-idea 在 `input/` 记录相对来源；自己的 map、候选和综合稿归 `output/`。

## 准备一次验证

Kernel 2.1.0 尚未提供 State visit/attempt 轮换接口，而 State invariant 要求离站身份与当前进入身份一致。因此当前显式兼容模式从首次进入 literature 起沿四条前向边复用同一非空 `run_id/attempt_id`，并按 action 隔离每一阶段的 Gate 幂等键。不要把同一通过结果用于不同转移。需要前进或完成时，当前阶段两个 required Verifier 都要产生绑定结果；对 `literature → candidates` 这类尚未形成候选价值判断的阶段，`hypothesis-merit` 可按契约返回“本次不适用”的 pass，但该结果不能复用于需要完整科学价值认证的阶段。

此模式不支持失败 Gate 后重试、证据变化后换 attempt、回退或在无身份旧现场续跑。出现这些情况时入口在生成新 handoff 前尽早拒绝可识别的身份错配；Kernel 幂等与 State invariant 继续作为最终防线。保留当前 State、错误码和恢复位置，等待 Kernel 原生 visit/attempt 接口，或建立新任务重新核验，不能手工补写事件。

阶段入口会把 action 对应的 source/target 及 Kernel 当前进入身份加入请求。输入文件只需提供以下 `context` 和 `evidence`，不能把示例当作已完成证据：

```json
{
  "context": {
    "rounds": 3,
    "agents": 3,
    "allow_custom_name": false,
    "sources": {"map-main": {"role": "map", "path": "项目内本任务的相对路径"}}
  },
  "evidence": [
    {"ref": "map-main", "source_type": "research-map-synthesis", "summary": "研究线与机会索引", "content_hash": "由当前文件计算的实际 SHA-256"}
  ]
}
```

设置从 manifest 读取，不因示例中的默认数值覆盖用户约束。Agent 必须实际打开源文件，检查非空、角色与成员覆盖、来源深度及科学充分性。文件可用 `shasum -a 256` 取内容标识，不搭建快照系统。证据路径限定授权项目，拒绝 `..`、绝对路径及符号链接逃逸；大体积资料只用有来源的必要摘要。

## Kernel API 实现说明（仅开发排查）

普通运行只使用 `phase_entry.py`，不让 Agent 重组 Kernel 调用。入口通过 `TaskWorkspace.read_meta_state()` 与 `EventLog.projection()` 读取状态及进入身份，通过 `SkillStateDeclaration` 和 `FilesystemVerifierRegistry` 执行本地 required Verifier，再用 `EventLog.record_verification()` 生成 Kernel Gate。多个 required Verifier 必须按同一阶段请求批量记录成一个 Gate；单独记录某一个通过结果不能覆盖全部 required。实现细节以脚本源码和定向测试为准，不在文档维护第二套可复制入口。

第一次调用返回 `awaiting_agent` 是正常状态。实际完成证据审查后，Agent 为每个待处理 handoff 写入绑定结果 JSON；`--submissions` 可指向单个结果对象，也可指向 `{ "submissions": [...] }`。第二次调用的 action、input 与原绑定字段必须保持一致，不能重建 handoff 再给旧判断套上新身份。

结果文件从原 handoff 复制 `pack_id`、`pack_version`、`package_kind`、`component_id`、`component_type`、`contract_hash`、`component_hash`、`plan_hash`、`run_id`、`attempt_id`、`handoff_hash`，再填写：

```json
{
  "protocol": "bensz-contract-component-result-v1",
  "execution_status": "unchecked",
  "verdict": "unchecked",
  "executor": {"type": "agent", "id": "scientific-reviewer", "model": "实际模型名"},
  "facts": {"summary": "尚未完成来源核验", "confidence": 0.0, "uncertainties": ["待核验事项"]},
  "evidence_refs": ["map-main"],
  "findings": []
}
```

此示例省略绑定字段，不能原样提交。实际完成后使用 `completed` 与真实 verdict；有未解决不确定性时使用 `uncertain`。尚未执行、执行报错、超时或跳过时，execution_status 与 verdict 分别使用对应的 `unchecked`、`error`、`timed_out`、`skipped`，不把执行失败写为 completed。同一可信会话也可调用 Kernel 的 `handoff.bind_result(...)` 生成绑定结果。不得以模板 pass 或模型自信替代读取来源，原有独立科研审查仍需执行；`hypothesis-merit` 必须对推荐或无合格结论写出价值、创新性和替代方向理由。

## 推进、回退限制与完成

`phase_entry.py` 的第二次调用会在 Kernel Gate 为 `allow` 后自动使用当前进入身份执行 BSK transition；普通运行不得手工重复。入口同时检查 JSON `status=transitioned` 和目标快照，退出码不能代替结果判断。所有非终态声明原生 `verifier-result-recorded`、`verifier-gate-allow`、`required-verifiers-pass`；没有当前身份的全部 required 结果或非通过 Gate 时不能离开。Kernel 不判断 subject 中的科学含义，Agent 仍负责核对证据与当前 action 对应。

State 图保留历史回退边，但 Kernel 2.1.0 兼容模式没有安全轮换目标 State visit/attempt 的公开接口，正式入口不执行 rework。发现前置证据需返工时，将目标及下游旧判断标为待复核，保留当前 State 与失败原因并停止；不得直接调用 bsk 回退、复用旧 Gate 或手工改写事件。

reporting → completed 前运行 `validate_report.py --report ...` 并检查 `passed` 与 `completion_eligible`，再完成阶段就绪和科学假设价值语义核验。recommended 和有充分淘汰/探索/复核证据的 no_qualified 可以完成；insufficient 即使格式通过也只能交付阶段性评估，保持真实最近阶段。零候选不能省略独立审查，全文受限不能算无需查新。

## 完成证据收敛检查

`validate_report.py` 只检查最终 Markdown 的结构和 frontmatter，不能证明 bsk 状态、Gate、依赖 Skill 和独立审查真实完成。recommended/no_qualified 报告交付前，先在 `research-idea/output/completion-evidence.json` 保存可复核索引，再运行完成收敛检查。

索引只记录相对于本轮 task-root 的路径和脱敏摘要，不复制完整私有 prompt、密钥或论文原文。推荐形状如下；实际路径必须指向非空文件：

```json
{
  "dependencies": {
    "research-topic-extractor": [{"path": "research-topic-extractor/output/theme.json", "status": "complete"}],
    "research-literature-radar": [{"path": "research-literature-radar/output/selection.md", "status": "complete"}],
    "research-literature-interpretation": [{"path": "research-literature-interpretation/output/R1/interpretation.md", "status": "complete"}],
    "research-literature-review": [{"path": "research-literature-review/output/C1/novelty-result.md", "status": "complete"}]
  },
  "review": {
    "rounds": [
      {
        "round": 1,
        "reviewers": [
          {"id": "round1-reviewer-a", "path": "parallel-vibe/output/round1/reviewer-a.md"}
        ],
        "summary_path": "parallel-vibe/output/round1/summary.md"
      }
    ],
    "synthesis_path": "research-idea/output/review-synthesis.md"
  }
}
```

然后执行：

```bash
python "$IDEA_SKILL/scripts/check_completion.py" \
  --project-root . \
  --task-root "$IDEA_TASK" \
  --report "{最终报告路径}"
```

该脚本会从 manifest 读取 `allow_custom_name`，因此用户指定 `docs/ideas/v11.md` 一类文件名时无需再手动猜 `validate_report.py --allow-custom-name`。检查通过只表示完成票据齐备；科学判断仍由已绑定的 Verifier 与独立审查承担。失败时先看 `state.first_control_break`：身份缺失/错配、拒绝 Gate 或回退需求在当前兼容模式停止；仅 handoff 尚未完成且证据未变化时可继续原绑定。依赖产物或审查证据不足同样保留当前阶段，不改写旧事件追认完成。

## 恢复与兼容边界

事件由 bsk 保存到 `{task}/log/events.ndjson`，领域快照位于 `{task}/research-idea/log/meta-state.json`。读取通用日志投影可用 `bsk status "$IDEA_TASK/log/events.ndjson"`；领域阶段通过 Kernel 读取：

```python
import json
import os
from bensz_skill_kernel.workspace import TaskWorkspace
print(json.dumps(TaskWorkspace.open_existing(os.environ["IDEA_TASK"]).read_meta_state("research-idea"), ensure_ascii=False, indent=2))
```

恢复先读取原 manifest、领域快照及 Kernel 投影，核对实际文件。若断在 handoff 后且尚无拒绝 Gate、请求和来源均未变化，可使用原绑定继续同一阶段；内容变化、已有拒绝 Gate 或需要新 attempt 时停止，当前兼容模式不在原任务重试。快照缺失但已有领域转移事件、快照损坏或不完整提交均停止处理，不按默认 ready 重新开始。`bsk rebuild` 只恢复通用投影，不承诺恢复领域 meta-state；不自行写恢复器。

等待、取消使用 `research-idea/log/` 中简短记录说明原因、未完成步骤和恢复条件，并停止推进。恢复由用户任务意图驱动，不能因为历史 Gate 存在就继续已取消工作。completed 无后继；新的研究任务另建工作区。

旧 `idea_runtime.py`、`phase_evidence.py`、Pack 机械脚本与 init/prepare/submit/rework/status/cancel 专用接口已移除；初始化的 `--workspace-dir`、`--run-id`、`--overwrite`、`--with-test-dir`、`--test-dir` 不再提供。旧 manifest、idea.* 事件和报告只读保留，不自动转成新协议，也不重新创建同一逻辑任务根。缺少 State 进入身份或需要新 run/attempt 的旧运行不能由当前兼容入口续作；旧报告仍可单独做格式检查，不能据此认证新运行完成。

Kernel 绑定的是提交的请求/证据标识；新完成证据索引（`schema: research-idea-completion-v2`）还必须保存每项来源的 SHA-256、大小、修改时间及 run/attempt。`check_completion.py` 在最终收敛时重算快照；Gate 后来源变化、跨 attempt 引用或报告替换都会失败，当前兼容模式停止并保留恢复位置。旧索引只读兼容，不能据此认证新 completed。日志和绑定提供可追溯性，不提供科学真实性或恶意本地代码沙箱。

## 按需复用内置组件

不复制内置 Pack。用 `bsk verifier describe ID` 阅读当前契约，再用 `bsk verifier run ID --input request.json`。这些辅助结果不替代本 Skill required 语义结果。

| 内置 ID | 适用范围与限制 |
| --- | --- |
| bensz.artifact.file-existence | subject.path 是否为文件；不检查内容 |
| bensz.artifact.path-scope | subject.paths 与 context.allowed_paths；空路径集合也可能通过，调用前检查非空 |
| bensz.document.markdown-link-integrity | Markdown 引用可定位性；不可观测保留未知，可达不等于支持论点 |
| bensz.evidence.citation-truth-fit | 具体引文和来源片段的语义核验，需要 Agent 实际执行 |
| bensz.evidence.provenance | 仅来源字段完整性，不重算文件哈希、也不证明来源真实 |

内置通用 runtime 状态不表达研究各阶段，不替换本 Skill 五个领域 State；task-completeness 只查 truthy 字段，不作为科研完成判据。

## 开发验证

```bash
PYTHONDONTWRITEBYTECODE=1 python -m pytest tests/research-idea -q \
  -o cache_dir="$IDEA_TASK/research-idea/log/pytest-cache" \
  --basetemp="$IDEA_TASK/research-idea/output/test-run"
```

定向回归直接调用正式阶段入口与必要的 Kernel CLI/API，覆盖带身份初始化、四阶段同身份直线推进、缺失/错配身份、required 缺失、不确定、错绑、复制后的 Pack 发现和报告三种结论。合成 Agent 回传只验证协议，不能当成真实科研质量或完整文献调查验收。
