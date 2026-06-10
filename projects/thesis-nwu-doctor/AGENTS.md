# thesis-nwu-doctor - 项目指令

本项目是西北大学博士学位论文示例项目，使用 `packages/bensz-thesis/` 公共包中的独立 `thesis-nwu-doctor` profile/style。

## 修改边界

- NWU 专属版式优先修改 `packages/bensz-thesis/styles/bthesis-style-thesis-nwu-doctor.tex`
- 项目正文、元数据和示例材料优先修改 `projects/thesis-nwu-doctor/extraTex/`
- 不要修改其它学校 thesis style 来适配 NWU
- 官方 PDF / Word 模板只记录来源和哈希，不直接作为项目资产分发

## 验证入口

```bash
python packages/bensz-thesis/scripts/thesis_project_tool.py build --project-dir projects/thesis-nwu-doctor
python packages/bensz-thesis/scripts/validate_package.py --skip-compile
```
