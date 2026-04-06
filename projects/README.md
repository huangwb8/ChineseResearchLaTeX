# projects 目录导览

`projects/` 目录存放的是各条产品线的示例项目与最薄的一层项目入口。它们面向的用户群体并不相同，建议先按你的写作场景选择版块，再进入具体项目。

补充说明：

- 每个示例项目都应自带一个与目录同名的 `*.code-workspace` 和 `.vscode/settings.json`
- 本地使用 VS Code 时，建议直接打开该 `*.code-workspace`，让 LaTeX Workshop 自动走项目内置的构建 wrapper，而不是手工拼 `xelatex`
- 当前固定配置默认通过 `texlua + scripts/latex_workshop_build.lua` 转调项目级 Python wrapper，按同一套模板兼容 macOS / Linux / Windows

## 国自然（NSFC）

适合人群：

- 正在撰写国家自然科学基金申请书正文的教师、医生、科研人员
- 需要在本地或 Overleaf 上快速得到与官方 Word 模板对齐 PDF 的用户

说明：

- 这一组项目共享 [`packages/bensz-nsfc/`](../packages/bensz-nsfc/) 公共包
- 三个项目的区别主要在于**申报类型不同**，不是写作工具链不同

| 项目 | 用途 | 适用场景 |
|------|------|----------|
| [`NSFC_General/`](./NSFC_General/) | 面上项目正文模板 | 已有一定研究基础，准备申报国自然面上项目 |
| [`NSFC_Local/`](./NSFC_Local/) | 地区科学基金项目正文模板 | 面向地区科学基金项目申报 |
| [`NSFC_Young/`](./NSFC_Young/) | 青年科学基金项目正文模板 | 面向青年科学基金项目申报 |

如果你是第一次接触本仓库，且当前任务是写国自然标书，通常从与你申报类型一致的 `NSFC_*` 项目进入即可。

## SCI 论文

适合人群：

- 正在撰写英文期刊论文的科研人员
- 希望维护一份 LaTeX 正文源文件，同时导出 PDF 和 Word 的用户

说明：

- 这一组项目共享 [`packages/bensz-paper/`](../packages/bensz-paper/) 公共包
- 当前已落地论文正文与投稿信两条可验证示例链路，重点展示“`extraTex/**/*.tex` 单一正文来源 + PDF/DOCX 双输出”

| 项目 | 用途 | 适用场景 |
|------|------|----------|
| [`paper-sci-01/`](./paper-sci-01/) | SCI 论文示例项目 | 写英文论文、投稿前排版、需要同时交付 `main.pdf` 与 `main.docx` |
| [`paper-coverletter-01/`](./paper-coverletter-01/) | 投稿信示例项目 | 已有 cover letter Word 稿件，想迁移到可维护的 LaTeX + DOCX 双输出模板 |

如果你的目标是期刊论文正文或投稿信，而不是基金申请书，请直接从对应的 `paper-*` 项目开始，不必进入 NSFC 项目。

## 毕业论文

适合人群：

- 正在撰写硕士或博士毕业论文的学生
- 需要对齐学校论文格式要求的导师、实验室或模板维护者

说明：

- 这一组项目共享 [`packages/bensz-thesis/`](../packages/bensz-thesis/) 公共包
- 当前示例项目按**学校 + 学位类型**区分，重点展示 PDF 输出与版式验收能力

| 项目 | 用途 | 适用场景 |
|------|------|----------|
| [`thesis-smu-master/`](./thesis-smu-master/) | 南方医科大学硕士论文示例项目 | 需要 SMU 硕士论文版式模板 |
| [`thesis-nju-master/`](./thesis-nju-master/) | 南京大学工程管理硕士论文示例项目 | 需要 NJU 工程管理硕士论文版式模板，且希望默认 `main.tex` 就是可编辑入口，同时保留公开基线验收文件 |
| [`thesis-sysu-doctor/`](./thesis-sysu-doctor/) | 中山大学博士论文示例项目 | 需要 SYSU 博士论文版式模板 |
| [`thesis-ucas-doctor/`](./thesis-ucas-doctor/) | 中国科学院大学博士论文示例项目 | 需要 UCAS 博士论文版式模板 |

如果你当前的核心需求是毕业论文排版，请优先进入与你学校和学位最接近的 thesis 项目。

## 简历（CV）

适合人群：

- 需要维护一份中英文双语学术简历的研究者、医生、学生或实验室成员
- 希望先用私有简历完成版式验收，再替换为公开演示内容的模板维护者

说明：

- 这一组项目共享 [`packages/bensz-cv/`](../packages/bensz-cv/) 公共包
- 当前示例项目重点展示“只读源样式复刻 → 像素级验收 → 去隐私公开示例”的完整链路

| 项目 | 用途 | 适用场景 |
|------|------|----------|
| [`cv-01/`](./cv-01/) | 中英文简历示例项目 | 写学术简历、个人资料页、媒体包式履历，或维护公开 CV 模板 |

如果你的目标是简历或个人资料页模板，请直接从 `cv-01/` 开始。

## 选型建议

- 写国自然标书：进入 `NSFC_General/`、`NSFC_Local/` 或 `NSFC_Young/`
- 写 SCI 论文正文：进入 `paper-sci-01/`
- 写投稿 cover letter：进入 `paper-coverletter-01/`
- 写毕业论文：进入与你学校和学位最接近的 `thesis-*` 项目（如 `thesis-smu-master/`、`thesis-nju-master/`、`thesis-sysu-doctor/`、`thesis-ucas-doctor/`）
- 写中英文简历：进入 `cv-01/`

若你的问题涉及共享样式、公共宏、构建脚本或安装逻辑，再回到 `packages/` 目录定位对应公共包。
