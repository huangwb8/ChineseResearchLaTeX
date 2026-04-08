# thesis-smu-postdoc

`thesis-smu-postdoc` 是一个基于 `bensz-thesis` 构建的南方医科大学博士后研究报告公开示例项目。

说明：

- 封面与题名页优先吸收《博士后研究报告编写规则》的国家通用口径，并结合南方医科大学现有公开模板资产做项目化重构
- 项目复用 `bensz-thesis` 的统一构建链路，不新增专门的 `bensz-postdoc` 公共包
- 当前正文、摘要、科研成果与个人简历均为公开演示内容，不包含任何真实出站材料或私有科研数据

构建方式：

```bash
python packages/bensz-thesis/scripts/thesis_project_tool.py build --project-dir projects/thesis-smu-postdoc
```

只打开项目子目录时，可执行：

```bash
python scripts/thesis_build.py
```
