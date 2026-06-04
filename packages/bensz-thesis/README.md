# bensz-thesis

`bensz-thesis` 是本仓库中面向毕业论文模板的公共包源码目录。

README 只描述公共包本身的职责、稳定入口和目录结构；具体学校、学位、示例正文与演示资产，应维护在各自的项目目录中。

## 包职责

- 提供毕业论文模板的公共入口包、profile 与样式装配逻辑
- 提供 PDF 构建、DOCX 初稿导出、缓存清理与像素级比较脚本入口
- 依赖 `bensz-fonts` 统一管理共享字体资源
- 当前已注册独立模板：`thesis-smu-master`、`thesis-nju-master`、`thesis-just-bachelor`、`thesis-ahnu-master`、`thesis-hit-doctor`、`thesis-jlau-master`、`thesis-smu-postdoc`、`thesis-sysu-doctor`、`thesis-ucas-doctor`

## 目录说明

- `bensz-thesis.sty`：公共入口包
- `bthesis-core.sty`：profile 与样式装配入口
- `profiles/`：不同论文模板的 profile
- `styles/`：不同论文模板的稳定样式实现
- `../bensz-fonts/`：共享字体基础包；`bensz-thesis` 安装时会作为强制依赖一并安装
- `scripts/thesis_project_tool.py`：PDF 构建 / DOCX 导出 / 清理 / 像素级比较入口
- `scripts/thesis_docx_tool.py`：LaTeX 源到可编辑 Word 初稿的通用导出实现
- `scripts/package/install.py`：本地安装脚本
- `scripts/package/build_tds_zip.py`：TDS ZIP 打包脚本

## 使用方式

在仓库中开发时，优先直接调用：

```bash
python packages/bensz-thesis/scripts/thesis_project_tool.py build --project-dir <project-dir>
```

如需从同一份 LaTeX 源导出可编辑 Word 初稿：

```bash
python packages/bensz-thesis/scripts/thesis_project_tool.py docx --project-dir <project-dir>
```

DOCX 导出默认生成 `<project-dir>/main.docx`，中间 Markdown 与质量报告保存在 `<project-dir>/.latex-cache/docx/`。该功能定位为“可编辑 Word draft”：标题、正文、列表、图片、基础公式和基础引用会尽量保留；复杂表格、算法、代码块、TikZ 或 PDF 专属构造会写入占位符，并在质量报告中提示人工复核。若学校提供官方 Word 模板，建议显式传入：

```bash
python packages/bensz-thesis/scripts/thesis_project_tool.py docx \
  --project-dir <project-dir> \
  --reference-doc <path-to-reference.docx>
```

如需安装到本地 `TEXMFHOME`：

```bash
python packages/bensz-thesis/scripts/package/install.py
python packages/bensz-thesis/scripts/package/install.py install --ref main
python packages/bensz-thesis/scripts/package/install.py rollback
python packages/bensz-thesis/scripts/package/install.py check
```
