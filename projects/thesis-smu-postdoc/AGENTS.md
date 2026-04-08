# thesis-smu-postdoc - 项目指令

本目录是一个基于 `bensz-thesis` 构建的南方医科大学博士后研究报告公开示例项目。AI 在这里的核心任务是维护可公开分享的研究报告示例与构建链路，不得重新引入真实出站材料、真实病历数据、私有图表或敏感个人信息。

## 修改边界

- `main.tex` 只负责装配结构，不要把大量正文重新堆回主文件
- 正文集中在 `extraTex/body/`，前置页集中在 `extraTex/front/`，后置页集中在 `extraTex/back/`
- `assets/` 中的校名字样与公开演示素材可复用，但不要替换成私有盖章页、真实签字页或未脱敏附件
- `.latex-cache/` 是构建产物，不要手工编辑

## 编译说明

完整仓库模式：

```bash
python packages/bensz-thesis/scripts/thesis_project_tool.py build --project-dir projects/thesis-smu-postdoc
```

项目目录模式：

```bash
python scripts/thesis_build.py
```
