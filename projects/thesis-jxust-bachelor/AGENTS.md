# thesis-jxust-bachelor - 项目指令

本目录是 `bensz-thesis` 的江西理工大学本科毕业论文 / 毕业设计公开示例项目。AI 在这里的核心任务是维护可公开分享的本科论文示例与构建链路，不得把私有论文原稿、比对基线或验收截图混入项目交付层。

## 修改边界

- `main.tex` 只负责装配结构，不要把大量正文重新堆回主文件
- 正文集中在 `extraTex/body/`、`extraTex/front/`、`extraTex/back/`
- `main.tex` 通过 `\jxustSetWorkType{thesis|design}` 控制毕业论文 / 毕业设计页眉与封面标题，不要复制成两套主文件
- `.latex-cache/` 是构建产物，不要手工编辑

## 编译说明

完整仓库模式：

```bash
python packages/bensz-thesis/scripts/thesis_project_tool.py build --project-dir projects/thesis-jxust-bachelor
```

项目目录模式：

```bash
python scripts/thesis_build.py
```
