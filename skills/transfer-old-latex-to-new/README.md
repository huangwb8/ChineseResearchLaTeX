# transfer-old-latex-to-new — 用户使用指南

本 README 面向使用者：怎么把旧材料、旧模板、旧项目或零散输入，迁移/整理/重构到当前 `ChineseResearchLaTeX` 的真实项目结构里。

**技能名称**：`transfer-old-latex-to-new`  
**版本**：`v2.0.0`  
**最后更新**：`2026-03-27`

兼容历史别名：`migrating-latex-templates`。后续文档统一使用 `transfer-old-latex-to-new`。

## 现在这个 skill 是做什么的

它不再只是“旧 NSFC 标书搬到新目录”的窄工具。

现在它更适合做这些事：

- 把旧标书接到当前 `projects/NSFC_*`
- 把旧论文材料接到 `projects/paper-sci-01/`
- 把旧毕业论文或公开 baseline 整理成 `projects/thesis-*`
- 把旧简历或公开样式整理成 `projects/cv-01/`
- 把旧模板里的共享逻辑上收到 `packages/`
- 接受 `tex/docx/pdf/md/截图/说明文字/旧项目目录` 的任意组合输入

一句话理解：

**目标不是守住固定输入输出格式，而是按当前仓库结构，把模板或项目真正做对。**

## 推荐用法

直接告诉 AI 目标、已有材料和你想得到的结果即可。

最小可用 prompt：

```text
请使用 transfer-old-latex-to-new skill。
目标：把这些旧材料迁移/整理/重构到 ChineseResearchLaTeX 当前合适的模板里。
输入：<你现有的项目目录、tex/docx/pdf/md、截图、说明文字，给什么都可以>
要求：请你自己判断应该改 packages 还是 projects，最后做出一个结构清晰、可维护、尽量可构建的结果；输出形式也由你自主决定。
```

## 常见场景

### 场景 1：旧 NSFC 标书迁到当前项目

```text
请使用 transfer-old-latex-to-new skill。
目标：把我这份旧 NSFC 标书迁移到当前仓库合适的 NSFC 项目里。
输入：
- 旧项目目录：/path/to/old-nsfc
- 目标模板参考：projects/NSFC_Young
要求：
- 以当前 ChineseResearchLaTeX 结构为准
- 不要被旧目录结构绑住
- 最后尽量给出一个能继续写作的干净项目
```

### 场景 2：把 Word/PDF/零散 tex 整理成论文模板

```text
请使用 transfer-old-latex-to-new skill。
目标：把这些论文材料整理进当前仓库的 SCI 模板。
输入：
- Word 稿
- 若干 PDF 截图
- 一个旧 tex 目录
- 目标项目：projects/paper-sci-01
要求：你自己决定哪些内容写入 extraTex，哪些内容需要补说明，输出不要预设固定格式。
```

### 场景 3：毕业论文模板接入

```text
请使用 transfer-old-latex-to-new skill。
目标：把这套旧毕业论文模板接成 ChineseResearchLaTeX 当前 thesis 产品线里的一个规范项目。
输入：
- 旧模板目录：/path/to/legacy-thesis
- 公开 baseline PDF：/path/to/baseline.pdf
- 当前最接近项目：projects/thesis-nju-master
要求：
- 按当前 projects/thesis-* 的真实结构处理
- 必要时补齐 template.json、README 和项目入口
- 以“做出一个好模板”为优先目标
```

### 场景 4：简历模板样式迁移

```text
请使用 transfer-old-latex-to-new skill。
目标：把我现有的简历样式迁移成当前仓库可维护的 cv 项目。
输入：
- 旧简历 PDF
- 一份旧 tex
- 目标项目：projects/cv-01
要求：请自主决定最终需要改哪些文件、生成哪些辅助说明，重点保证后续维护方便。
```

## 输入和输出怎么理解

### 输入

这个 skill **不要求固定输入协议**。

你可以提供：

- 目录
- 单文件
- 多个文件混合
- 截图
- 文字描述
- 当前仓库里的某个项目作为目标参考

如果材料不完整，AI 会先尽量自行判断，而不是先要求你把输入整理成某个硬编码格式。

### 输出

这个 skill **不预设固定输出清单**。

AI 会根据任务决定输出方式，常见结果包括：

- 直接修改目标项目
- 新建或重写 `extraTex/*.tex`
- 调整 `main.tex`、wrapper、README、`template.json`
- 把共享逻辑迁到 `packages/`
- 补一份简短的迁移说明、风险提示或验收记录

如果任务需要额外工作区或中间文件，AI 会自行安排到合适位置。

## 设计理念

这个 skill 现在遵循三条原则：

1. **当前仓库结构优先**
   先看 `packages/` 和 `projects/` 的真实分层，不沿用旧记忆。

2. **AI 自主托管输入输出**
   不要求用户先按 old/new 目录或固定文件名整理材料。

3. **结果导向**
   重点是把模板或项目做得正确、清晰、可维护，而不是机械完成某个旧脚本流程。

## 备选用法（legacy CLI）

如果你的任务刚好还是经典的“旧目录 -> 新目录”迁移，也可以用本 skill 自带脚本。

### 分析

```bash
python skills/transfer-old-latex-to-new/scripts/run.py analyze \
  --old /path/to/old_project \
  --new /path/to/new_project
```

### 应用

```bash
python skills/transfer-old-latex-to-new/scripts/run.py apply \
  --run-id <run_id> \
  --old /path/to/old_project \
  --new /path/to/new_project
```

### 编译验证

```bash
python skills/transfer-old-latex-to-new/scripts/run.py compile \
  --run-id <run_id> \
  --new /path/to/new_project
```

更完整的脚本说明见 [scripts/README.md](scripts/README.md)。

## FAQ

### 它还只适用于 NSFC 吗？

不是。现在默认面向 `NSFC / paper / thesis / cv` 四条已落地产品线。

### 我只有 Word、PDF 和一些截图，没有标准 LaTeX 输入，能用吗？

能用。这个 skill 的默认前提就是“输入不必规整”。

### 输出一定会给我一堆固定报告吗？

不会。输出由 AI 自主决定，只要对完成任务有帮助即可。

### 它还会用到 `runs/<run_id>/` 吗？

可能会，但那已经是可选实现细节，不再是这个 skill 的主约束。

### 什么时候应该改 `packages/`，什么时候改 `projects/`？

如果是共享样式、共享逻辑、共享脚本问题，优先改 `packages/`。如果是某个具体示例项目、正文、入口、元数据问题，优先改 `projects/`。

## 相关文件

- 执行规范见 [SKILL.md](SKILL.md)
- 默认参数见 [config.yaml](config.yaml)
- legacy CLI 说明见 [scripts/README.md](scripts/README.md)
- 变更记录见 [CHANGELOG.md](CHANGELOG.md)
