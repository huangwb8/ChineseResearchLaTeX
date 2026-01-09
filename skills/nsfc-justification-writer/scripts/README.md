# nsfc-justification-writer scripts

这些脚本提供“硬编码确定性能力”（诊断/术语/字数/评审建议/可视化报告 + 安全写入 + 版本回滚），用于配合 AI 写作流程：
- AI 负责生成/重写文字
- 脚本负责**定位段落**、**写入白名单文件**、**备份与可复现诊断**

## 快速开始

```bash
python skills/nsfc-justification-writer/scripts/run.py diagnose --project-root projects/NSFC_Young
python skills/nsfc-justification-writer/scripts/run.py wordcount --project-root projects/NSFC_Young
python skills/nsfc-justification-writer/scripts/run.py refs --project-root projects/NSFC_Young
python skills/nsfc-justification-writer/scripts/run.py terms --project-root projects/NSFC_Young
python skills/nsfc-justification-writer/scripts/run.py coach --project-root projects/NSFC_Young --stage auto
python skills/nsfc-justification-writer/scripts/run.py review --project-root projects/NSFC_Young
```

## 配置覆盖与学科预设（可选）

全局参数需要放在子命令前：

```bash
python skills/nsfc-justification-writer/scripts/run.py --preset medical diagnose --project-root projects/NSFC_Young
python skills/nsfc-justification-writer/scripts/run.py --preset engineering terms --project-root projects/NSFC_Young
python skills/nsfc-justification-writer/scripts/run.py --override /path/to/override.yaml coach --project-root projects/NSFC_Young --stage auto
python skills/nsfc-justification-writer/scripts/run.py --no-user-override diagnose --project-root projects/NSFC_Young
```

说明：
- `--preset <name>` 会加载 `skills/nsfc-justification-writer/config/presets/<name>.yaml`
- 默认会尝试加载 `~/.config/nsfc-justification-writer/override.yaml`（如存在）；用 `--no-user-override` 关闭

## 信息表生成（推荐）

生成模板（用于你手工填写）：

```bash
python skills/nsfc-justification-writer/scripts/run.py init --out /path/to/info_form.md
```

交互式填写并生成：

```bash
python skills/nsfc-justification-writer/scripts/run.py init --interactive --out /path/to/info_form_filled.md
```

## 渐进式写作引导（主推）

```bash
python skills/nsfc-justification-writer/scripts/run.py coach --project-root projects/NSFC_Young --stage auto --topic "你的课题一句话"
```

说明：
- 输出会告诉你“本轮只做三件事”，并给出“可复制提示词”（用于生成某个小标题正文）
- 你每轮只需要改一个 `\subsubsection` 的正文，然后用 `apply-section` 写入

## 安全写入：替换指定小标题正文

将某个 `\\subsubsection{...}` 的正文替换为新内容（不改动小标题本身）：

```bash
python skills/nsfc-justification-writer/scripts/run.py apply-section \
  --project-root projects/NSFC_Young \
  --title "国内外研究现状" \
  --body-file /path/to/new_body.txt
```

说明：
- 备份默认写入 `skills/nsfc-justification-writer/runs/`（不污染标书项目目录）
- 仅允许写入 `extraTex/1.1.立项依据.tex`（由 `config.yaml` 的 guardrails 控制）
- 默认严格：若新正文中出现 `\cite{...}` 但 `.bib` 不存在对应 key，将拒绝写入（防止幻觉引用）
- 标题未命中时：可加 `--suggest-alias` 输出当前文档所有 `\subsubsection` 标题，便于修正 `--title`
- 如需允许“标题不完全一致也能匹配”：在 `config.yaml` 里设置 `structure.strict_title_match: false`（会启用模糊匹配；AI 可用时会先做语义匹配）
- 若你使用了 `--allow-missing-citations` 放宽引用约束，建议同时加 `--strict-quality` 启用“新正文质量闸门”（命中绝对化表述/危险命令将拒绝写入）

## 运行产物（runs/cache）

- `skills/nsfc-justification-writer/runs/`：每次写入/回滚的备份、diff、报告与日志（可随时删除某些旧 run）
- `skills/nsfc-justification-writer/.cache/ai/`：Tier2/术语一致性等可选 AI 计算缓存（可用 `--fresh` 忽略缓存）

清理示例：

```bash
rm -rf skills/nsfc-justification-writer/runs/*
rm -rf skills/nsfc-justification-writer/.cache/*
```

## HTML 可视化诊断报告

```bash
python skills/nsfc-justification-writer/scripts/run.py diagnose --project-root projects/NSFC_Young --html-report auto
```

## 版本 diff / 回滚

列出 runs：

```bash
python skills/nsfc-justification-writer/scripts/run.py list-runs
```

查看某次写入的备份与当前文件差异：

```bash
python skills/nsfc-justification-writer/scripts/run.py diff --project-root projects/NSFC_Young --run-id <run_id>
```

从某次备份回滚（需要显式确认）：

```bash
python skills/nsfc-justification-writer/scripts/run.py rollback --project-root projects/NSFC_Young --run-id <run_id> --yes
```
