# bensz-paper

`bensz-paper` 是本仓库中面向 SCI / 期刊论文写作的公共包源码目录。

README 只说明公共包本身的职责、结构与官方入口；具体示例项目、演示正文和个性化模板差异，应写在对应项目文档中，而不是反向写回包文档。

## 包职责

- 提供论文模板的公共样式、profile 与兼容入口
- 提供 PDF / DOCX 联合构建所需的脚本入口
- 约定 `extraTex/**/*.tex` 作为正文单一真相来源，Markdown 仅在 DOCX 导出时临时生成
- 依赖 `bensz-fonts` 统一管理外置字体资源

## 目录说明

- `bensz-paper.sty`：新的公共入口包名
- `benszmanuscriptlatex.sty`：兼容旧名称的入口
- `bml-*.sty`：内部模块实现
- `../bensz-fonts/`：共享字体基础包；`bensz-paper` 安装时会作为强制依赖一并安装
- `profiles/`：模板 profile
- `scripts/manuscript_tool.py`：PDF + DOCX 统一构建工具
- `scripts/paper_project_tool.py`：面向仓库内论文项目的官方 wrapper
- `scripts/package/install.py`：本地安装脚本
- `scripts/package/build_tds_zip.py`：TDS ZIP 打包脚本

## 构建说明

- PDF 直接编译项目内的 `main.tex + extraTex/**/*.tex`
- DOCX 按 `main.tex` 中的 `\input{extraTex/...}` 顺序读取同一批 `.tex` 片段，运行时经 Pandoc 转成临时 Markdown 后导出 Word
- 构建后默认保留 `main.pdf`、`main.docx` 与 `.latex-cache/`，不再持久化正文 Markdown 中间稿

## 使用方式

在仓库中开发时，优先直接调用：

```bash
python packages/bensz-paper/scripts/paper_project_tool.py build --project-dir <project-dir>
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
