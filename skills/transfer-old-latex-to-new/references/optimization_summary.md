# transfer-old-latex-to-new 优化摘要

> 历史上此文用于记录一次旧版“约定符合性优化”。当前只保留仍有用的维护结论，避免与现行 `SKILL.md` 重复。

## 保留结论

- 技能名称、触发语义和内容层边界必须在 `SKILL.md` frontmatter 中讲清楚
- 用户文档若描述安装或入口，需与真实脚本一致
- `metadata.keywords`、`triggers` 等可发现性字段要和真实 skill 名保持一致

## 不再沿用的旧结论

- 旧的命名推荐、旧版 NSFC 专用定位、旧环境要求评分，不再是当前行为依据

## 当前维护动作

1. 先改 `SKILL.md`
2. 再改 `references/`
3. 需要面向用户同步时再改 `README.md` / `CHANGELOG.md`
