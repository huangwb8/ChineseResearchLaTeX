# 恢复指南

- run_id: `20260108_160458_739741`
- 说明：本技能在 apply 前会为新项目的目标文件创建快照（仅限白名单路径）。

## 一键恢复命令

```bash
python skills/transfer_old_latex_to_new/scripts/run.py restore --run-id 20260108_160458_739741 --new /path/to/new_project
```

## 备注
- 本恢复只覆盖本次 apply 涉及的目标文件。
- 如新项目在 apply 后又被手动修改，恢复会以快照为准覆盖对应文件。
