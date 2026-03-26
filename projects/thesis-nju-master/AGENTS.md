# thesis-nju-master - 项目指令

本目录是 `bensz-thesis` 的南京大学工程管理学院硕士论文示例项目。AI 在这里的核心任务是同时维护：

- `main.tex` 对 issue #37 公开附件 PDF 的稳定像素级复现链路
- `editable.tex` 这套去除教学标签后的可编辑 thesis 脚手架
- 项目级公开资源、薄封装与统一构建入口

## 修改边界

- 真正的模板身份定义在 `packages/bensz-thesis/`，不要把共享样式重新复制回项目目录
- `main.tex` 是验收入口，不要把教学标签误改写进 `editable.tex` 的正文文件
- `assets/source/` 保留公开基线；`assets/demo/` 保留从 issue 附件提取出的公开素材；`.latex-cache/` 是构建产物，不要手工编辑

## 编译说明

完整仓库模式：

```bash
python packages/bensz-thesis/scripts/thesis_project_tool.py build --project-dir projects/thesis-nju-master
python packages/bensz-thesis/scripts/thesis_project_tool.py build --project-dir projects/thesis-nju-master --tex-file editable.tex
```

项目目录模式：

```bash
python scripts/thesis_build.py
python scripts/thesis_build.py build --tex-file editable.tex
```
