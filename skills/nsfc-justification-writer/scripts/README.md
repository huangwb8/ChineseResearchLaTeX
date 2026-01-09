# nsfc-justification-writer scripts

这些脚本提供“硬编码确定性能力”（结构/引用/字数/术语检查 + 安全写入），用于配合 AI 写作流程：
- AI 负责生成/重写文字
- 脚本负责**定位段落**、**写入白名单文件**、**备份与可复现诊断**

## 快速开始

```bash
python skills/nsfc-justification-writer/scripts/run.py diagnose --project-root projects/NSFC_Young
python skills/nsfc-justification-writer/scripts/run.py wordcount --project-root projects/NSFC_Young
python skills/nsfc-justification-writer/scripts/run.py terms --project-root projects/NSFC_Young
```

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

