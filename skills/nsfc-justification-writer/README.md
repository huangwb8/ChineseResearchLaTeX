# nsfc-justification-writer

本 Skill 用于撰写、重构、审查和润色 NSFC 申请书的立项依据。

它只保留一个核心闭环：**宿主 AI 负责理解和改写，Python 负责检查和安全写入**。

## 主流程

直接在支持 Skill 的宿主中提出任务：

```text
请使用 nsfc-justification-writer 重构立项依据。
项目目录：/path/to/project
要求：保留已核验事实、引用和 LaTeX 结构，只修改立项依据正文。
请输出修改摘要、假设/待核验项、unified diff、备份路径和回滚命令。
```

宿主 AI 会：

1. 读取目标正文、研究内容、研究基础和参考文献；
2. 按“研究意义 → 国内外研究现状 → 科学问题与科学假设 → 小结”组织内容；
3. 一次性完成逻辑、证据、章节边界、正文自然度、术语和专业可读性检查；科学问题与假设从现状缺口自然收束，正文优先推进科学判断，证据等级、外推边界和待核验项单独列入审查记录；
4. 生成完整正文提案，并调用 `preview` 完成安全写入。

材料不足时，AI 缩小正文主张并在审查记录中列出待核验项，不用连续否定句填补缺口，也不编造文献、结果或绝对化结论。

## 参考资料

- [分节写法](references/section_writing.md)：从论证地图到四个小节的段落推进、证据组织和章节边界。
- [质量控制](references/quality_control.md)：AI 语义审查与脚本安全检查。
- [边界表达回归样例](references/regression_examples.md)：五类匿名案例，复核正文判断、叙事收束与审查记录是否分离。

不再提供独立的信息表模板：宿主 AI 直接从项目材料提取研究对象、现有瓶颈、科学问题、假设和切入点。需要整理输入时，参照 [`references/section_writing.md`](references/section_writing.md) 的论证地图。诊断命令只输出文本或 JSON，不生成 HTML 报告。

## 固定写作边界

- 研究意义默认 2–3 段，约占正文 15%–25%；
- 研究现状按课题主题组织，每个主题默认 1 段，必要时最多 2 段；
- 科学问题与假设采用“现状缺口 → 核心未知 → 项目切入点 → 可证伪预测”的连续叙述；不把 `R1/R2/R3`、`H1/H2`、模型配置、数据划分和评价协议写成问题或假设主体；
- 研究目标、技术路线、主验证场景、终点、阈值和风险处理属于后续章节；
- 字数只按配置的统计口径报告，不设默认目标或容差；如项目有明确篇幅要求，由用户另行指定；
- 不新增无法在项目 `.bib` 中核验的引用；
- 段首先写科学判断；每段默认只保留一个会改变解释的核心限定，同一限制不在后文重复展开；证据等级、临床外推边界和待核验项单独输出，不逐项写成正文免责声明；
- 只修改白名单正文，不修改 `main.tex`、`.cls`、`.sty` 或配置文件。

## Python 入口

AI 生成完整正文提案后运行：

```bash
python skills/nsfc-justification-writer/scripts/run.py preview \
  --project-root <项目目录> \
  --proposal-file <完整正文提案.tex>
```

需要只读检查时加 `--dry-run`。脚本负责目标路径、白名单、引用 key、结构命令变化、diff、备份和回滚，不负责判断研究逻辑。

常用辅助命令：

```bash
python skills/nsfc-justification-writer/scripts/run.py diagnose --project-root <项目目录>
python skills/nsfc-justification-writer/scripts/run.py refs --project-root <项目目录>
python skills/nsfc-justification-writer/scripts/run.py wordcount --project-root <项目目录>
```

## 写入与回滚

默认 `preview` 会在写入前备份，并输出实际 diff。查看和回滚：

```bash
python skills/nsfc-justification-writer/scripts/run.py list-runs
python skills/nsfc-justification-writer/scripts/run.py diff \
  --project-root <项目目录> --run-id <run_id>
python skills/nsfc-justification-writer/scripts/run.py rollback \
  --project-root <项目目录> --run-id <run_id> --yes
```

版本号以 [`config.yaml`](config.yaml) 的 `skill_info.version` 为准，执行规范见 [`SKILL.md`](SKILL.md)。
