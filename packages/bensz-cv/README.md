# bensz-cv

`bensz-cv` 是本仓库中面向中英文学术简历的公共包源码目录。

当前首个模板链路是 `cv-01`，定位为：

- 公共包：[`packages/bensz-cv`](/Volumes/2T01/Github/ChineseResearchLaTeX/packages/bensz-cv)
- 示例项目：[`projects/cv-01`](/Volumes/2T01/Github/ChineseResearchLaTeX/projects/cv-01)
- 官方构建入口：`python packages/bensz-cv/scripts/cv_project_tool.py build --project-dir projects/cv-01 --variant all`

## 目录说明

- `bensz-cv.cls`：公共入口类
- `resume.cls`：源样式实现与兼容入口
- `fontawesome.sty`、`zh_CN-*.sty`、`Noto*.sty`：字体与中英文支持
- `../bensz-fonts/`：共享字体基础包；`bensz-cv` 安装时会作为强制依赖一并安装
- `profiles/`：示例 profile
- `scripts/cv_project_tool.py`：PDF 构建 / 清理 / 像素级比较入口
- `scripts/package/install.py`：本地安装脚本
- `scripts/package/build_tds_zip.py`：TDS ZIP 打包脚本

## 使用方式

在仓库中开发时，优先直接调用：

```bash
python packages/bensz-cv/scripts/cv_project_tool.py build --project-dir projects/cv-01 --variant all
```

如需与基线 PDF 做像素级比较：

```bash
python packages/bensz-cv/scripts/cv_project_tool.py compare --project-dir projects/cv-01 --variant zh --baseline-pdf <baseline.pdf>
```

如需安装到本地 `TEXMFHOME`：

```bash
python packages/bensz-cv/scripts/package/install.py
```

安装后可通过以下方式检查：

```bash
kpsewhich bensz-cv.cls
```
