# make-latex-model 常见问题

## Q1：这个 skill 现在还是只给 NSFC 用吗？

不是。

它现在面向整个 ChineseResearchLaTeX：

- `NSFC`
- `paper`
- `thesis`
- `cv`

NSFC 仍然是重要场景，但它只是四条产品线之一。

## Q2：它现在还只改 `extraTex/@config.tex` 吗？

不是。

`extraTex/@config.tex` 只是 NSFC 项目层的一个具体入口。现在更重要的是先选对层级：

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

但注意：这不等于“发现是共享问题就直接改”。现在的硬规则是：

1. 先说明为什么项目层方案不够
2. 先生成包层回归计划
3. 改完后回归该公共包覆盖的全部现有模板

推荐命令：

```bash
python3 skills/make-latex-model/scripts/plan_package_regression.py packages/bensz-thesis
```

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

## Q9：如果我必须改 `packages/`，怎么保证不伤到其它模板？

不要靠主观判断，要靠回归矩阵。

做法是：

1. 先运行 `plan_package_regression.py` 看这个公共包覆盖了哪些现有项目
2. 优先把改动收敛到模板专属 `profile / style`，而不是先改共享核心入口
3. 改完后先验证当前目标项目，再逐个回归这些受影响项目
4. 若受影响项目已有 baseline，再补跑官方 compare

如果没有完成这些验证，就不能把结果表述成“不会影响其它模板”。
