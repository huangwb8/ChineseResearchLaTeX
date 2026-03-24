# 开发者模板标准总览

本目录面向两类读者：

- 想为仓库贡献新模板或维护现有模板的人类开发者
- 需要理解“标准模板长什么样”的 AI Agent

这里的标准不是抽象愿景，而是根据当前 `projects/` 与 `packages/` 的真实源码、真实构建入口和真实目录结构整理出的现行约定。

## 当前产品线

| 产品线 | 当前标准项目 | 公共包 | 主要产物 |
|------|------|------|------|
| NSFC 标书 | `projects/NSFC_General`、`projects/NSFC_Local`、`projects/NSFC_Young` | `packages/bensz-nsfc/` | `main.pdf` |
| SCI 论文 | `projects/paper-sci-01` | `packages/bensz-paper/` | `main.pdf`、`main.docx` |
| 毕业论文 | `projects/thesis-smu-master`、`projects/thesis-sysu-doctor`、`projects/thesis-ucas-doctor` | `packages/bensz-thesis/` | `main.pdf` |
| 学术简历 | `projects/cv-01` | `packages/bensz-cv/` | `main-zh.pdf`、`main-en.pdf` |

## 共享标准

无论贡献哪一类模板，都优先遵守下面这些总规则。

### 1. 项目是薄封装，公共包才是样式主线

- `packages/` 负责共享样式、共享字体接入、profile、构建脚本、安装脚本和稳定实现。
- `projects/` 负责示例正文、项目级最薄入口、公开可分享素材和项目级 wrapper。
- 如果一个改动会影响同产品线多个项目，优先改 `packages/`，不要把同一份逻辑复制回 `projects/`。

### 2. 构建必须走官方 Python wrapper

- NSFC：`python packages/bensz-nsfc/scripts/nsfc_project_tool.py build --project-dir <project-dir>`
- SCI：`python packages/bensz-paper/scripts/paper_project_tool.py build --project-dir <project-dir>`
- Thesis：`python packages/bensz-thesis/scripts/thesis_project_tool.py build --project-dir <project-dir>`
- CV：`python packages/bensz-cv/scripts/cv_project_tool.py build --project-dir <project-dir> --variant all`

项目目录内还应保留一个最薄的 `scripts/*_build.py` wrapper，方便“只打开单个项目目录”时调用已安装公共包。

### 3. VS Code 工程文件是标准模板的一部分

每个标准项目都应包含：

- 一个与目录同名的 `*.code-workspace`
- `.vscode/settings.json`
- `scripts/latex_workshop_build.lua`

这些文件不是装饰，而是 LaTeX Workshop 通过 `texlua -> 项目级 Python wrapper` 走统一构建链路的基础设施。新增或调整项目后，应运行：

```bash
python scripts/sync_vscode_configs.py
```

### 4. 中间文件进入 `.latex-cache/`

- 根目录尽量只保留最终交付物，例如 `main.pdf`、`main.docx`、`main-zh.pdf`
- `.aux`、`.log`、`.bbl`、`.synctex.gz` 等中间文件应进入 `.latex-cache/`
- 这也是 VS Code、Release 打包和像素级回归链路的默认假设

### 5. 公共示例必须可公开

- `projects/` 下的示例正文、头像、图表、参考文献和附录都应可公开分享
- 不要把私有正文、真实身份信息、私有头像、私有 baseline 对比图重新留在公开项目里

### 6. 先判断修改层级，再动手

优先回答这几个问题：

1. 这是共享样式问题，还是单个项目内容问题？
2. 这是包级 profile/style 问题，还是项目级入口文件问题？
3. 这是构建脚本问题，还是示例内容问题？
4. 这是当前仓库已有主线，还是尚未落地的新能力？

## 分类型标准

- [NSFC 模板标准](./nsfc-template-standard.md)
- [SCI 论文模板标准](./paper-template-standard.md)
- [毕业论文模板标准](./thesis-template-standard.md)
- [学术简历模板标准](./cv-template-standard.md)

## 贡献前自检清单

在提交模板类改动前，至少自检以下几点：

1. 我改的是对的层：`packages/` 还是 `projects/`
2. 项目入口文件名、wrapper、VS Code 文件是否齐全
3. 是否仍然通过官方构建入口
4. 新增内容是否是公开可分享的
5. 是否把共享逻辑错误地下沉到了单个项目
6. 如涉及新 thesis 项目，是否补齐 `template.json`
7. 如涉及 README、开发者口径或流程变化，是否同步更新文档与 `CHANGELOG.md`
