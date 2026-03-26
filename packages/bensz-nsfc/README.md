# bensz-nsfc-common

`bensz-nsfc-common` 是 `ChineseResearchLaTeX` 为 NSFC 模板抽出的公共包源码。它将不同 NSFC 项目类型收敛到统一安装入口，并通过 `type=general|local|young` 切换模板类型。

README 只描述公共包自身的结构、入口与资源策略；具体示例项目、正文内容与项目差异，应维护在对应项目目录中。

## 结构

- `bensz-nsfc-common.sty`：薄入口
- `bensz-nsfc-core.sty`：选项解析、profile 元信息与实现分发
- `assets/`：共享 BibTeX 样式资源
- `profiles/`：不同项目类型的版本与标识元信息
- `templates/`：不同项目类型的稳定模板实现，直接承载已通过像素级回归验证的排版逻辑
- `scripts/`：围绕 `bensz-nsfc` 的安装、构建、校验与 TDS 打包脚本
- `bensz-nsfc-layout.sty` / `bensz-nsfc-typography.sty` / `bensz-nsfc-headings.sty` / `bensz-nsfc-bibliography.sty`：后续进一步细化抽象时保留的模块化骨架
- `../bensz-fonts/`：共享字体基础包；`bensz-nsfc` 安装时会作为强制依赖一并安装

## 接入方式

项目层仍保持 `main.tex -> extraTex/@config.tex` 单一路径。`@config.tex` 现在只保留一行入口：

```latex
\usepackage[type=general]{bensz-nsfc-common}
```

## 安装与版本管理

官方安装入口统一为：

```bash
python packages/bensz-nsfc/scripts/install.py install --ref v3.5.1
python packages/bensz-nsfc/scripts/install.py install --ref v3.5.1 --mirror gitee
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

- 字体统一托管在 `packages/bensz-fonts/fonts/`，`bensz-nsfc` 通过 `bensz-fonts` 提供的统一 API 引用字体
- `bst` 统一托管在 `assets/bibtex-style/`
- 各 NSFC 项目默认优先使用公共包内共享资源；若用户保留了历史项目内 `./fonts/` 或 `bibtex-style/`，仍可作为兼容兜底
- `examples/basic-usage.tex` 与 `examples/basic-bibliography.tex` 都直接走公共包内共享资源，方便 `validate_package.py` 做 smoke test
- Overleaf Release 包会将 `bensz-nsfc` 的最小运行时裁剪后注入项目根目录下的 `styles/`，并只保留当前项目对应的 `profiles/` 与 `templates/`，避免不同 NSFC 模板之间互相混入
