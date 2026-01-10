# nsfc-justification-writer

用于科研申请书"立项依据"章节的写作/重构：把"价值与必要性、现状不足、科学问题/假说、切入点与贡献"写成一段可直接落到 LaTeX 模板的正文，并保持模板结构不被破坏。适用于 NSFC 及各类科研基金申请书的立项依据写作场景。

> **⚠️ AI 模型要求**：本 skill 涉及复杂的科学问题识别、假说可证伪性判断、理论创新导向写作等高阶任务，**建议使用 GPT-5.2 High 或同级别的高智能 AI** 以获得最佳效果。较低级别的模型可能在理论深度、逻辑严谨性、表达准确性等方面表现不足。

> 主推"渐进式写作引导"（coach），配合"诊断→（分步写作）→安全写入→验收"形成闭环。
> AI 能力默认来自运行环境的 Claude Code / Codex 原生智能，无需额外配置外部 API Key；不可用时自动回退到硬编码能力。

能力亮点（本版新增/强化）：
- 默认不强制标题精确匹配，改为检查“价值/现状/科学问题/切入点”内容维度覆盖（AI + 兜底启发式）
- AI 语义识别“吹牛式表述”（绝对化/填补空白/无依据夸大/自我定性）并给出改写建议，高风险词仅提示不做机械阻断
- 目标字数优先从用户意图/信息表的“字数/范围/±容差”解析，再用配置兜底
- `coach --stage auto` 支持 AI 阶段判断（skeleton/draft/revise/polish/final），AI 不可用则回退到硬编码阈值
- 写作导向可配置：`style.mode=theoretical|mixed|engineering`（默认 `theoretical`）

## 推荐用法（Prompt 模板）

### 开发者建议：多轮对话优化立项依据

使用 Claude Code / Codex CLI 时，建议先让 skill 在本轮对话全局生效，便于多轮迭代优化：

```
接下来，我要使用 nsfc-justification-writer 这个skill 优化立项依据。仅使用skill，不要修改skill的任何文件。保持这个skill在本轮对话全局生效。先做好准备，不要开始干活。你准备好了吗？
```

然后在同一轮对话中持续使用 coach→diagnose→apply 的闭环，直到满意为止。

---

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
python skills/nsfc-justification-writer/scripts/run.py check-ai
```

安全写入（替换指定 `\\subsubsection{...}` 的正文）：

```bash
python skills/nsfc-justification-writer/scripts/run.py apply-section \\
  --project-root projects/NSFC_Young \\
  --title "国内外研究现状" \\
  --body-file /path/to/new_body.txt
```

标题未命中时输出候选（便于修正 `--title`）：

```bash
python skills/nsfc-justification-writer/scripts/run.py apply-section \\
  --project-root projects/NSFC_Young \\
  --title "现状" \\
  --body-file /path/to/new_body.txt \\
  --suggest-alias
```

可视化诊断报告（HTML）：

```bash
python skills/nsfc-justification-writer/scripts/run.py diagnose --project-root projects/NSFC_Young --html-report auto
```

## FAQ

- **Q：AI 能力为什么有时“不生效”？**  
  A：本仓库脚本默认不假设可直接调用宿主 AI；需要运行环境注入 responder 才会启用 AI（不可用会自动回退到硬编码能力）。可先运行 `python skills/nsfc-justification-writer/scripts/run.py check-ai` 查看当前是否处于降级模式。
- **Q：为什么 `apply-section` 会拒绝写入？**  
  A：默认严格：若新正文里出现 `\\cite{...}` 但项目 `references/*.bib` 找不到对应 key，会拒绝写入以避免“幻觉引用”。先用 `refs` 生成提示词交给 `nsfc-bib-manager` 补齐后再写入。
  如你使用 `--allow-missing-citations` 放宽该检查，建议同时加 `--strict-quality` 启用“新正文质量闸门”（命中绝对化表述/危险命令则拒绝写入）。
- **Q：我想按学科调整术语一致性检查怎么做？**  
  A：先试 `--preset medical/engineering`（已提供更丰富的三维矩阵示例），或写一个 `override.yaml` 覆盖 `terminology.dimensions`（推荐）：

  ```yaml
  terminology:
    dimensions:
      研究对象:
        研究对象: ["患者", "受试者", "样本"]
      指标:
        AUC: ["AUC", "ROC-AUC"]
      术语:
        深度学习: ["深度学习", "DL"]
  ```

  如需临时关闭该检查，可设置 `terminology.dimensions: {}`（或兼容的 `terminology.alias_groups: {}`）。如需叠加 AI 语义检查，可设置 `terminology.mode: auto/ai`（AI 不可用时会自动回退到矩阵规则）。
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
