# bensz-nsfc-common

`bensz-nsfc-common` 是 `ChineseResearchLaTeX` 为 NSFC 模板抽出的公共包源码。它把 `NSFC_General / NSFC_Local / NSFC_Young` 统一收敛到一个安装入口，并通过 `type=general|local|young` 切换模板类型。

## 结构

- `bensz-nsfc-common.sty`：薄入口
- `bensz-nsfc-core.sty`：选项解析、profile 元信息与实现分发
- `assets/`：共享字体与 BibTeX 样式资源，供 `NSFC_General / NSFC_Local / NSFC_Young` 统一复用
- `profiles/`：不同项目类型的版本与标识元信息
- `impl/`：当前运行时使用的稳定实现，直接承载已通过像素级回归验证的排版逻辑
- `scripts/`：围绕 `bensz-nsfc` 的安装、构建、校验与 TDS 打包脚本
- `bensz-nsfc-layout.sty` / `bensz-nsfc-typography.sty` / `bensz-nsfc-headings.sty` / `bensz-nsfc-bibliography.sty`：后续进一步细化抽象时保留的模块化骨架

## 接入方式

项目层仍保持 `main.tex -> extraTex/@config.tex` 单一路径。`@config.tex` 现在只保留一行入口：

```latex
\usepackage[type=general]{bensz-nsfc-common}
```

## 安装与版本管理

官方安装入口统一为：

```bash
python packages/bensz-nsfc/scripts/install.py install --ref v3.5.1
python packages/bensz-nsfc/scripts/install.py pin --ref v3.5.1
python packages/bensz-nsfc/scripts/install.py sync
```

仓库开发时推荐先把当前工作树安装到本机 `TEXMFHOME`：

```bash
python packages/bensz-nsfc/scripts/install.py install --source local --path packages/bensz-nsfc --ref local-dev
```

支持的核心能力：

- 按 Git `tag / branch / commit` 安装
- 本地缓存按解析后的 commit 去重
- `.nsfc-version` 锁文件记录 `ref + commit + package_version + template_version`
- 一键 `rollback` 回退到上一个激活版本

## 资源策略

- 字体与 `bst` 统一托管在 `assets/fonts/`、`assets/bibtex-style/`
- 三套项目默认优先使用公共包内共享资源；若用户保留了历史项目内 `./fonts/` 或 `bibtex-style/`，仍可作为兼容兜底
- `examples/basic-usage.tex` 与 `examples/basic-bibliography.tex` 都直接走公共包内共享资源，方便 `validate_package.py` 做 smoke test
