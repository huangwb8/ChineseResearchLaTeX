# 产品线判定与初始化规则

本文件把 `make-latex-model` 的产品线判定、初始化标记与官方构建入口从 `SKILL.md` 中拆出，避免核心工作文档继续膨胀。

## 单一真相来源

- 机器可读规则以 [`config.yaml`](../config.yaml) 中的 `product_line_rules`、`official_build_commands`、`baseline.preferred_candidates` 为准。
- 本文件负责给 AI 和维护者解释“为什么这样判定”，不重复承载脚本细节。

## 当前规则

| 产品线 | 目录/名称识别 | 初始化标记 | 官方验证命令 |
|------|------|------|------|
| `nsfc` | `projects/NSFC_*` | `main.tex` + `extraTex/@config.tex` | `python packages/bensz-nsfc/scripts/nsfc_project_tool.py build --project-dir <project>` |
| `paper` | `projects/paper-*` | `main.tex` + `extraTex/` | `python packages/bensz-paper/scripts/paper_project_tool.py build --project-dir <project>` |
| `thesis` | `projects/thesis-*` | `main.tex` + `template.json` | `python packages/bensz-thesis/scripts/thesis_project_tool.py build --project-dir <project>` |
| `cv` | `projects/cv-*` | `main-zh.tex` + `main-en.tex` | `python packages/bensz-cv/scripts/cv_project_tool.py build --project-dir <project> --variant all` |

## 基线文件建议

若用户提供 PDF 基线，优先检查以下位置：

1. `template/baseline.pdf`
2. `.make_latex_model/baselines/baseline.pdf`
3. `.make_latex_model/baselines/word.pdf`

其中：

- `baseline.pdf` 是当前推荐命名。
- `word.pdf` 仅作为 legacy 兼容路径，不应再作为文档默认口径。

## 维护约束

- 新增产品线时，先更新 `config.yaml`，再同步本文件与 `SKILL.md` 的摘要说明。
- 不要再把“是否初始化完成”的判定硬编码为 `extraTex/@config.tex` 是否存在。
