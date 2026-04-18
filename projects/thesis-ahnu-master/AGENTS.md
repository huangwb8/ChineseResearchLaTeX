# thesis-ahnu-master - 项目指令

本目录是 `bensz-thesis` 的安徽师范大学硕士论文公开示例项目。AI 在这里的核心任务是维护可公开分享的硕士论文示例与构建链路，不得把私有论文原稿、验收差异图或临时分析材料混入项目交付层。

## 修改边界

- `main.tex` 只负责装配结构，不要把大量正文重新堆回主文件
- 正文集中在 `extraTex/body/`、`extraTex/front/`、`extraTex/back/`
- `assets/branding/` 中是公开校名字样素材，可替换但不要混入私有论文附件
- `.latex-cache/` 是构建产物，不要手工编辑

## 编译说明

完整仓库模式：

```bash
python packages/bensz-thesis/scripts/thesis_project_tool.py build --project-dir projects/thesis-ahnu-master
```

项目目录模式：

```bash
python scripts/thesis_build.py
```
