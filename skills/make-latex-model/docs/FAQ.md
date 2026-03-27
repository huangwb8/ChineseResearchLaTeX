# make-latex-model 常见问题

## Q1：这个 skill 现在还是只给 NSFC 用吗？

不是。

它现在面向整个 ChineseResearchLaTeX：

- `NSFC`
- `paper`
- `thesis`
- `cv`

NSFC 仍然是重要场景，但不再是唯一场景。

## Q2：它现在还只改 `extraTex/@config.tex` 吗？

不是。

那只是旧版 NSFC 工作流里的一个典型入口。现在更重要的是先选对层级：

- 单项目问题改 `projects/*`
- 共享样式问题改 `packages/bensz-*`

例如：

- `thesis` 的共享版式通常应该落在 `packages/bensz-thesis/styles/`
- `paper` 的共享样式与 DOCX 链路通常应该落在 `packages/bensz-paper/`
- `cv` 的共享类与双语支持通常应该落在 `packages/bensz-cv/`

## Q3：什么时候应该改公共包，而不是项目层？

当问题满足以下任一条件时，优先考虑公共包：

- 会影响多个项目
- 属于共享样式、profile、字体接入、统一构建逻辑
- 本来就应该是模板能力，而不是某个示例项目的私有参数

## Q4：如果我只有 Word 模板怎么办？

可以继续把 Word 导出成 PDF 作为 baseline。

优先顺序：

1. 官方 PDF
2. Word 导出 PDF
3. LibreOffice 导出 PDF

尽量不要用 QuickLook 之类的非 Word 渲染链路做像素级基线。

## Q5：还需要看 `scripts/README.md` 吗？

需要，但要带着新口径看：

- 那些脚本现在是辅助工具
- 它们不是当前仓库的权威工作流
- 一旦脚本假设与真实目录结构冲突，应直接以真实项目结构和官方构建命令为准

## Q6：`paper` 场景最容易忽略什么？

最容易只盯 PDF，忘了 DOCX。

当前仓库里，`paper` 模板默认要关注：

- PDF 是否正常
- DOCX 是否还能导出
- `extraTex/**/*.tex` 是否仍然是唯一正文真相来源

## Q7：`thesis` 场景最容易忽略什么？

最容易只改项目示例，而忘了真正的模板身份在包层。

尤其是新增学校或学位模板时，通常要同步考虑：

- `packages/bensz-thesis/profiles/`
- `packages/bensz-thesis/styles/`
- `projects/thesis-*/template.json`

## Q8：`cv` 场景最容易忽略什么？

最容易只看一个入口。

当前标准是：

- 中文入口：`main-zh.tex`
- 英文入口：`main-en.tex`

默认应一起验证。
