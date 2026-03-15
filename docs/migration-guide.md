# NSFC 模板迁移说明

## 目标

旧版本项目直接在 `extraTex/@config.tex` 里维护整套样式。重构后，项目入口仍然保留 `extraTex/@config.tex`，但职责改为“项目级参数面板 + 公共包加载入口”：公共样式实现收敛到 `bensz-nsfc`，项目侧只保留可调参数、说明注释以及覆盖钩子。安装、锁定与切换统一交给 `packages/bensz-nsfc/scripts/install.py`。
这些脚本跟随 `bensz-nsfc` 包一起安装，不要求在每个具体项目 zip 里重复携带。

## 最短迁移路径

1. 安装公共包

```bash
python packages/bensz-nsfc/scripts/install.py install --ref v3.5.1
```

开发当前仓库时可直接安装本地工作树：

```bash
python packages/bensz-nsfc/scripts/install.py install --source local --path packages/bensz-nsfc --ref local-dev
```

2. 将项目入口改为在 `main.tex` 顶部输入 `extraTex/@config.tex`，并在 `@config.tex` 内加载公共包

```latex
\input{extraTex/@config.tex}
```

对应关系：

- `NSFC_General` -> `\usepackage[type=general]{bensz-nsfc-common}`
- `NSFC_Local` -> `\usepackage[type=local]{bensz-nsfc-common}`
- `NSFC_Young` -> `\usepackage[type=young]{bensz-nsfc-common}`

3. 锁定项目版本

```bash
cd projects/NSFC_General
python ../../packages/bensz-nsfc/scripts/install.py pin --ref v3.5.1
```

这会生成 `.nsfc-version`，写入：

- `ref`
- `commit`
- `package_name`
- `package_version`
- `template_id`
- `template_version`

4. 编译项目

优先使用统一 Python 渲染器：

```bash
python packages/bensz-nsfc/scripts/nsfc_project_tool.py build --project-dir projects/NSFC_General
```

该入口会自动执行标准 4 步法：

```text
xelatex -> bibtex -> xelatex -> xelatex
```

## 常用命令

- `python packages/bensz-nsfc/scripts/install.py sync`：按 `.nsfc-version` 切换版本
- `python packages/bensz-nsfc/scripts/install.py check`：检查当前激活版本是否与项目锁一致
- `python packages/bensz-nsfc/scripts/install.py rollback`：回退到上一个激活版本
- `python packages/bensz-nsfc/scripts/install.py status`：查看当前激活版本、安装路径与缓存信息

## 验证结论

本次重构已对三套模板执行”4 步编译 + PDF 转 JPG 逐页视觉对比”。在官方安装路径下，`NSFC_General`、`NSFC_Local`、`NSFC_Young` 的输出 PDF 与重构前基线外观一致。

## 参考文献间距配置

三套 NSFC 模板（General/Local/Young）的参考文献间距参数采用“两层架构”管理：

- 基础默认值：在 `packages/bensz-nsfc/impl/bensz-nsfc-{general,local,young}.tex` 中定义
- 项目级默认值：在各项目 `extraTex/@config.tex` 中集中列出并通过项目级钩子覆盖
- 局部临时覆盖：如只想在参考文献区块做一次性微调，可在各项目 `references/reference.tex` 中用 `\setlength{...}{...}` 再次覆盖

默认值：

| 参数 | 默认值 |
|------|--------|
| `\NSFCBibTitleAboveSkip`（标题与上文） | `10pt` |
| `\NSFCBibTitleBelowSkip`（标题与条目） | `10pt` |
| `\NSFCBibItemSep`（条目间距） | `0pt` |
| `\NSFCBibTextWidth`（条目行宽） | `397.16727pt` |
