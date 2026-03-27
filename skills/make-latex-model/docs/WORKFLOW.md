# make-latex-model 工作流

本文件描述 `make-latex-model` 在当前 ChineseResearchLaTeX 仓库中的推荐执行方式。

核心变化只有一句话：

- 现在优先服从 `packages/ + projects/ + 官方构建脚本` 的真实结构
- 旧版 NSFC 专用脚本链路只作为辅助，不再是默认主流程

## 0. 先判定产品线

根据目标项目路径先判断你在处理哪条产品线：

- `projects/NSFC_*` -> `nsfc`
- `projects/paper-*` -> `paper`
- `projects/thesis-*` -> `thesis`
- `projects/cv-*` -> `cv`

随后优先阅读对应标准文档：

- `docs/for-developers/nsfc-template-standard.md`
- `docs/for-developers/paper-template-standard.md`
- `docs/for-developers/thesis-template-standard.md`
- `docs/for-developers/cv-template-standard.md`
- `skills/make-latex-model/references/PRODUCT_LINE_RULES.md`

## 1. 再判定验收口径

常见目标有三类：

1. 对齐某份官方模板或 baseline PDF
2. 把当前项目整理成符合仓库标准的“好模板”
3. 新增或修复一套共享模板能力

可接受的 baseline 输入：

- 官方 PDF
- Word 导出 PDF
- 既有 baseline PDF
- 学校或期刊给出的公开样例 PDF

## 2. 选择修改层级

优先用下面这条规则：

- 只影响单项目：改 `projects/*`
- 影响多个项目共享行为：改 `packages/bensz-*`
- 两边都有：联动修改，但每层职责要清楚

### 当前仓库里的典型位置

#### NSFC

- 项目层：`main.tex`、`extraTex/@config.tex`
- 包层：`packages/bensz-nsfc/profiles/`、`impl/`、`scripts/`

#### Paper

- 项目层：`main.tex`、`extraTex/**/*.tex`、`artifacts/reference.docx`、`artifacts/manuscript.csl`
- 包层：`packages/bensz-paper/profiles/`、`bml-*.sty`、`scripts/`

#### Thesis

- 项目层：`main.tex`、`baseline.tex`、`editable.tex`、`extraTex/`、`template.json`
- 包层：`packages/bensz-thesis/profiles/`、`styles/`

#### CV

- 项目层：`main-zh.tex`、`main-en.tex`、`assets/`
- 包层：`packages/bensz-cv/`、`profiles/`

## 3. 实施修改

执行时遵守以下准则：

- 优先最小正确修改，不做无关重构
- 共享逻辑不要复制回项目层
- 不要为了沿用旧 skill 规则，硬把 thesis / paper / cv 简化成 `@config.tex` 问题
- 默认不重写用户正文语义内容；除非用户明确要求，或正文装配本身就是模板工作的一部分

## 4. 用官方入口验证

### NSFC

```bash
python packages/bensz-nsfc/scripts/nsfc_project_tool.py build --project-dir <项目路径>
```

### Paper

```bash
python packages/bensz-paper/scripts/paper_project_tool.py build --project-dir <项目路径>
```

### Thesis

```bash
python packages/bensz-thesis/scripts/thesis_project_tool.py build --project-dir <项目路径>
```

如需回归比对：

```bash
python packages/bensz-thesis/scripts/thesis_project_tool.py compare --project-dir <项目路径> --baseline-pdf <baseline.pdf>
```

### CV

```bash
python packages/bensz-cv/scripts/cv_project_tool.py build --project-dir <项目路径> --variant all
```

如需回归比对：

```bash
python packages/bensz-cv/scripts/cv_project_tool.py compare --project-dir <项目路径> --variant zh --baseline-pdf <baseline.pdf>
```

## 5. 需要时使用辅助脚本

以下脚本可以用来补充判断，但不是默认主流程：

- `check_state.py`
- `analyze_pdf.py`
- `compare_headings.py`
- `compare_pdf_pixels.py`
- `optimize_heading_linebreaks.py`

脚本边界说明见：`skills/make-latex-model/references/LEGACY_SCRIPT_SCOPE.md`

推荐使用场景：

- 你手里只有 PDF baseline，想先抽取参数
- 你想快速对比标题文本或标题换行
- 你要做像素级差异分析

不推荐的用法：

- 用 `validate.sh` 替代当前产品线官方构建命令
- 强迫 `paper / thesis / cv` 套入旧版 NSFC 目录假设

## 6. 收尾

输出时至少说明：

- 这次问题属于哪条产品线
- 改动落在项目层、包层，还是两者联动
- 使用了哪条官方验证命令
- 是否执行了 compare / 像素比对；如果没有，为什么没做
