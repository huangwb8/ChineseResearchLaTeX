# paper-sci-01 - 项目指令

本目录是 `bensz-paper` 的 SCI 论文示例项目。AI 在这里的核心任务是维护公开可分享的论文示例与构建链路，不得引入未发表论文正文。

## 写作与修改边界

- 正文单一真相来源在 `artifacts/source/`
- `main.tex` 只负责装配结构，不应手工堆叠正文内容
- `.latex-cache/extraTex/` 是构建产物，不要手工编辑
- 不要把任何私有论文正文复制到本项目

## 目录职责

- `artifacts/source/front/abstract.md`：摘要
- `artifacts/source/body/*.md`：Introduction / Methods / Results / Discussion / Conclusion
- `artifacts/source/back/`：附加说明、图注、补充材料
- `references/meta.yaml`：题名、作者、单位、通讯作者
- `references/refs.bib`：参考文献
- `scripts/paper_build.py`：项目级构建入口

## 编译说明

完整仓库模式：

```bash
python packages/bensz-paper/scripts/paper_project_tool.py build --project-dir projects/paper-sci-01
```

项目目录模式：

```bash
python scripts/paper_build.py
```

## 工程原则

- 只修改与当前任务相关的文件
- 示例正文必须保持公开可分享
- 优先维护 `artifacts/source/`，避免 Markdown 与 LaTeX 双份正文漂移
- 变更构建链路或项目指令后，同步检查根级 `README.md`、`AGENTS.md` 与 `CHANGELOG.md`

## 默认语言

- 与用户沟通：简体中文
- 论文正文：英文
