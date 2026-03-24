# bensz-cv

`bensz-cv` 是本仓库中面向中英文学术简历的公共包源码目录。

README 只描述公共包能力、结构和官方入口；具体示例项目、公开演示内容与项目级素材，应维护在对应项目目录中。

## 包职责

- 提供中英文简历模板的公共入口类与兼容入口
- 提供中英文字体、图标与 profile 组织方式
- 提供 PDF 构建、缓存清理与像素级比较脚本入口
- 依赖 `bensz-fonts` 统一管理共享字体资源

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
python packages/bensz-cv/scripts/cv_project_tool.py build --project-dir <project-dir> --variant all
```

如需与基线 PDF 做像素级比较：

```bash
python packages/bensz-cv/scripts/cv_project_tool.py compare --project-dir <project-dir> --variant <zh|en> --baseline-pdf <baseline.pdf>
```

如需安装到本地 `TEXMFHOME`：

```bash
python packages/bensz-cv/scripts/package/install.py
python packages/bensz-cv/scripts/package/install.py install --ref main
python packages/bensz-cv/scripts/package/install.py rollback
python packages/bensz-cv/scripts/package/install.py check
```

安装后可通过以下方式检查：

```bash
kpsewhich bensz-cv.cls
```
