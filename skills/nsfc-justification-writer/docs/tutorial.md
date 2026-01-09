# 教程：从 0 到可验收的“立项依据”

目标：在不破坏 NSFC 2026 模板结构的前提下，完成 `extraTex/1.1.立项依据.tex` 的“诊断→分步写作→安全写入→验收”闭环。

## 0）准备

- 确认你的标书项目目录（示例：`projects/NSFC_Young`）
- 确认目标文件存在：`extraTex/1.1.立项依据.tex`
- 推荐先跑一次结构模板：`skills/nsfc-justification-writer/templates/structure_template.tex`

## 1）生成信息表（最小输入）

生成模板（手工填写）：

```bash
python skills/nsfc-justification-writer/scripts/run.py init --out /tmp/info_form.md
```

或交互式填写：

```bash
python skills/nsfc-justification-writer/scripts/run.py init --interactive --out /tmp/info_form_filled.md
```

## 2）先诊断（把坑提前挖出来）

```bash
python skills/nsfc-justification-writer/scripts/run.py diagnose --project-root projects/NSFC_Young
python skills/nsfc-justification-writer/scripts/run.py diagnose --project-root projects/NSFC_Young --html-report auto
```

建议：
- 结构不完整时，先补齐 4 个 `\\subsubsection` 标题骨架，再进入正文写作
- 有引用但缺 bibkey 时，先修引用，再写正文

## 3）用 coach 拆解任务（每轮只改一个小标题）

```bash
python skills/nsfc-justification-writer/scripts/run.py coach \
  --project-root projects/NSFC_Young \
  --stage auto \
  --topic "一句话主题/关键词"
```

你会得到：
- “本轮只做三件事”（把工作量压到可执行）
- “需要你补充的问题”（补齐关键信息）
- “可直接复制的写作提示词”（给 AI 生成某个小标题正文用）

## 4）安全写入：只替换某个 `\\subsubsection` 的正文

把 AI 生成的正文保存为文件（例如 `/tmp/new_body.txt`），然后写入：

```bash
python skills/nsfc-justification-writer/scripts/run.py apply-section \
  --project-root projects/NSFC_Young \
  --title "国内外研究现状" \
  --body-file /tmp/new_body.txt
```

说明：
- 只允许写入白名单文件（默认仅 `extraTex/1.1.立项依据.tex`）
- 默认严格：若正文里新增 `\\cite{...}` 且 `.bib` 缺 key，会拒绝写入（防止“幻觉引用”）

## 5）引用与术语一致性（跨章节对齐）

引用核验并生成可复制提示词：

```bash
python skills/nsfc-justification-writer/scripts/run.py refs --project-root projects/NSFC_Young
```

术语一致性矩阵：

```bash
python skills/nsfc-justification-writer/scripts/run.py terms --project-root projects/NSFC_Young
```

## 6）回滚与差异查看（放心大胆迭代）

```bash
python skills/nsfc-justification-writer/scripts/run.py list-runs
python skills/nsfc-justification-writer/scripts/run.py diff --project-root projects/NSFC_Young --run-id <run_id>
python skills/nsfc-justification-writer/scripts/run.py rollback --project-root projects/NSFC_Young --run-id <run_id> --yes
```

## 7）最后验收

- `diagnose` 通过（结构/引用/字数/表述）
- `terms` 结果可接受（跨章节关键术语口径一致）
- 需要引用的外部工作全部可核验（DOI/链接/题录信息明确）

如需编译 PDF（含参考文献），按本仓库建议执行 4 步：

```text
xelatex → bibtex → xelatex → xelatex
```

