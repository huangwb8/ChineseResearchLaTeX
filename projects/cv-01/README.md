# cv-01

`cv-01` 是本仓库中首个中英文学术简历示例项目。

它的核心特点是：

- 依赖公共包 [`packages/bensz-cv`](/Volumes/2T01/Github/ChineseResearchLaTeX/packages/bensz-cv)
- 同一项目内维护中文和英文两份简历入口
- 支持统一 Python wrapper 构建与像素级 PDF 比较

## 内容来源说明

本项目当前正文、头像与参考文献均为公开可分享的演示内容：

- 演示人物采用“佐佐木希 / Nozomi Sasaki”这一公开人物设定
- 联系方式、ORCID、GitHub、教育与经历均为模板展示所用的虚构信息
- `references/` 下的条目为演示引用样式所用的 synthetic bibliography，不对应真实论文成果

## 构建

仓库内开发时，推荐直接执行：

```bash
python packages/bensz-cv/scripts/cv_project_tool.py build --project-dir projects/cv-01 --variant all
```

若只打开了项目子目录，可执行：

```bash
python scripts/cv_build.py
```

构建成功后会产出：

- `main-zh.pdf`
- `main-en.pdf`
- `.latex-cache/`

如需做版式回归验收，可执行：

```bash
python packages/bensz-cv/scripts/cv_project_tool.py compare --project-dir projects/cv-01 --variant zh --baseline-pdf <baseline.pdf>
```

## 结构

- `main-zh.tex`：中文简历入口
- `main-en.tex`：英文简历入口
- `references/`：参考文献 BibTeX 数据库
- `scripts/cv_build.py`：项目级构建 wrapper
