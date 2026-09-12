# State / Verifier 与 bsk 的协作

## 职责与环境

本 Skill 仅维护五个 [STATE.md](states/index.json)、两个 required 语义 Verifier（[阶段就绪](verifiers/stage-readiness/VERIFIER.md)、[科学假设价值](verifiers/hypothesis-merit/VERIFIER.md)）和领域报告检查。Agent 读取契约、执行研究、核验证据；bsk 负责 Pack 解析、结果绑定、Gate、事件和状态持久化。不要另写 Skill 运行时、锁、检查点或事件重放器。

使用 Python 3.11+ 和满足 `config.yaml.dependencies.kernel` 最低版本的 `bensz-skill-kernel`。在项目已有合适环境中运行，或用 `.bensz-api/.venv` 安装声明的依赖；包名不是 `bsk`。先核对 `python --version`、`python -m pip show bensz-skill-kernel`、`bsk --version` 及 CLI 实际路径属于同一环境。当前文档和回归在 Kernel 1.0.3 验证；后续版本需重跑定向检查，不能仅凭版本更高推断兼容。

最低版本放在 `dependencies.kernel`，因为 Kernel 1.0.3 的 `runtime.kernel.version` 只接受字符串全等，不能表达最低版本范围。`runtime` 只声明 State 与 required Verifier，交给原生加载器。无需增加版本解析代码。

## 初始化与阶段

先公开并固定唯一任务目录。在项目根运行，以下 shell 变量需替换为本轮真实路径；`python` 与 `bsk` 使用同一环境：

```bash
export IDEA_SKILL="$(pwd)/skills/research-idea"
export IDEA_TASK=".bensz-api/task-YYYYMMDD-HHMM-topic"
bsk workspace init . --task-root "$IDEA_TASK"
python "$IDEA_SKILL/scripts/init_workspace.py" --cwd . --task-root "$IDEA_TASK" --input-label topic
bsk state transition "$IDEA_TASK" research-idea bensz.research-ideation.literature --skill-root "$IDEA_SKILL"
```

安装后将 `IDEA_SKILL` 改为实际安装路径。`init_workspace.py` 只生成 `research-idea/input/manifest.json`（研究参数和正式报告路径）及 `output/candidate-schema.json`（空候选池与独立示例）；不生成状态、事件或科研结论。用户指定人数/轮次时增加 `--agents N --rounds N`，自定义文件名时增加 `--allow-custom-name`。`--skip-dependency-check` 仅用于开发测试。

State 的初始入口复用内置 `bensz.workspace.ready`。以下四条前进边及各状态声明的回退边由 bsk 解析：

| 当前 → 目标 | Agent 必须核对的证据角色 |
| --- | --- |
| literature → candidates | theme、radar、interpretation、map |
| candidates → review | candidates、novelty（含零候选淘汰/不适用依据） |
| review → reporting | review、synthesis（达到约定轮次/人数，保留分歧） |
| reporting → completed | report、validate_report 结果及前置证据一致性 |

阶段充分性的详细判据维护在 `stage-readiness/VERIFIER.md`；候选科学价值、创新性、颠覆潜力和无合格结论充分性维护在 `hypothesis-merit/VERIFIER.md`。各业务 Skill 的产物归本任务各自 `input/output/log`，research-idea 在 `input/` 记录相对来源；自己的 map、候选和综合稿归 `output/`。

## 准备一次验证

每次检查创建新的 `attempt_id`，同一个研究运行保持 `run_id`；重试、返工、证据变化都用新 attempt。不要把同一通过结果用于不同转移。需要前进或完成时，当前 attempt 下两个 required Verifier 都要产生绑定结果；对 `literature → candidates` 这类尚未形成候选价值判断的阶段，`hypothesis-merit` 可按契约返回“本次不适用”的 pass，但该结果不能复用于需要完整科学价值认证的阶段。

将 JSON 请求写入本 Skill 的 `input/`，设置 `IDEA_REQUEST` 指向该文件。下面展示形状，不能直接作为已完成证据使用；完整请求须覆盖本阶段所有角色和真实来源：

```json
{
  "run_id": "idea-run-1",
  "attempt_id": "literature-1",
  "subject": {
    "operation": "advance",
    "source": "bensz.research-ideation.literature",
    "target": "bensz.research-ideation.candidates"
  },
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

## 直接调用 Kernel 的本地 Pack API

Kernel 1.0.3 的 `bsk verifier run` 仅发现内置 Verifier，不能运行本 Skill 的本地 Pack。以下是宿主可直接执行的 API 用法，不需要保存为新 CLI 或常驻脚本。先设 `IDEA_REQUEST`；第一次不要设置 `IDEA_SUBMISSION`，读取输出的 handoff 绑定字段，并直接阅读本 Skill VERIFIER.md。handoff 只是待办。多个 required Verifier 必须在同一 run/attempt 下批量记录成一个 Gate；单独记录某一个通过结果不能覆盖全部 required。

```python
import json
import os
from pathlib import Path
from bensz_skill_kernel.states import SkillStateDeclaration
from bensz_skill_kernel.verifiers import FilesystemVerifierRegistry
from bensz_skill_kernel.workspace import TaskWorkspace
from bensz_skill_kernel.runtime import EventLog

skill = Path(os.environ["IDEA_SKILL"])
workspace = TaskWorkspace.open_existing(os.environ["IDEA_TASK"])
request = json.loads(Path(os.environ["IDEA_REQUEST"]).read_text())
declaration = SkillStateDeclaration.from_skill_root(skill)
requirements = declaration.verifier_requirements()
registry = FilesystemVerifierRegistry(skill / "references/verifiers")
submission_path = os.environ.get("IDEA_SUBMISSION")
loaded_submissions = json.loads(Path(submission_path).read_text()) if submission_path else []
if isinstance(loaded_submissions, dict):
    loaded_submissions = [loaded_submissions]
submissions = loaded_submissions if isinstance(loaded_submissions, list) else []
executions = []
for requirement in requirements:
    pack_submissions = [
        item for item in submissions
        if isinstance(item, dict) and item.get("pack_id") == requirement["id"]
    ]
    executions.append(registry.run_contract(
        requirement["id"], request, version=requirement["version"],
        run_id=request["run_id"], attempt_id=request["attempt_id"],
        submissions=pack_submissions,
    ))
_, gate = EventLog(workspace.events).record_verification(
    [execution.to_event_payload() for execution in executions],
    {"decision": "wait"},
    run_id=request["run_id"], attempt_id=request["attempt_id"],
    requirements=requirements,
)
print(json.dumps({
    "gate": gate.payload,
    "handoffs": [
        handoff.to_audit_dict()
        for execution in executions
        for handoff in execution.report.handoffs
    ],
}, ensure_ascii=False, indent=2))
```

第一次输出 Gate 未放行是正常状态。输出保存在 `research-idea/log/`，不保存包含指令正文的完整 handoff。实际完成证据审查后，Agent 为每个待处理 handoff 写入绑定结果 JSON；`IDEA_SUBMISSION` 可指向单个结果对象，也可指向结果对象数组。再次执行同一段 API 调用时，请求与原绑定字段必须保持一致；不能重建 handoff 再给旧判断套上新身份。下一次 attempt 先清除该变量。

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

此片段省略绑定字段，不能原样提交。实际完成后使用 `completed` 与真实 verdict；有未解决不确定性时使用 `uncertain`。尚未执行、执行报错、超时或跳过时，execution_status 与 verdict 分别使用对应的 `unchecked`、`error`、`timed_out`、`skipped`，不把执行失败写为 completed。同一可信会话也可调用 Kernel 的 `handoff.bind_result(...)` 生成绑定结果。不得以模板 pass 或模型自信替代读取来源，原有独立科研审查仍需执行；`hypothesis-merit` 必须对推荐或无合格结论写出价值、创新性和替代方向理由。

## 推进、回退与完成

确认 Kernel 输出 Gate 为 `allow`，再核对最新证据、当前 source、目标 target 与请求完全一致，用相同 run/attempt 执行：

```bash
bsk state transition "$IDEA_TASK" research-idea bensz.research-ideation.candidates \
  --skill-root "$IDEA_SKILL" --run-id idea-run-1 --attempt-id literature-1
```

**必须检查输出 JSON 的 `status` 为 `transitioned`。** Kernel 1.0.3 的图边/Gate 拒绝可能仍退出 0，退出码不能代替结果判断。所有非终态声明原生 `verifier-result-recorded`、`verifier-gate-allow`、`required-verifiers-pass`；没有当前身份的全部 required 结果或非通过 Gate 时不能离开。Kernel 不判断 subject 中的科学含义，也不自动检查本次结果是否被错误用于另一图边，Agent 负责这项对应关系。

回退时新请求用 `operation: rework` 和图中更早目标，提供返工原因、受影响证据及恢复位置；Verifier 判断返工是否有依据，通过后仍使用上述 bsk 命令转移。rework 的 pass 仅允许回退，不能用于前进。Agent 将目标及下游旧判断标为待复核；此后前进逐阶段重新检查。

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

该脚本会从 manifest 读取 `allow_custom_name`，因此用户指定 `docs/ideas/v11.md` 一类文件名时无需再手动猜 `validate_report.py --allow-custom-name`。检查通过只表示完成票据齐备；科学判断仍由已绑定的 Verifier 与独立审查承担。若失败，按错误恢复到对应阶段：状态或 Gate 缺失时先完成 bsk 转移，依赖产物缺失时回到文献/查新阶段，审查轮次不足时回到 review；不要改写旧事件来追认完成。

## 恢复与兼容边界

事件由 bsk 保存到 `{task}/log/events.ndjson`，领域快照位于 `{task}/research-idea/log/meta-state.json`。读取通用日志投影可用 `bsk status "$IDEA_TASK/log/events.ndjson"`；领域阶段通过 Kernel 读取：

```python
import json
import os
from bensz_skill_kernel.workspace import TaskWorkspace
print(json.dumps(TaskWorkspace.open_existing(os.environ["IDEA_TASK"]).read_meta_state("research-idea"), ensure_ascii=False, indent=2))
```

恢复先读取原 manifest、领域快照及最近验证事件，核对实际文件。若断在 Gate 与转移之间且请求/来源仍一致，可以完成同一转移；内容变化则使用新 attempt。快照缺失但已有领域转移事件、快照损坏或不完整提交均停止处理，不按默认 ready 重新开始。`bsk rebuild` 只恢复通用投影，不承诺恢复领域 meta-state；不自行写恢复器。

等待、取消使用 `research-idea/log/` 中简短记录说明原因、未完成步骤和恢复条件，并停止推进。恢复由用户任务意图驱动，不能因为历史 Gate 存在就继续已取消工作。completed 无后继；新的研究任务另建工作区。

旧 `idea_runtime.py`、`phase_evidence.py`、Pack 机械脚本与 init/prepare/submit/rework/status/cancel 专用接口已移除；初始化的 `--workspace-dir`、`--run-id`、`--overwrite`、`--with-test-dir`、`--test-dir` 不再提供。旧 manifest、idea.* 事件和报告只读保留，不自动转成新协议，也不重新创建同一逻辑任务根。对旧运行的续作在原任务内记录迁移说明、用新的 run 身份重新核验；不要覆写旧文件。旧报告仍可单独做格式检查，不能据此认证新运行完成。

Kernel 绑定的是提交的请求/证据标识；新完成证据索引（`schema: research-idea-completion-v2`）还必须保存每项来源的 SHA-256、大小、修改时间及 run/attempt。`check_completion.py` 在最终收敛时重算快照；Gate 后来源变化、跨 attempt 引用或报告替换都会失败并要求新 attempt。旧索引只读兼容，不能据此认证新 completed。日志和绑定提供可追溯性，不提供科学真实性或恶意本地代码沙箱。

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

定向回归直接调用 Kernel CLI/API，并执行本文 API 示例，覆盖合法/非法转移、required 缺失、不确定、错绑、恢复读取、复制后的 Pack 发现和报告三种结论。合成 Agent 回传只验证协议，不能当成真实科研质量或完整文献调查验收。
