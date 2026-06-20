---
name: paper-know-journal
description: 当用户给出期刊/杂志名并希望了解投稿要求、投稿形式/格式清单、期刊官网信息、社区评价、审稿速度、费用、文章类型、格式细节或“这个 journal 怎么投/是否靠谱/投稿指南调研”时必须使用。联网核验期刊官网与社区评测，默认把全部中间文件隔离到当前工作目录的 `.paper-know-journal/`，最终只交付 `KnowJournal-{杂志名}.md`。⚠️ 不适用：用户要根据 manuscript 选择投稿期刊（用 paper-select-journal）、写论文正文、下载全文 PDF，或只问一个无需成稿的简单事实。
metadata:
  author: Bensz Conan
  short-description: 按期刊名生成投稿要求与社区评价调研报告
  keywords:
    - paper-know-journal
    - 期刊调研
    - 投稿指南
    - 投稿要求
    - 投稿形式要求
    - 社区评价
    - journal guide
---

# paper-know-journal

## 与 bensz-collect-bugs 的协作约定

- 因本 skill 设计缺陷导致的 bug，先用 `bensz-collect-bugs` 规范记录到 `~/.bensz-skills/bugs/`，不要直接修改用户本地已安装的 skill 源码；若有 workaround，先记 bug，再继续完成任务。
- 只有用户明确要求“report bensz skills bugs”等公开上报时，才用本地 `gh` 上传新增 bug 到 `huangwb8/bensz-bugs`；不要 pull / clone 整个仓库。

## 输入与输出

输入：期刊/杂志名；可附加输出目录、工作区、关注方向、目标文体/文章类型（如 Article、Original Research、Review、Brief Communication、Case Report、Letter）或目标 manuscript 类型。

输出：`KnowJournal-{杂志名}.md`，默认在用户当前工作目录根目录；用户指定输出位置时按指定保存。文件名中的 `/\:*?"<>|` 等路径危险字符替换为 `-`。

中间文件：默认全部放入 `.paper-know-journal/run-<timestamp>/`。除最终 Markdown 和用户明确指定输出外，不得在隐藏工作区外写检索日志、网页摘录、截图、草稿、JSON、临时下载或运行缓存。

测试区：轻量验证用 `./tests/paper-know-journal/`；测试证据不得混入最终报告。

## 标准工作流

### 初始化

先运行脚本创建隔离工作区、测试区和安全输出路径：

```bash
python3 /path/to/paper-know-journal/scripts/init_workspace.py \
  --journal "Cancer Cell" \
  --cwd "$PWD"
```

脚本会打印 `workspace_dir`、`output_path`、`test_dir`、`manifest_path`、`sources_path`。所有中间产物写入 `workspace_dir`。如提示 `output_path already exists`，覆盖前先向用户确认或改用新路径。

如用户指定输出目录或工作区：

```bash
python3 /path/to/paper-know-journal/scripts/init_workspace.py \
  --journal "Journal for ImmunoTherapy of Cancer" \
  --cwd "$PWD" \
  --output-dir "/path/to/output" \
  --workspace-dir "/path/to/.paper-know-journal"
```

### 调研

必须联网核验，至少覆盖：

- 官方来源：期刊官网、作者指南、投稿系统说明、manuscript preparation / formatting guidelines、出版商政策页、费用页、编辑政策页。
- 社区/第三方来源：SciRev、LetPub、ResearchGate、Reddit、X/Twitter、论坛、机构图书馆说明、作者经验贴等。第三方只作体验线索，不替代官方政策。

优先查证这些信息：

- 期刊全称、出版社/学会、ISSN、官网、投稿入口。
- scope、文章类型、字数/摘要/图表/参考文献限制。
- 目标文体/文章类型的具体要求：用户指定文体时必须覆盖该文体；未指定时先列出官方文章类型，再选择 2-3 个最常见或最相关类型（通常包括原创研究与综述）展开。逐项核验该类型的名称、正文/摘要字数或页数、摘要类型、关键词数量、章节标题与顺序、图表/补充材料/参考文献限制、报告规范清单和特殊提交材料。
- 投稿形式要求：标题页、作者信息、摘要类型与字数、关键词、正文结构、章节标题、文件组成、模板、行距/页码/编号、图表文件格式与分辨率、补充材料、参考文献格式、cover letter、报告规范清单。
- OA/订阅模式、APC、许可证、是否有会员折扣或豁免。
- 审稿方式、首轮决定时间、接收到上线时间、接收率；没有官方数据时标明来源类型和不确定性。
- 格式要求：标题页、摘要、关键词、正文结构、图像分辨率、补充材料、参考文献格式、声明章节、数据/代码/AI 使用政策。
- 近期文章格式：抽样 2-3 篇近年同类文章，归纳摘要、正文结构、图表数量、声明与参考文献风格。
- 社区评价：速度、沟通、拒稿/大修体验、费用争议、透明度、常见槽点；与官方信息分开写。

调研时维护 `sources.json`：

- `official`：官方网页、作者指南、费用页、投稿系统、出版伦理页。
- `community`：SciRev、LetPub、论坛、作者经验贴、机构说明等。
- `article_samples`：近期代表性已发表文章。

每条来源至少记录 `title`、`url`、`source_type`、`accessed_at`、`key_facts`。网页摘录、检索日志和草稿只能放在 `workspace_dir` 内。

资料处理规则见 `references/source-policy.md`。报告结构见 `references/report-template.md`。

### 成稿

用中文 Markdown 输出，风格接近 JITC / Cancer Cell 调研样例：先给关键结论和期刊概况，再写投稿要求、投稿形式要求、真实文章格式、社区评价和投稿建议。

报告必须包含：

- 调研日期。
- 期刊名称和可核验官网链接。
- “官方信息”和“社区评价/第三方信息”的来源区分。
- 独立的“投稿形式要求与格式清单”章节；不能只用近期文章样本替代官方投稿格式要求。
- 在“投稿形式要求与格式清单”中包含独立的“目标文体/文章类型具体要求”小节；对每个目标文体写清楚官方章节标题/顺序、字数或页数、摘要、关键词、图表、参考文献和特殊文件要求。若官方采用 format-free / free format 初投稿，也要写清哪些项目仍需满足、哪些项目仅修回或接收后适用。
- 面向投稿准备的可执行清单，至少覆盖标题页、摘要/关键词、正文结构、图表、补充材料、参考文献、声明/伦理/数据/代码/AI、投稿文件或 cover letter；官方未披露时逐项写“未在官方页面确认”。
- 对缺失、冲突或疑似过期信息的显式标注。
- 来源清单，含链接与访问日期。

不得输出未核验断言。影响因子、分区、费用、审稿时长等易变信息必须写来源年份或访问日期。

### 验证

成稿后运行：

```bash
python3 /path/to/paper-know-journal/scripts/validate_report.py \
  --report "KnowJournal-Cancer Cell.md" \
  --journal "Cancer Cell"
```

验证通过后告知用户：最终文件路径、主要来源数量、无法确认的信息和残余风险。

## 失败处理

- 找不到官网：先用出版商、ISSN、NLM Catalog、DOAJ、Crossref、期刊投稿系统交叉定位；仍不能确认时停止成稿并说明需要用户确认目标期刊。
- 同名期刊冲突：列出候选期刊、出版社和 ISSN，先让用户确认。
- 社区评价稀少：明确写“未找到足够社区评价”，不要编造体验。
- 官方信息与社区信息冲突：以官方政策为准，社区信息作为体验线索，并标注冲突点。
- 网站无法访问：记录访问失败、尝试替代官方页面或缓存摘要；关键政策无法核验时在报告中列为待确认。
