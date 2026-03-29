# complete-example 参考说明

> 本目录只保留对执行仍有帮助的补充说明；主流程与边界以 `SKILL.md` 和 `config.yaml` 为准。

## 核心定位

- `complete-example` 用来补“示例内容”，不是写真实科研结论
- AI 负责语义理解和叙事生成
- 硬编码负责结构保护、备份、格式验证和回滚

## 常用入口

- `scripts/skill_controller.py`：主控制器
- `config.yaml`：参数、运行目录、扫描与生成策略

## 运行产物

- 默认写入目标项目的 `.complete_example/<run_id>/`
- 常见子目录：
  - `backups/`
  - `logs/`
  - `analysis/`
  - `output/`

## 使用建议

- 首次优先 `preview`
- 需要固定叙事风格时显式给 `narrative_hint`
- 对核心章节再用高密度 `content_density`

## 常见问题

- 格式保护触发：检查日志与备份
- 编译失败：先看 `compile.log`
- 生成质量差：收紧 `narrative_hint`，必要时降低生成温度
