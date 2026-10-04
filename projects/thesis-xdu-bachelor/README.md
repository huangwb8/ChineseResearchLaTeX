# thesis-xdu-bachelor

西安电子科技大学本科毕业设计论文示例，使用 `NSFC_Young` 的佐佐木希主题构造虚构的职业发展与跨媒介形象研究，默认专业信息保留机电工程学院机械工程。示例主题用于展示排版，可按实际课题替换。学校版式由 `bensz-thesis` 的独立 profile 与固定的 XDUTS 6.2.7.2 本科文档类提供。

## 构建

完整仓库中运行：

```bash
python packages/bensz-thesis/scripts/thesis_project_tool.py build --project-dir projects/thesis-xdu-bachelor
```

首次使用新 profile，在完整仓库根目录安装本次源码，强制刷新可能已缓存的旧包：

```bash
python packages/bensz-thesis/scripts/package/install.py install --source local --path . --force
```

只打开本目录时，先完成上述安装，再运行：

```bash
python scripts/thesis_build.py
```

使用 XeLaTeX 与 Biber；建议 TeX Live / MacTeX 2024 或更新版本，并安装 `biblatex-gb7714-2015`（同时提供 GB/T 7714—2005 样式）。输出为 `main.pdf`，中间文件与 SyncTeX 保存在 `.latex-cache/`。VS Code 打开 `thesis-xdu-bachelor.code-workspace` 后，LaTeX Workshop 调用同一 Python 入口。

Overleaf 使用本项目的 Overleaf ZIP，选择 **XeLaTeX**，主文件为 `main.tex`。ZIP 内带固定本科类、校徽与共享字体，无需手工安装公共包，无需开启 shell escape。

## 修改论文

| 文件 | 内容 |
| --- | --- |
| `extraTex/meta.tex` | 题目、学院、专业、姓名、班级、学号、导师、关键词和材料路径 |
| `extraTex/front/abstract_zh.tex`、`abstract_en.tex` | 中英文摘要正文 |
| `extraTex/body/chapter-*.tex` | 正文；新增章节后在 `main.tex` 中加入 `\input` |
| `references/references.bib` | 文献数据库 |
| `figures/` | 复用自 `NSFC_Young` 的横向、纵向人物配图 |
| `extraTex/back/thanks.tex`、`appendix.tex` | 致谢、附录 |
| `extraTex/@config.tex` | 公共包选择、辅助宏包与页面选项 |

XDUTS 自动生成封面、中英文摘要、目录、致谢、参考文献和附录，不要重复输出这些页面。中文题目最多两行，用 `\\` 指定换行。校外毕业设计可在 `info` 中使用 `supv-ent` 和 `supv-school` 代替 `supervisor`。

默认按本科基线双面编排，章节从右页开始，允许相应空白页。若学院要求单面，可将 `main.tex` 中传给 `ctexbook` 的选项改为 `oneside,openany`；上游双面页眉在单面模式下会产生 fancyhdr 提示。中文正文用共享宋体文件，英文用 Times New Roman，标题用共享黑体文件。

## 引用与资料边界

按 issue 指定采用 GB/T 7714—2005 顺序编码制：`\cite{key}` 为方括号上标，`\parencite{key}` 为正文内引用；书目按首次引用顺序排列，超过三位作者列前三位并追加“等”或“et al.”。请录入完整文献标题和期刊名。示例文献用于理论视角与附录公式展示，不能代替真实论文的文献要求。

本项目源自 [issue #54](https://github.com/huangwb8/ChineseResearchLaTeX/issues/54)。两份 Word 附件均为研究生资料，未将硕博文献数量、详细摘要和声明套入本科模板。当前本科版式依据为 XDUTS；学院最新本科工作手册和声明页尚未随 issue 提供，提交前应按学院实际要求核对。来源与取舍见 [docs/specification.md](docs/specification.md)。

正文以佐佐木希为主题，展示五阶段职业轨迹、两张人物图片、分析流程图、模拟情感得分表和编码一致性公式。时间线、事件、评论样本与数值均为虚构教学设定，不构成真实人物的履历或舆情结论；配图复用自 `projects/NSFC_Young/figures/`，不参与时间线判定。附录保留单自由度机械模型、运动方程和参数表。请将示例替换为自己的研究、设计与验证材料。
