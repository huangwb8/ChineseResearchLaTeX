# bensz-paper

`bensz-paper` 是本仓库中面向 SCI / 期刊论文写作的公共包源码目录，也承载投稿信等轻量英文科研文档的共享版式与构建链。

README 只说明公共包本身的职责、结构与官方入口；具体示例项目、演示正文和个性化模板差异，应写在对应项目文档中，而不是反向写回包文档。

## 包职责

- 提供论文模板的公共样式、profile 与兼容入口
- 提供 cover letter 等轻量投稿文档可复用的 profile
- 提供 PDF / DOCX 联合构建所需的脚本入口
- 约定 `extraTex/**/*.tex` 作为正文单一真相来源，Markdown 仅在 DOCX 导出时临时生成
- 依赖 `bensz-fonts` 统一管理外置字体资源

## 目录说明

- `bensz-paper.sty`：新的公共入口包名
- `benszmanuscriptlatex.sty`：兼容旧名称的入口
- `bml-*.sty`：内部模块实现
- `../bensz-fonts/`：共享字体基础包；`bensz-paper` 安装时会作为强制依赖一并安装
- `profiles/`：模板 profile
- `scripts/manuscript_tool.py`：PDF + DOCX 统一构建工具，并提供可见字数统计能力
- `scripts/paper_project_tool.py`：面向仓库内论文项目的官方 wrapper
- `scripts/package/install.py`：本地安装脚本
- `scripts/package/build_tds_zip.py`：TDS ZIP 打包脚本

## 构建说明

- PDF 直接编译项目内的 `main.tex + extraTex/**/*.tex`
- DOCX 按 `main.tex` 中的 `\input{extraTex/...}` 顺序读取同一批 `.tex` 片段，运行时经 Pandoc 转成临时 Markdown 后导出 Word
- DOCX 导出会将 LaTeX `\textsuperscript{...}` 规范转换为 Pandoc 原生上标语法，避免作者单位编号、共同一作和通讯标记在 Word 中失效
- 当项目不声明参考文献命令时，构建链会自动跳过 `biber` 与 citeproc，支持 cover letter 等无参考文献文档保持同一套 PDF / DOCX 工作流
- `bml-bibliography.sty` 现同时兼容默认 `gb7714-2015` 与 `vancouver` 两条 biblatex 链路；前者继续保留中文科技论文式参数，后者则按 Vancouver/JITC 口径保留 `doi` 并仅在缺 DOI 时回退到 URL
- 当项目在 `main.tex` 中显式写出 `\section{References}` + `\printbibliography[heading=none]` 时，PDF 书签会稳定出现 `References`
- DOCX 后处理现会优先读取当前论文 profile 的章节字号、参考文献字号、行距与悬挂缩进参数，再对最终 Word 文档做归一化，减少 `reference.docx` 与 PDF profile 分叉导致的样式漂移
- `paper-sci-01` 现已切到更接近 `CCS/paper` 的 Vancouver/JITC 参考文献口径：PDF 端使用 `biblatex-vancouver`，DOCX 端使用对应 CSL，正文引用与文末条目会同步收敛到同一套编号风格
- DOCX 后处理会为 Pandoc 默认生成、且尚无显式边框定义的 `Normal Table` 自动补上横向边框，改善 key resources table 等投稿场景下的可读性，同时保留已有自定义表格边框
- DOCX 后处理会把 `References` 统一为与正文一级章节一致的 `Heading 1`，并自动重排到图注节之前，同时兼容 `Figure legends` / `Figure titles and legends` 与 `Supplementary materials` / `Supplemental information titles and legends` 这两组尾部标题命名
- DOCX 构建会先经 HTML5 + MathML 中间态再写入 Word，确保 LaTeX 数学尽量落成原生 OMML 公式对象，而不是残留为源码文本
- 构建后默认保留 `main.pdf`、`main.docx` 与 `.latex-cache/`，不再持久化正文 Markdown 中间稿
- 字数统计支持直接传入一个或多个 `.tex`；若传入 `main.tex`，会递归跟随 `\input` / `\include` 链，并按“渲染后可见文本”统计英文词与 CJK 字符，自动忽略 LaTeX 命令名、引用 keys 与数学公式源码

## 使用方式

在仓库中开发时，优先直接调用：

```bash
python packages/bensz-paper/scripts/paper_project_tool.py build --project-dir <project-dir>
python packages/bensz-paper/scripts/paper_project_tool.py count-words <tex-1> [<tex-2> ...]
```

如需安装到本地 `TEXMFHOME`：

```bash
python packages/bensz-paper/scripts/package/install.py
python packages/bensz-paper/scripts/package/install.py install --ref main
python packages/bensz-paper/scripts/package/install.py rollback
python packages/bensz-paper/scripts/package/install.py check
```

安装后可通过以下方式检查：

```bash
kpsewhich bensz-paper.sty
bpaper --version
```
