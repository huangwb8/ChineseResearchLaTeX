# nsfc-research-content-writer

[中文](README.md) · [English](README_EN.md) · [执行规范](SKILL.md) · [配置](config.yaml)

为 NSFC 研究内容、特色与创新、年度研究计划提供新写、重构、审查和保真润色。先理解项目材料，再按授权修改；单章任务也会只读检查关联影响。

## 快速开始

在支持 Agent Skill 的宿主中指向本目录并提出任务：

```text
使用 nsfc-research-content-writer。
project_root: projects/NSFC_Young
只润色特色与创新，保留研究设计和其他章节。
output_mode: preview
从现有正文、立项依据和研究基础提取信息，缺口按影响处理。
```

完整新写或重构时，明确授权三章并提供已有研究材料；审查只输出诊断，不创建或改动正文。无需先填写固定信息表。相邻的 `nsfc-justification-writer` 负责立项依据，`nsfc-research-foundation-writer` 负责研究基础，本 Skill 将两者作为只读上下文。

## 输入与输出

`project_root` 必需；`output_mode` 默认 `apply`，`preview` 只展示草稿及可用时的 diff。两种模式含义保持不变。默认路径及数值由 [config.yaml](config.yaml) 管理：

| 角色 | 正文落点 |
| --- | --- |
| `research_content_tex` | `extraTex/2.1.研究内容.tex` |
| `innovation_tex` | `extraTex/2.2.特色与创新.tex` |
| `yearly_plan_tex` | `extraTex/2.3.年度研究计划.tex` |

默认保留 **3–4 个子目标、三年计划、研究内容 12–15 页（含图表）**；创新点 1–3 条。原有纯文字 12000–15000 字建议只作辅助，不由字数换算页数。未编译会注明“尚未核验实际页数”。内部规划编号不写进最终正文。

交付包括请求的正文和四类简短说明：研究设计与结构调整、学术表达改进、科学歧义与证据缺口、作者决策事项。写入另附实际 diff、备份及恢复方法。技术路线图建议放研究内容开头，本 Skill 不生成图表。

## 安全写入与预览

脚本需 **Python 3.11+、PyYAML**；示例用 `python3.11`，也可替换为满足版本的解释器。先由宿主 AI 写出完整文件提案，保存于本任务已声明的 `.bensz-api/task-*`；模板中必需目标必须已存在。

将以下 JSON 保存为任务目录的 `nsfc-research-content-writer/input/proposals.json`，提案路径也相对任务根目录。只提交本次授权角色：

```json
{"proposals": {"innovation_tex": "nsfc-research-content-writer/input/innovation.tex"}}
```

从任意工作目录调用安装副本或仓库脚本。`/path/to/skill` 替换为真实 Skill 目录；清单和提案不得越出任务目录：

```bash
python3.11 /path/to/skill/scripts/run.py revise \
  --project-root /path/to/project --task-root /path/to/.bensz-api/task-YYYYMMDD-HHMM-topic \
  --proposal-manifest nsfc-research-content-writer/input/proposals.json \
  --role innovation_tex --output-mode preview
```

`preview` 不改正文、不建备份。已授权写入时改为 `--output-mode apply`；省略模式按配置默认写入。全套修改需三次 `--role` 且清单集合完全相同。默认保留标题、层级、标签和资源命令；只有明确授权结构修改才用 `--allow-structure-change`，目标集合仍受白名单限制。禁止改动 `main.tex`、`extraTex/@config.tex`、任何 `.cls/.sty`。

所有目标先检查；任一失败则全不写。所有变化原稿先备份，随后检查并发修改，再逐文件安全替换；无差异不替换。可捕获失败会尝试恢复已替换部分，进程中断可能留下部分写入，不能保证多文件整体原子性。最后检查后的外部竞态也不由此工具完全消除。

## 查看差异与恢复

写入结果返回 `backup_dir`，其中有前后版本与 `record.json`，不保存宿主绝对路径。将 `<id>` 替换为返回值：

```bash
python3.11 /path/to/skill/scripts/run.py diff --project-root /path/to/project \
  --task-root /path/to/.bensz-api/task-YYYYMMDD-HHMM-topic \
  --backup-dir nsfc-research-content-writer/output/revision-<id>
python3.11 /path/to/skill/scripts/run.py restore --project-root /path/to/project \
  --task-root /path/to/.bensz-api/task-YYYYMMDD-HHMM-topic \
  --backup-dir nsfc-research-content-writer/output/revision-<id>
```

恢复前保护当前版本。若当前内容既非原稿也非本次提案，或备份损坏/目标不匹配，整个恢复拒绝覆盖；先解决冲突。中断后可恢复原稿与提案混合的集合。恢复产生的新 revision 也可用于撤销恢复。

## 自检与兼容

```bash
python3.11 /path/to/skill/scripts/validate_skill.py
python3.11 /path/to/skill/scripts/check_project_outputs.py --project-root /path/to/project
python3.11 /path/to/skill/scripts/run_checks.py --project-root /path/to/project --fail-on-risk-phrases
python3.11 /path/to/skill/scripts/create_test_session.py \
  --task-root /path/to/.bensz-api/task-YYYYMMDD-HHMM-topic --kind a --id v202611011300 --create-plan
```

旧检查入口及 `--no-content-check`、`--no-risk-scan`、`--fail-on-risk-phrases` 保留；不再要求正文出现 S 编号，`checks.subgoal_markers_min` 已停用并提示。词表默认提示，显式严格模式才拒绝，命中本身不说明主张错误。引用 key 存在不证明真实性或支持性，脚本不判断三章科学一致性。

`create_test_session.py` 现在必须指定已声明的 `--task-root`；旧计划参数保留兼容提示，计划/报告写在该任务内，正式维护计划放仓库 `docs/plans/`。不再创建 Skill 内 `plans/`、`tests/`。运行产物不进入源码目录；本次未增加 State、Verifier 或 Kernel 依赖。

## 常见问题

**资料缺失是否全部停工？** 不影响保真修改的缺口登记后继续；涉及可行性或项目承诺的段落保留待决，不补造样本量、队列、伦理时间或效果。

**为何缺失 bibkey 会阻止写入？** 提案不能引入无法解析的引用；保留必要引用和待核验说明，修正文献条目后再提交，不为通过检查删主张。

**是否必须先确认每一次预览？** 预览可供审阅；已有写入授权即可应用，不重复申请许可。单章授权不自动扩成三章授权。

## 更多资料

[研究设计与分节写法](references/section_writing.md) · [质量控制](references/quality_control.md) · [回归案例](references/regression_examples.md) · [篇幅指导](references/page_budget.md) · [变更记录](CHANGELOG.md)
