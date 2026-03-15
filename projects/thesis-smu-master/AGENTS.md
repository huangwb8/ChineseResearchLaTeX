# thesis-smu-master - 项目指令

本目录是 `bensz-thesis` 的南方医科大学硕士论文公开示例项目。AI 在这里的核心任务是维护可公开分享的毕业论文示例与构建链路，不得重新引入真实论文正文、真实病历数据或私有图表。

## 修改边界

- `main.tex` 只负责装配结构，不要把大量正文重新堆回主文件
- 正文集中在 `extraTex/body/`、`extraTex/front/`、`extraTex/back/`
- `assets/demo/` 中的图表是公开演示资产，可替换但不要改回真实数据图
- `.latex-cache/` 是构建产物，不要手工编辑

## 编译说明

完整仓库模式：

```bash
python packages/bensz-thesis/scripts/thesis_project_tool.py build --project-dir projects/thesis-smu-master
```

项目目录模式：

```bash
python scripts/thesis_build.py
```
