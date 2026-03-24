# bensz-thesis

`bensz-thesis` 是本仓库中面向毕业论文模板的公共包源码目录。

当前已落地三条示例链路：

- 公共包：[`packages/bensz-thesis`](/Volumes/2T01/Github/ChineseResearchLaTeX/packages/bensz-thesis)
- 示例项目：[`projects/thesis-smu-master`](/Volumes/2T01/Github/ChineseResearchLaTeX/projects/thesis-smu-master)
- 示例项目：[`projects/thesis-sysu-doctor`](/Volumes/2T01/Github/ChineseResearchLaTeX/projects/thesis-sysu-doctor)
- 示例项目：[`projects/thesis-ucas-resource-env`](/Volumes/2T01/Github/ChineseResearchLaTeX/projects/thesis-ucas-resource-env)
- 官方构建入口：`python packages/bensz-thesis/scripts/thesis_project_tool.py build --project-dir <project-dir>`

## 目录说明

- `bensz-thesis.sty`：公共入口包
- `bthesis-core.sty`：profile 与样式装配入口
- `profiles/`：不同论文模板的 profile
- `styles/`：不同论文模板的稳定样式实现
- `../bensz-fonts/`：共享字体基础包；`bensz-thesis` 安装时会作为强制依赖一并安装
- `scripts/thesis_project_tool.py`：PDF 构建 / 清理 / 像素级比较入口，支持 `main.tex + extraTex/` 与 `template.json + Thesis.tex + .latexmkrc` 两类 thesis 项目布局
- `scripts/package/install.py`：本地安装脚本
- `scripts/package/build_tds_zip.py`：TDS ZIP 打包脚本

## 使用方式

在仓库中开发时，优先直接调用：

```bash
python packages/bensz-thesis/scripts/thesis_project_tool.py build --project-dir projects/thesis-smu-master
python packages/bensz-thesis/scripts/thesis_project_tool.py build --project-dir projects/thesis-ucas-resource-env
```

如需安装到本地 `TEXMFHOME`：

```bash
python packages/bensz-thesis/scripts/package/install.py
```
