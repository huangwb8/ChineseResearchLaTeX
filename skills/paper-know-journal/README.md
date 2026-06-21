# paper-know-journal

这个 skill 用来按“期刊名”调研投稿要求、目标文体/文章类型的具体格式清单、官网政策和社区评价，并生成一份可交付的中文 Markdown 报告。

## 用法

### 最推荐用法

```text
请使用 paper-know-journal skill 调研这个期刊的投稿要求、投稿形式要求和社区评价。
输入：Cancer Cell
输出：`KnowJournal-Cancer Cell.md`，保存在当前工作目录根目录
```

### 指定输出目录

```text
请使用 paper-know-journal skill 调研 Journal for ImmunoTherapy of Cancer。
输出：保存到 `/path/to/reports/`
另外，所有中间文件仍放在当前工作目录的 `.bensz-api/skills/paper-know-journal/`
```

### 聚焦某类稿件

```text
请使用 paper-know-journal skill 调研 Nature Medicine 的 Article 和 Review 投稿要求。
输出：`KnowJournal-Nature Medicine.md`
另外，请重点关注 Article 和 Review 各自的章节标题/顺序、正文或摘要字数、关键词、图表数量、补充材料、参考文献格式、数据政策、APC 和社区审稿速度反馈。
```

## 能做什么

- 联网核验期刊官网、作者指南、投稿系统、费用和出版政策。
- 按指定文体/文章类型整理具体要求，例如 Article、Original Research、Review、Brief Communication 的章节顺序、字数/页数、摘要、关键词、图表、参考文献和特殊提交材料。
- 单独整理投稿形式要求：标题页、摘要/关键词、正文结构、图表、补充材料、参考文献、声明、投稿文件和 cover letter。
- 补充 SciRev、LetPub、论坛、作者经验等社区评价。
- 抽样近期已发表文章，观察真实文章结构、图表数量和声明写法。
- 输出类似 JITC / Cancer Cell 投稿指南调研的中文 Markdown 报告。
- 默认把中间文件隔离到 `.bensz-api/skills/paper-know-journal/{yyyy-mm-dd-hh-mm}/`。

## 输出

- 最终报告：`KnowJournal-{杂志名}.md`
- 默认输出位置：当前工作目录根目录
- 默认隐藏工作区：`.bensz-api/skills/paper-know-journal/{yyyy-mm-dd-hh-mm}/`
- 来源索引：隐藏工作区内的 `sources.json`
- 默认测试区：`./tests/paper-know-journal/`
- 报告会区分官方政策与社区/第三方评价；官方政策优先，社区反馈只作为投稿体验线索。
- 报告会包含独立的“投稿形式要求与格式清单”章节；官方未披露的格式项会标明“未在官方页面确认”。
- 报告会包含“目标文体/文章类型具体要求”小节；用户指定稿件类型时优先覆盖指定类型，未指定时会说明默认选择展开的官方文章类型。
- 报告末尾应包含来源与可信度表，标注来源类型和访问日期。

## 脚本

初始化工作区：

```bash
python3 paper-know-journal/scripts/init_workspace.py --journal "Cancer Cell" --cwd "$PWD"
```

验证最终报告：

```bash
python3 paper-know-journal/scripts/validate_report.py \
  --report "KnowJournal-Cancer Cell.md" \
  --journal "Cancer Cell"
```

## 注意

- 官方政策优先，社区评价只作为体验线索。
- 近期文章格式观察不能替代官方投稿形式要求，只能作为补充证据。
- 影响因子、APC、审稿周期等易变信息必须带来源年份或访问日期。
- 找不到足够社区评价时应明确说明，不编造作者体验。
