# thesis-xdu-bachelor 项目指令

本目录是西安电子科技大学本科毕业设计论文公开示例，遵循仓库根 `AGENTS.md`。

- `main.tex` 只装配正文；XDUTS 自动生成前后置材料，避免重复输出封面、目录和文献列表。
- 元数据在 `extraTex/meta.tex`，正文在 `extraTex/front/`、`body/`、`back/`。
- 学校样式在公共包独立 style；`packages/bensz-thesis/styles/xdu/` 是固定上游源码，不在项目层复制或修改文档类。
- 研究生附件不能作为本科专用格式要求，依据记录在 `docs/specification.md`。
- 使用官方 wrapper：`python packages/bensz-thesis/scripts/thesis_project_tool.py build --project-dir projects/thesis-xdu-bachelor`；独立目录运行 `python scripts/thesis_build.py`。
- 中间文件放 `.latex-cache/`，公开产物为 `main.pdf`；不放入原始附件、截图或个人论文材料。
