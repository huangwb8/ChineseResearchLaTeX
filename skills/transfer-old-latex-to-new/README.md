# transfer-old-latex-to-new — 用户使用指南

本 README 面向使用者：怎样把旧材料里的正文内容迁移到当前 `ChineseResearchLaTeX` 现有模板项目的内容层。

**技能名称**：`transfer-old-latex-to-new`  
**版本**：`v2.1.0`  
**最后更新**：`2026-03-28`

兼容历史别名：`migrating-latex-templates`。后续文档统一使用 `transfer-old-latex-to-new`。

## 现在这个 skill 是做什么的

它现在是一个**内容迁移 skill**，不是模板开发 skill。

它适合做这些事：

- 把旧标书正文接到当前 `projects/NSFC_*`
- 把旧论文正文接到 `projects/paper-sci-01/`
- 把旧毕业论文正文接到合适的 `projects/thesis-*`
- 把旧简历正文接到 `projects/cv-01/`
- 接受 `tex/docx/pdf/md/截图/说明文字/旧项目目录` 的任意组合输入

它**不负责**做这些事：

- 修改 `packages/` 里的公共包源码
- 修改 `projects/` 里的模板样式、入口骨架、`main.tex`、`extraTex/@config.tex`
- 为了复刻旧样式而重写模板
- 把共享逻辑上收到 `packages/`

一句话理解：

**这个 skill 只把正文内容放到现有模板的合适位置，不碰模板源码和样式。**

## 推荐用法

直接告诉 AI 目标、已有材料和目标项目即可。

最小可用 prompt：

```text
请使用 transfer-old-latex-to-new skill。
目标：把这些旧材料迁移到 ChineseResearchLaTeX 当前合适的现有模板项目里。
输入：<你现有的项目目录、tex/docx/pdf/md、截图、说明文字，给什么都可以>
硬性约束：
- 只能迁移正文内容和参考文献
- 绝不能修改 packages/ 里的公共包源码
- 绝不能修改 projects/ 里的模板样式、main.tex、@config.tex、wrapper 或其它模板骨架
- 只把内容放到合适的 extraTex/*.tex 和 references/*.bib
输出：给我一个内容已经落位、最好可构建、并明确说明剩余缺口的结果
```

## 常见场景

### 场景 1：旧 NSFC 标书迁到当前项目

```text
请使用 transfer-old-latex-to-new skill。
目标：把我这份旧 NSFC 标书正文迁移到当前仓库合适的 NSFC 项目里。
输入：
- 旧项目目录：/path/to/old-nsfc
- 目标模板参考：projects/NSFC_Young
要求：
- 只迁移正文与参考文献
- 不要修改模板样式和项目骨架
- 如果当前模板缺少承载位点，只报告，不要偷改模板
```

### 场景 2：把 Word/PDF/零散 tex 整理成论文正文

```text
请使用 transfer-old-latex-to-new skill。
目标：把这些论文材料整理进当前仓库的 SCI 模板正文层。
输入：
- Word 稿
- 若干 PDF 截图
- 一个旧 tex 目录
- 目标项目：projects/paper-sci-01
要求：
- 只写入 extraTex 和 references
- 不修改 main.tex、模板样式和构建脚本
```

### 场景 3：毕业论文正文接入

```text
请使用 transfer-old-latex-to-new skill。
目标：把旧毕业论文正文接到 ChineseResearchLaTeX 当前 thesis 产品线里的一个现有项目。
输入：
- 旧模板目录：/path/to/legacy-thesis
- 当前最接近项目：projects/thesis-nju-master
要求：
- 只迁移内容，不开发新模板
- 如果版式差异必须通过改模板才能解决，请直接指出
```

### 场景 4：简历正文接入

```text
请使用 transfer-old-latex-to-new skill。
目标：把我现有的简历正文迁移到当前仓库的 cv 项目内容层。
输入：
- 旧简历 PDF
- 一份旧 tex
- 目标项目：projects/cv-01
要求：
- 只放正文内容
- 不改简历模板样式和骨架
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

如果材料不完整，AI 会先尽量判断哪些内容能安全落位，哪些缺口超出内容迁移边界。

### 输出

这个 skill **也不预设一堆固定报告**。

常见结果包括：

- 直接更新目标项目的 `extraTex/*.tex`
- 更新目标项目的 `references/*.bib`
- 补一份简短的迁移说明、未落位清单或风险提示
- 给出官方构建验证结果

它默认**不会**输出这些改动：

- `main.tex`
- `extraTex/@config.tex`
- `.cls` / `.sty`
- `packages/` 下公共包源码
- 模板 wrapper、style、profile、构建脚本

## 设计理念

这个 skill 现在遵循三条原则：

1. **现有模板骨架只读**
   目标模板是承载容器，不是让这个 skill 顺手改造的对象。

2. **内容层优先**
   默认只迁移到 `extraTex/*.tex` 和 `references/*.bib`。

3. **边界清晰**
   如果任务已经变成模板开发，应该转给 `make-latex-model`，而不是让这个 skill 偷偷越界。

## 备选用法（legacy CLI）

如果你的任务刚好还是经典的“旧目录 -> 新目录”迁移，也可以用本 skill 自带脚本。

注意：即使使用脚本，仍然只能写内容层，不能借 CLI 改模板骨架。

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

### 它还会修改 `packages/` 或模板样式吗？

不会。当前版本明确禁止这样做。

### 我只有 Word、PDF 和一些截图，没有标准 LaTeX 输入，能用吗？

能用。这个 skill 的默认前提就是“输入不必规整”。

### 如果当前模板放不下我的内容怎么办？

这个 skill 会指出缺口，但不会为了容纳内容去改模板。那属于模板开发任务。

### 输出一定会给我固定报告吗？

不会。只要能把内容安全落位，并把剩余问题讲清楚即可。

### 什么时候不该再用这个 skill？

当你的真实需求是“开发/修改模板”而不是“迁移正文内容”时，就不该继续用它。

## 相关文件

- 执行规范见 [SKILL.md](SKILL.md)
- 默认参数见 [config.yaml](config.yaml)
- legacy CLI 说明见 [scripts/README.md](scripts/README.md)
- 变更记录见 [CHANGELOG.md](CHANGELOG.md)
