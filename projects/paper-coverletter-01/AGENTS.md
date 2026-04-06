# paper-coverletter-01 - 项目指令

本目录是 `bensz-paper` 的 cover letter 示例项目。AI 在这里的核心任务是维护一个可公开分享、已匿名化、可稳定导出 PDF / DOCX 的投稿信模板，不得写回任何真实未发表稿件信息。

## 写作与修改边界

- 正文单一真相来源在 `extraTex/front/metadata.tex` 与 `extraTex/body/letter.tex`
- `main.tex` 只负责装配结构与载入 `paper-coverletter-01` profile，不应手工堆叠正文内容
- 当前模板示例中的题名、期刊、作者与单位均为匿名化占位内容；如需替换，应继续保持公开可分享口径
- 不要为 cover letter 新增独立公共包；优先复用 `packages/bensz-paper/`

## 目录职责

- `extraTex/front/metadata.tex`：日期、期刊、通讯作者等可复用元信息
- `extraTex/body/letter.tex`：Cover letter 正文
- `artifacts/reference.docx`：DOCX 样式参考模板
- `scripts/paper_build.py`：项目级构建入口

## 编译说明

完整仓库模式：

```bash
python packages/bensz-paper/scripts/paper_project_tool.py build --project-dir projects/paper-coverletter-01
```

项目目录模式：

```bash
python scripts/paper_build.py
```

## 工程原则

- 只修改与当前任务直接相关的文件
- 优先维护 `extraTex/**/*.tex`，避免重新引入持久化 Markdown 正文副本
- 保持模板匿名化、可公开分享、可稳定构建
- 变更构建链路或项目指令后，同步检查根级 `README.md`、`AGENTS.md` 与 `CHANGELOG.md`

## 默认语言

- 与用户沟通：简体中文
- 模板正文：英文
