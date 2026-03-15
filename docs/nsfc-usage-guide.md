# 国自然模板使用说明

本文面向第一次使用本仓库 NSFC 模板的用户，介绍当前“公共包 + 薄项目”模式下的基本使用方法。为便于说明，正文以下以青年基金项目 `projects/NSFC_Young/` 为例，演示“安装公共包 -> 编辑正文 -> 编译 PDF -> 管理版本”的完整流程。

如果你正在使用单独下载的青年基金项目压缩包，也可以参考本文；只是在“编译入口”处应优先使用项目内自带的 `scripts/nsfc_build.py` 包装脚本。

## 先理解当前结构

当前仓库不是“每个项目各带一整套样式文件”的旧结构，而是：

- `packages/bensz-nsfc/`：NSFC 公共包源码、共享样式、共享字体、共享 BibTeX 资源、官方脚本入口
- `projects/NSFC_Young/`：青年基金项目正文示例和最薄的一层入口封装
- `docs/`：迁移说明、写作指南和本文这类辅助文档

其中，青年基金项目的关键入口文件是：

- [`projects/NSFC_Young/main.tex`](../projects/NSFC_Young/main.tex)：主控文件
- [`projects/NSFC_Young/extraTex/@config.tex`](../projects/NSFC_Young/extraTex/@config.tex)：模板配置入口，目前只保留 `\usepackage[type=young]{bensz-nsfc-common}`
- [`projects/NSFC_Young/extraTex/`](../projects/NSFC_Young/extraTex/)：各章节正文文件
- [`projects/NSFC_Young/references/myexample.bib`](../projects/NSFC_Young/references/myexample.bib)：参考文献数据
- [`packages/bensz-nsfc/scripts/install.py`](../packages/bensz-nsfc/scripts/install.py)：安装、锁定、同步、回退
- [`packages/bensz-nsfc/scripts/nsfc_project_tool.py`](../packages/bensz-nsfc/scripts/nsfc_project_tool.py)：统一构建与清理

## 你属于哪种使用场景

建议先判断自己属于下面哪一类：

### 场景 A：在完整仓库里使用模板

适合想直接使用本仓库、也可能顺手查看源码和文档的用户。本文默认优先按这个场景说明。

### 场景 B：只拿到了青年基金项目压缩包

这种情况下，项目目录通常只有 `NSFC_Young/` 自身内容。你仍然应该先安装 `bensz-nsfc` 公共包，再进入项目目录编译。

### 场景 C：打算上传到 Overleaf

请优先使用 Release 生成的 `NSFC_Young-Overleaf-<tag>.zip`。这个压缩包已经内嵌运行时文件和共享资源，上传后直接选择 XeLaTeX 编译即可。

## 获取模板

优先建议使用 GitHub Release，而不是主分支快照。Release 更稳定，适合普通写标书场景。

如果你在当前仓库里开发或验证模板，则直接使用当前工作树即可。

## 安装 NSFC 公共包

### 使用正式版本

在仓库根目录执行：

```bash
python packages/bensz-nsfc/scripts/install.py install --ref <tag>
```

例如：

```bash
python packages/bensz-nsfc/scripts/install.py install --ref v3.5.1
```

这一步会把 `bensz-nsfc` 安装到你的 `TEXMFHOME` 下，供 `NSFC_Young`、`NSFC_General`、`NSFC_Local` 共用。

### 开发当前仓库源码

如果你正在当前仓库里联调公共包源码，用本地源码安装更合适：

```bash
python packages/bensz-nsfc/scripts/install.py install --source local --path packages/bensz-nsfc --ref local-dev
```

## 编译青年基金示例项目

### 方式 1：完整仓库模式下的官方入口

在仓库根目录执行：

```bash
python packages/bensz-nsfc/scripts/nsfc_project_tool.py build --project-dir projects/NSFC_Young
```

这是当前推荐的官方构建链路。它会自动执行：

```text
xelatex -> bibtex -> xelatex -> xelatex
```

并且会：

- 把中间文件隔离到 `projects/NSFC_Young/.latex-cache/`
- 仅把最终 `main.pdf` 留在 `projects/NSFC_Young/`
- 保留 `.latex-cache/main.synctex.gz` 以支持 VS Code 跳转

### 方式 2：单项目压缩包模式

如果你只打开了 `NSFC_Young/` 这个项目目录，优先在项目根目录执行：

```bash
python scripts/nsfc_build.py build --project-dir .
```

这个脚本会自动尝试：

1. 在完整仓库路径下查找 `packages/bensz-nsfc/scripts/nsfc_project_tool.py`
2. 用 `kpsewhich bensz-nsfc-common.sty` 定位已安装包路径
3. 再兜底查找常规 `TEXMFHOME/tex/latex/bensz-nsfc/`

因此它更适合普通用户从 Release zip 打开项目后直接编译。

### 方式 3：Overleaf

上传 `NSFC_Young-Overleaf-<tag>.zip` 后：

1. 打开 Overleaf 项目
2. 在 Menu 中将编译器设置为 `XeLaTeX`
3. 点击 Recompile

Overleaf 场景下，默认不需要再手工安装 `bensz-nsfc` 公共包。

## 应该编辑哪些文件

青年基金项目的正文内容主要在 [`projects/NSFC_Young/extraTex/`](../projects/NSFC_Young/extraTex/) 下：

- `1.1.立项依据.tex`：研究意义、国内外现状、不足、关键科学问题、研究思路
- `2.1.研究内容.tex`：研究内容、研究目标、拟解决的关键科学问题
- `2.2.特色与创新.tex`：特色与创新点
- `2.3.年度研究计划.tex`：三年计划与预期成果
- `3.1.研究基础.tex`：研究积累、可行性、风险应对
- `3.2.工作条件.tex`：已有条件、缺少条件、解决途径
- `3.3.承担项目情况.tex`：正在承担项目
- `3.4.完成国基项目情况.tex`：已完成基金项目
- `4.1` 到 `4.6`：按实际情况填写的声明项

一般情况下：

- 优先修改正文文件，而不是改样式
- 非必要不要改 [`projects/NSFC_Young/extraTex/@config.tex`](../projects/NSFC_Young/extraTex/@config.tex)
- 如果问题影响三套 NSFC 模板的共同样式，再回到 `packages/bensz-nsfc/` 修改公共包

## 参考文献和图片怎么放

### 参考文献

把 BibTeX 条目写入 [`projects/NSFC_Young/references/myexample.bib`](../projects/NSFC_Young/references/myexample.bib)，正文中用：

```latex
\cite{your-bib-key}
```

参考文献渲染入口是 [`projects/NSFC_Young/references/reference.tex`](../projects/NSFC_Young/references/reference.tex)，通常无需修改。

### 图片

图片建议放在 [`projects/NSFC_Young/figures/`](../projects/NSFC_Young/figures/)。

正文中可直接使用：

```latex
\begin{figure}[!th]
    \begin{center}
        \includegraphics[width=0.8\linewidth]{figures/example.png}
        \caption{示意图标题}
        \label{fig:example}
    \end{center}
\end{figure}
```

## 版本锁定与同步

如果你希望某个青年基金项目固定在一个模板版本上，推荐在项目目录写入 `.nsfc-version`：

```bash
cd projects/NSFC_Young
python ../../packages/bensz-nsfc/scripts/install.py pin --ref v3.5.1
```

之后常用命令是：

- `python ../../packages/bensz-nsfc/scripts/install.py sync`：按锁文件切换版本
- `python ../../packages/bensz-nsfc/scripts/install.py check`：检查当前版本是否与锁文件一致
- `python ../../packages/bensz-nsfc/scripts/install.py rollback`：回退到上一个激活版本

如果你是在单项目压缩包里工作，也可以先定位到已安装包根目录下的 `scripts/install.py` 再执行同类命令。

## 常见问题

### 1. 编译时报找不到 `bensz-nsfc-common.sty`

通常说明公共包还没有安装，或者 TeX 的搜索路径还没刷新。优先重新执行：

```bash
python packages/bensz-nsfc/scripts/install.py install --ref <tag>
```

然后再试一次构建命令。

### 2. 我只想写内容，不想碰样式

完全可以。对大多数用户来说，只需要改 `extraTex/*.tex`、`references/myexample.bib` 和 `figures/`。

### 3. 什么时候才需要改公共包

当问题会同时影响 `NSFC_General`、`NSFC_Local`、`NSFC_Young` 三套模板，例如共享标题样式、字体、BibTeX 资源、公共宏行为时，才应该修改 `packages/bensz-nsfc/`。

## 推荐的最短上手路径

如果你只是想尽快把青年基金模板跑起来，可以直接按下面顺序操作：

1. 安装公共包：`python packages/bensz-nsfc/scripts/install.py install --ref <tag>`
2. 编译青年基金示例：`python packages/bensz-nsfc/scripts/nsfc_project_tool.py build --project-dir projects/NSFC_Young`
3. 打开 `projects/NSFC_Young/extraTex/*.tex` 开始写正文
4. 需要参考文献时补 `projects/NSFC_Young/references/myexample.bib`
5. 每次修改后重新执行 `build`

## 延伸阅读

- [`docs/bensz-nsfc-design-principles.md`](./bensz-nsfc-design-principles.md)：解释公共包、profile、薄项目与官方脚本入口为何这样分层
- [`packages/bensz-nsfc/README.md`](../packages/bensz-nsfc/README.md)：包级结构、安装入口与资源策略速览
- [`projects/NSFC_Young/AGENTS.md`](../projects/NSFC_Young/AGENTS.md)：面向 AI 协作写作的项目级指令
