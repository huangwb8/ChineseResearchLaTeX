# 验证器与状态恢复操作

## 环境与兼容性

使用 Python 3.11+（推荐 3.12），`bensz-skill-kernel` 版本必须与 `config.yaml.runtime.kernel.version` 精确一致。Kernel 不随本 Skill 内嵌；请在隔离环境安装匹配版本，例如：

```bash
python3.12 -m venv .bensz-api/research-idea-env
.bensz-api/research-idea-env/bin/python -m pip install bensz-skill-kernel==1.0.3
```

版本值应随 config 的消费约束更新。当前宿主串行锁使用 POSIX `flock`，支持 macOS/Linux；Windows 请在 WSL 运行。旧 Kernel 缺少 ContractPackExecutor 时明确失败，不静默跳过验证。

本 Skill 提供的实际执行入口为 `scripts/idea_runtime.py`，它加载 Skill 本地注册表并调用 Kernel `run_contract`。普通 `bsk verifier run` 不自动发现本 Skill Pack；普通 `bsk state transition` 也不执行本 Skill 的阶段验收。

## 初始化与恢复

先确定并公开唯一任务根目录，然后显式传 `--task-root` 复用。以下命令在项目根运行；`python` 指匹配依赖的隔离环境解释器，`{skill}` 是实际 Skill 根路径，`{task}` 是项目内 `.bensz-api/task-*` 相对路径。

```bash
python {skill}/scripts/init_workspace.py --cwd . --input-label topic --task-root {task}
python {skill}/scripts/idea_runtime.py --task-root {task} status
```

初始化会创建 manifest、业务目录及 `research-idea/log/events.ndjson`；起始阶段为 literature。用户指定审查轮次/人数时初始化增加 `--rounds N --agents N`；自定义最终文件名增加 `--allow-custom-name`。这些设置在 run 内固定。普通用户不可用 `--skip-dependency-check`，该选项只供开发测试，而且不能绕过 Kernel 检查。

若已有本协议的事件日志，直接 `status` 恢复，不重新初始化。只有旧 manifest 的任务不自动视为任何阶段已通过：可用 `idea_runtime.py ... init` 在相同任务根下开始新控制记录，再逐阶段验证已有证据。旧 `--workspace-dir` 时间戳嵌套布局不再写入，旧文件不删除、不自动迁移；新任务采用 `--task-root`。

单独使用 `idea_runtime.py ... init` 只初始化控制目录，不负责发现研究依赖或生成报告 manifest；常规业务应使用 `init_workspace.py`。

## 阶段与证据

| 当前阶段 | 下一阶段 | 必需角色 |
| --- | --- | --- |
| literature | candidates | theme、radar、interpretation、map |
| candidates | review | candidates、novelty |
| review | reporting | review、synthesis |
| reporting | completed | report |

角色可有多个条目。例如每篇解读、每个候选的查新各有一条；也可以使用包含全部成员及来源锚点的结构化汇总。脚本检查角色存在，Agent 必须检查是否完整覆盖成员及真实来源。

证据列表 JSON 保存到 `{task}/research-idea/input/`。每条示例：

```json
{
  "ref": "map-main",
  "role": "map",
  "path": ".bensz-api/task-YYYYMMDD-HHMM-topic/research-idea/output/research-map.md",
  "source_type": "research-map-synthesis",
  "summary": "基于已解读文献的研究线、转折与知识缺口"
}
```

`path` 相对项目根，可引用本任务其他 Skill 的结果；拒绝绝对路径、`..` 和符号链接。文件限大小，证据数量限额以 config 为准；大型资料使用有来源锚点的必要摘要。宿主实算 `content_hash`，不要手写通过状态。审查条目另带整数 `round` 和脱敏的 `reviewer` 标识，各轮人数与初始化参数一致；同一内容复制成多文件不能充当不同审查。

## 发起验证和回传

```bash
python {skill}/scripts/idea_runtime.py --task-root {task} prepare \
  --target candidates --evidence {task}/research-idea/input/evidence.json
```

宿主冻结证据清单，实际执行脚本组件并返回待处理 handoff。没有语义结果时 Gate 不允许前进，退出码为 2（这是预期的待办状态）。每次 prepare 使用新的 attempt，旧 attempt 的回传不能提交。

主 Agent 读取 [VERIFIER.md](verifiers/stage-readiness/VERIFIER.md)、handoff 引用的源文件、当前阶段和必要的前置检查点，实际评估科学充分性。回传 JSON 必须从 handoff **逐字复制**以下绑定字段：

`pack_id`、`pack_version`、`package_kind`、`component_id`、`component_type`、`component_hash`、`contract_hash`、`plan_hash`、`run_id`、`attempt_id`、`handoff_hash`。

再添加实际判断（下面是未完成模板，不能用它放行）：

```json
{
  "protocol": "bensz-contract-component-result-v1",
  "execution_status": "unchecked",
  "verdict": "unchecked",
  "executor": {"type": "agent", "id": "scientific-reviewer", "model": "实际模型名称"},
  "evidence_refs": ["map-main"],
  "facts": {
    "summary": "尚未完成源证据核验",
    "confidence": 0.0,
    "uncertainties": ["待核验事项"]
  },
  "findings": []
}
```

完成审查后按实际结果填写 completed 与 pass/fail/uncertain，不能把模型自信当作通过依据。有未解决不确定性时不能 pass。保留非通过原因和证据，必要时补资料或请人类复核。

```bash
python {skill}/scripts/idea_runtime.py --task-root {task} submit \
  --result {task}/research-idea/input/review-result.json
```

宿主再次实算证据哈希、校验绑定，并由 Kernel 重新计算 Gate。只有两个 required 组件均完成且 pass 才记录前向转移。结果为 fail/uncertain/unchecked/error/timed_out/skipped 时保持原阶段。退出码：0 为操作成功或允许；2 为 Gate 未放行；1 为输入/绑定/环境错误。

## 回退、取消与重放

发现 map 变化、候选实质改写需重新查新、审查发现前置不足时，使用图中回退边。先保存一份原因与来源证据文件，用 `role=rework` 条目引用：

```bash
python {skill}/scripts/idea_runtime.py --task-root {task} rework \
  --target candidates --evidence {task}/research-idea/input/rework-evidence.json
python {skill}/scripts/idea_runtime.py --task-root {task} cancel
```

rework 只向前置阶段退回，不能绕过前向 Gate；删除目标及下游检查点的有效性，不删除历史事件或文件。重新前进使用新 attempt。cancel 终止当前 run，保持最后业务阶段可见，不冒充完成。

事件日志是权威来源，status 每次通过 Kernel 哈希链校验并重放领域事件，不需要人工维护第二份 state.json。成功转移引用相同 run/attempt 的 Kernel Gate，断在 Gate 与转移之间时可重交同一绑定结果；内容变化须新 attempt。已通过的上游证据变化会阻止继续推进，须回退到对应阶段。Skill 脚本、配置或 Pack 变化会阻止旧 run 继续执行，不静默改写历史。

## 验证边界

报告原有 `validate_report.py --report ... [--allow-custom-name]` CLI 保留，只检查结构，不替代状态流完成。Pack 复用其函数，避免规则双写，并以项目根限定交付路径检查。

定向测试：

```bash
PYTHONDONTWRITEBYTECODE=1 python -m pytest tests/research-idea -q \
  -o cache_dir={task}/research-idea/log/pytest-cache \
  --basetemp={task}/research-idea/output/test-run
```

测试含合成 Agent 回传，只证明协议与失败边界；实际科研任务仍须执行文献调查、Premium 查新和独立审查。可信宿主和本地文件权限是运行前提，目录隔离与哈希链不构成恶意代码沙箱，也不证明执行者身份经过外部认证。

## 业务结论与完成边界

`report_contract: research-idea-report-v2` 的 recommended 和 no_qualified 都可在证据充分、约定探索与独立审查完成后通过原 reporting → completed 路径。recommended 至少一个候选且所有保留项完成 Premium；no_qualified 的 novelty 证据角色仍必需，记录淘汰依据与查新完成或不适用的具体理由。无需查新仅用于价值筛选已经足以淘汰的事项，缺少近邻全文或核验不能算不适用。

三轮分别核验价值、解释与辨别能力、重新选择与迁移；人数和轮数不自动改变。零候选仍执行约定轮次，对淘汰与重新开启条件独立复核。原图、命令、角色需求和证据哈希/绑定机制保持不变，契约版本在索引中更新。

insufficient 报告可以结构通过并交付，但 `completion_eligible: false` 会阻止完成，保留真实最近阶段；不要为了交付阶段性文件推进状态。它说明缺口和恢复位置，不证明新颖性。

旧标题报告仍可读取，CLI 返回 legacy 和完成不可用警告，不改写原文件。旧运行因资产哈希变化不能由新版本续写；在新任务重建需核验的证据，禁止改旧事件或把新结论追认给旧结果。结构检查不验证引用推理、声明的 Premium 执行或科学价值，这些仍由 required scientific-review 按来源审查。
