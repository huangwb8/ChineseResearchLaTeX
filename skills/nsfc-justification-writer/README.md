# nsfc-justification-writer

用于 NSFC 2026 新模板正文 `（一）立项依据` 的写作/重构：把“价值与必要性、现状不足、科学问题/假说、切入点与贡献”写成一段可直接落到 LaTeX 模板的正文，并保持模板结构不被破坏。

> 主推“渐进式写作引导”（coach），配合“诊断→（分步写作）→安全写入→验收”形成闭环。

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

## 配置（可选）

全局配置加载顺序（后者覆盖前者）：
1. `skills/nsfc-justification-writer/config.yaml`
2. `skills/nsfc-justification-writer/config/presets/<preset>.yaml`（可选）
3. `~/.config/nsfc-justification-writer/override.yaml`（可选，可用 `--no-user-override` 关闭）
4. `--override /path/to/override.yaml`（可选，优先级最高）

示例：

```bash
python skills/nsfc-justification-writer/scripts/run.py --preset medical diagnose --project-root projects/NSFC_Young
python skills/nsfc-justification-writer/scripts/run.py --override /path/to/override.yaml terms --project-root projects/NSFC_Young
```

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

## FAQ

- **Q：为什么 `apply-section` 会拒绝写入？**  
  A：默认严格：若新正文里出现 `\\cite{...}` 但项目 `references/*.bib` 找不到对应 key，会拒绝写入以避免“幻觉引用”。先用 `refs` 生成提示词交给 `nsfc-bib-manager` 补齐后再写入。
- **Q：我想按学科调整术语 alias_groups 怎么做？**  
  A：先试 `--preset medical/engineering`，或写一个 `override.yaml` 覆盖 `terminology.alias_groups`。
- **Q：行号怎么复制？**  
  A：HTML 报告里点击行号会复制 `Lxx`；`Shift+点击` 复制带锚点链接（便于讨论定位）。

## 更多文档

- `skills/nsfc-justification-writer/docs/tutorial.md`
- `skills/nsfc-justification-writer/docs/architecture.md`

版本回滚：

```bash
python skills/nsfc-justification-writer/scripts/run.py list-runs
python skills/nsfc-justification-writer/scripts/run.py diff --project-root projects/NSFC_Young --run-id <某次apply/rollback的run_id>
python skills/nsfc-justification-writer/scripts/run.py rollback --project-root projects/NSFC_Young --run-id <run_id> --yes
```
