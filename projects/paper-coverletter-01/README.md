# paper-coverletter-01

`paper-coverletter-01` 是基于 `bensz-paper` 构建的投稿 cover letter 示例项目，面向“已存在 Word 信件样稿，希望迁移到可维护的 LaTeX + DOCX 双输出模板”的场景。

它的核心特点是：

- 依赖公共包 [`packages/bensz-paper`](/Volumes/2T01/Github/ChineseResearchLaTeX/packages/bensz-paper)
- 不新增专门 cover letter 公共包，而是在 `bensz-paper` 内增加轻量 profile
- 正文只维护在 `extraTex/**/*.tex`
- 示例内容已完成匿名化处理，不包含真实未发表稿件题名、作者或单位
- 同一份正文可同时输出 `main.pdf` 与 `main.docx`
- 当前示例默认使用 `Feng BaoBao` 作为通讯作者占位名

## 内容来源说明

本项目源自一份真实 cover letter 的结构与段落组织方式，但示例正文已重写为可公开分享的匿名化版本：

- 稿件题名改为泛化示例标题
- 作者与机构信息改为模板占位内容
- 保留 cover letter 常见结构：日期、收件人、投稿说明、工作亮点、期刊契合度、投稿声明、落款

因此，这里的正文仅用于模板演示，不对应任何公开或未公开的真实稿件。

## 构建

仓库内开发时，推荐直接执行：

```bash
python packages/bensz-paper/scripts/paper_project_tool.py build --project-dir projects/paper-coverletter-01
```

若只打开了项目子目录，可执行：

```bash
python scripts/paper_build.py
```

构建成功后会产出：

- `main.pdf`
- `main.docx`
- `.latex-cache/`

当前项目不依赖参考文献文件；`bensz-paper` 的构建脚本会自动识别这是一个“无参考文献的轻量文档”，跳过 `biber` 与 citeproc 步骤，同时保留 PDF / DOCX 双输出链路。

## 结构

- `main.tex`：LaTeX 主入口
- `extraTex/front/metadata.tex`：日期、收件人、通讯作者等集中配置
- `extraTex/body/letter.tex`：Cover letter 正文
- `artifacts/reference.docx`：DOCX 样式模板
- `scripts/paper_build.py`：项目级构建 wrapper
