# nsfc-justification-writer

用于 NSFC 2026 新模板正文 `（一）立项依据` 的写作/重构：把“价值与必要性、现状不足、科学问题/假说、切入点与贡献”写成一段可直接落到 LaTeX 模板的正文，并保持模板结构不被破坏。

> v0.3.0 起：主推“渐进式写作引导”（coach），配合“诊断→（分步写作）→安全写入→验收”形成闭环。

## 推荐用法（Prompt 模板）

### 1）主推：渐进式写作引导（骨架→段落→修订→润色→验收）

第一步先跑引导（不需要你一步到位写完）：

```bash
python skills/nsfc-justification-writer/scripts/run.py coach --project-root projects/NSFC_Young --stage auto --topic "你的课题一句话"
```

按 coach 输出的“下一步可直接复制的写作提示词”去生成某个小标题正文后，用 `apply-section` 安全写入；再重复 coach→apply 的迭代，直到 `diagnose` 通过。

### 2）从零生成（一次性写完）

```
请使用 nsfc-justification-writer：
目标项目：projects/NSFC_Young
主题：<一句话题目/方向>
信息表：<按 references/info_form.md 提供>
输出：写入 extraTex/1.1.立项依据.tex
```

### 3）基于已有草稿重构

```
请使用 nsfc-justification-writer 重构（强调逻辑闭环与可核验性），不要改 main.tex：
目标项目：<你的项目路径>
现有草稿：<粘贴或指向 extraTex/1.1.立项依据.tex>
补充信息：<按 references/info_form.md 缺啥补啥>
```

## 输出文件

- `extraTex/1.1.立项依据.tex`

## 配套脚本（可选但推荐）

```bash
python skills/nsfc-justification-writer/scripts/run.py diagnose --project-root projects/NSFC_Young
python skills/nsfc-justification-writer/scripts/run.py wordcount --project-root projects/NSFC_Young
python skills/nsfc-justification-writer/scripts/run.py refs --project-root projects/NSFC_Young
python skills/nsfc-justification-writer/scripts/run.py terms --project-root projects/NSFC_Young
python skills/nsfc-justification-writer/scripts/run.py review --project-root projects/NSFC_Young
python skills/nsfc-justification-writer/scripts/run.py coach --project-root projects/NSFC_Young --stage auto
```

安全写入（替换指定 `\\subsubsection{...}` 的正文）：

```bash
python skills/nsfc-justification-writer/scripts/run.py apply-section \\
  --project-root projects/NSFC_Young \\
  --title "国内外研究现状" \\
  --body-file /path/to/new_body.txt
```

可视化诊断报告（HTML）：

```bash
python skills/nsfc-justification-writer/scripts/run.py diagnose --project-root projects/NSFC_Young --html-report auto
```

版本回滚：

```bash
python skills/nsfc-justification-writer/scripts/run.py list-runs
python skills/nsfc-justification-writer/scripts/run.py diff --project-root projects/NSFC_Young --run-id <某次apply/rollback的run_id>
python skills/nsfc-justification-writer/scripts/run.py rollback --project-root projects/NSFC_Young --run-id <run_id> --yes
```
