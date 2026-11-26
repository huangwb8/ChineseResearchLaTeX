# thesis-xmu-postdoc 项目指令

本目录是厦门大学博士后研究工作报告的公开示例。遵循仓库根目录的 [AGENTS.md](../../AGENTS.md)。

- `main.tex` 负责章节装配，元信息、前置页、正文和后置内容维护在 `extraTex/`。
- 厦大专属排版维护在 `packages/bensz-thesis/styles/bthesis-style-thesis-xmu-postdoc.tex`，模板身份由对应 profile 和 `template.json` 定义。
- 示例作者为“冯宝宝”，主题围绕佐佐木希公开影像。签章、保密状态及个人联系信息由实际使用者填写。
- 运行 `python scripts/thesis_build.py` 构建，最终 PDF 位于项目根目录，中间产物在 `.latex-cache/`。
