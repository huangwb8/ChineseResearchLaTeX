# thesis-ucas-doctor - 项目指令

本目录是 `bensz-thesis` 的中国科学院大学博士论文公开示例项目。AI 在这里的核心任务是维护可公开分享的论文示例、项目级薄封装与统一构建链路，不得重新引入私有论文正文、私有导出链路或项目私有样式实现。

## 修改边界

- `main.tex` 只负责结构装配；正文单一真相保留在 `extraTex/`
- 根目录 `chapter1.tex`、`chapter2.tex`、`appendix1.tex`、`appendix2.tex`、`acknowledgements.tex`、`cv.tex` 只是给 `\include` 用的薄 wrapper，不要把正文重新写回这些文件
- 共享样式与专属 class 在 `packages/bensz-thesis/`，不要把 `ucasDissertation` 的实现重新放回项目目录
- `assets/`、`bibs/` 是公开演示资源；`.latex-cache/` 是构建产物，不要手工编辑

## 编译说明

完整仓库模式：

```bash
python packages/bensz-thesis/scripts/thesis_project_tool.py build --project-dir projects/thesis-ucas-doctor
```

项目目录模式：

```bash
python scripts/thesis_build.py
```
