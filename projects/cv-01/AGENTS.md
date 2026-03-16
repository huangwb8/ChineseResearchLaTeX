# cv-01 - 项目指令

本目录是 `bensz-cv` 的中英文简历示例项目。AI 在这里的核心任务是维护公开可分享的简历示例与构建链路，不得重新引入真实姓名、真实电话、真实邮箱、真实 ORCID 或私有履历细节。

## 修改边界

- `main-zh.tex` 与 `main-en.tex` 是当前双语示例入口
- `references/` 仅存放公开可分享的演示参考文献或 synthetic bibliography
- `assets/avatar.jpg` 必须保持为公开可分享头像，不要替换回真实简历照片
- `.latex-cache/` 是构建产物，不要手工编辑

## 编译说明

完整仓库模式：

```bash
python packages/bensz-cv/scripts/cv_project_tool.py build --project-dir projects/cv-01 --variant all
```

项目目录模式：

```bash
python scripts/cv_build.py
```
