# nsfc-justification-writer 脚本

脚本只承担确定性边界：目标文件定位、路径白名单、引用 key、字数统计、备份、diff 和回滚。逻辑、术语、论证维度、可读性等语义判断与正文改写由宿主 AI 自动完成。

## 推荐流程

1. 配置中声明 `targets.justification_tex`；未声明时自动追踪 `main.tex` 并按确定性优先级选择候选。
2. AI 输出完整正文提案，运行 `preview` 自动生成 unified diff 并写入。
3. 写入前自动备份，写入后输出 diff；需要只读检查时显式使用 `--dry-run`，不需要人工确认。

```bash
python skills/nsfc-justification-writer/scripts/run.py preview \
  --project-root projects/NSFC_Young \
  --proposal-file /tmp/proposal.tex
```

默认 `preview` 不解析标题但会自动写入；如果新增/删除行包含章节、环境、引用入口或配置命令，宿主 AI 自动退回正文-only 提案并重试。`--dry-run` 可强制只读。

## 独立工具

```bash
python skills/nsfc-justification-writer/scripts/run.py refs --project-root projects/NSFC_Young
python skills/nsfc-justification-writer/scripts/run.py wordcount --project-root projects/NSFC_Young
python skills/nsfc-justification-writer/scripts/run.py diagnose --project-root projects/NSFC_Young
python skills/nsfc-justification-writer/scripts/run.py coach --project-root projects/NSFC_Young --stage auto
```

`diagnose/coach/review` 的结果是建议，不以固定小节数、开篇关键词或页数阈值阻断写作。逻辑、术语、论证维度和专业可读性由宿主 AI 自主规划并复核；措辞中的吹牛式、绝对化和无依据夸大表述由宿主 AI 按 `references/boastful_expression_guidelines.md` 复核，Python 不维护固定短语表。需要时可在配置 `constraints` 中显式启用独立预警。

完整诊断还要按标准立项依据区分内容职责。宿主 AI 应分别检查：研究意义说明必要性与研究价值；研究现状及发展动态按主题呈现代表性证据、趋势、能力边界和关键缺口；小结压缩科学问题/假设与项目切入点，并简短衔接研究内容。科学问题和假设是现状末端的论证要素，不要求单独成章。研究目标、总体研究思路、技术路线、主验证场景、排除标准、终点、阈值和风险处理属于研究内容、研究方案或研究基础。申请人前期工作通常作为现状末端的切入点证据，详细流程、公式、终点和可行性材料后移。章节边界发现必须在报告中给出位置、当前职责、建议归属和理由；跨小节移动先形成章节级提案，再生成正文 diff。

## legacy 兼容入口

```bash
python skills/nsfc-justification-writer/scripts/run.py apply-section \
  --project-root projects/NSFC_Young \
  --title "国内外研究现状" \
  --body-file /tmp/new_body.txt
```

该命令仍按 `\\subsubsection` 标题替换正文，仅用于迁移旧项目；它不会成为新项目默认工作流。标题未命中时不要改正文来适配检查器，应改用 `preview` 并明确正文范围。

## 版本管理与验证

```bash
python skills/nsfc-justification-writer/scripts/run.py list-runs
python skills/nsfc-justification-writer/scripts/run.py diff --project-root projects/NSFC_Young --run-id <run_id>
python skills/nsfc-justification-writer/scripts/run.py rollback --project-root projects/NSFC_Young --run-id <run_id> --yes
python skills/nsfc-justification-writer/scripts/run.py validate-config
```
