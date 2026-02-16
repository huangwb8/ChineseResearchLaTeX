# 工作流：已有草稿 → 诊断通过

适用：你已经有 `extraTex/1.1.立项依据.tex` 的初稿，但结构/引用/字数/表述存在问题，希望快速“诊断→迭代→可回滚→验收”。

路径提示：
- 在本仓库根目录运行：`python skills/nsfc-justification-writer/scripts/run.py ...`
- 在本 skill 目录运行：`python scripts/run.py ...`

## 0）先校验配置（可选）

```bash
python skills/nsfc-justification-writer/scripts/run.py validate-config
```

## 1）先跑一次 Tier1 诊断（把硬性问题先暴露）

```bash
python skills/nsfc-justification-writer/scripts/run.py diagnose --project-root <你的项目>
```

若结构缺失：先用 `assets/templates/structure_template.tex` 补齐 4 个 `\subsubsection{...}` 骨架，再进入正文优化。

## 2）必要时补齐引用（防止“幻觉引用”）

```bash
python skills/nsfc-justification-writer/scripts/run.py refs --project-root <你的项目>
```

把输出里的“可复制提示词”交给 `nsfc-bib-manager` 去核验/补齐，再回来继续写作。

## 3）用 coach 把任务拆小（每轮只改一个小标题）

```bash
python skills/nsfc-justification-writer/scripts/run.py coach --project-root <你的项目> --stage auto --topic "一句话主题"
```

把本轮生成的正文保存为文件（例如 `/tmp/new_body.txt`），然后安全写入：

```bash
python skills/nsfc-justification-writer/scripts/run.py apply-section \
  --project-root <你的项目> \
  --title "国内外研究现状" \
  --body-file /tmp/new_body.txt
```

## 4）跨章节术语口径检查（对齐 2.1/3.1）

```bash
python skills/nsfc-justification-writer/scripts/run.py terms --project-root <你的项目>
```

## 5）最终验收

```bash
python skills/nsfc-justification-writer/scripts/run.py diagnose --project-root <你的项目> --html-report auto
python skills/nsfc-justification-writer/scripts/run.py review --project-root <你的项目>
```

如需更严格的语义检查，可开启 Tier2（大文件可用分块与缓存控制）：

```bash
python skills/nsfc-justification-writer/scripts/run.py diagnose --project-root <你的项目> --tier2 --chunk-size 12000 --max-chunks 20
```
