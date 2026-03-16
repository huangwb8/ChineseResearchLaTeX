# bensz-paper

`bensz-paper` 是本仓库中面向 SCI/期刊论文写作的公共包源码目录。

当前已落地的首个模板是 `paper-sci-01`，定位为：

- 公共包：[`packages/bensz-paper`](/Volumes/2T01/Github/ChineseResearchLaTeX/packages/bensz-paper)
- 示例项目：[`projects/paper-sci-01`](/Volumes/2T01/Github/ChineseResearchLaTeX/projects/paper-sci-01)
- 官方构建入口：`python packages/bensz-paper/scripts/paper_project_tool.py build --project-dir projects/paper-sci-01`

## 目录说明

- `bensz-paper.sty`：新的公共入口包名
- `benszmanuscriptlatex.sty`：兼容旧名称的入口
- `bml-*.sty`：内部模块实现
- `../bensz-fonts/`：共享字体基础包；`bensz-paper` 安装时会作为强制依赖一并安装
- `profiles/`：模板 profile
- `scripts/manuscript_tool.py`：PDF + DOCX 统一构建工具
- `scripts/paper_project_tool.py`：面向仓库工作流的官方 wrapper
- `scripts/package/install.py`：本地安装脚本
- `scripts/package/build_tds_zip.py`：TDS ZIP 打包脚本

## 使用方式

在仓库中开发时，优先直接调用：

```bash
python packages/bensz-paper/scripts/paper_project_tool.py build --project-dir projects/paper-sci-01
```

如需安装到本地 `TEXMFHOME`：

```bash
python packages/bensz-paper/scripts/package/install.py
```

安装后可通过以下方式检查：

```bash
kpsewhich bensz-paper.sty
bpaper --version
```
