# VS Code 固定配置

本目录托管 `projects/` 下各示例项目统一复用的 VS Code / LaTeX Workshop 固定配置，避免不同项目各自手工维护后发生漂移。

## 文件说明

- `project.code-workspace.json`：所有项目共用的 `.code-workspace` 模板
- `nsfc.settings.json`：`projects/NSFC_*` 的 `.vscode/settings.json` 模板
- `paper.settings.json`：`projects/paper-*` 的 `.vscode/settings.json` 模板
- `thesis.settings.json`：`projects/thesis-*` 的 `.vscode/settings.json` 模板
- `cv.settings.json`：`projects/cv-*` 的 `.vscode/settings.json` 模板
- `latex_workshop_build.lua`：由 `texlua` 调起、负责在 macOS / Linux / Windows 上寻找可用 Python 解释器并转调项目级 `scripts/*_build.py` 的通用 launcher

## 同步方式

在仓库根目录执行：

```bash
python scripts/sync_vscode_configs.py
```

只检查项目配置是否与模板一致：

```bash
python scripts/sync_vscode_configs.py --check
```

原则上应先修改本目录模板，再同步到具体项目；不要只改单个 `projects/*/.vscode/settings.json`、单个 `*.code-workspace` 或单个项目里的 `scripts/latex_workshop_build.lua`，否则后续容易再次漂移。

当前模板默认不再依赖 `bash -lc "python3 ..."` 这类偏 Unix 的写法，而是让 LaTeX Workshop 调用 `texlua` 执行项目内同步下发的 `scripts/latex_workshop_build.lua`。这样在 TeX 与 Python 均已安装的前提下，macOS / Linux / Windows 都可以复用同一份 `.vscode/settings.json`。
