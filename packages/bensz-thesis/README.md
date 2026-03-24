# bensz-thesis

`bensz-thesis` 是本仓库中面向毕业论文模板的公共包源码目录。

README 只描述公共包本身的职责、稳定入口和目录结构；具体学校、学位、示例正文与演示资产，应维护在各自的项目目录中。

## 包职责

- 提供毕业论文模板的公共入口包、profile 与样式装配逻辑
- 提供 PDF 构建、缓存清理与像素级比较脚本入口
- 依赖 `bensz-fonts` 统一管理共享字体资源

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
python packages/bensz-thesis/scripts/thesis_project_tool.py build --project-dir <project-dir>
```

如需安装到本地 `TEXMFHOME`：

```bash
python packages/bensz-thesis/scripts/package/install.py
python packages/bensz-thesis/scripts/package/install.py install --ref main
python packages/bensz-thesis/scripts/package/install.py rollback
python packages/bensz-thesis/scripts/package/install.py check
```
