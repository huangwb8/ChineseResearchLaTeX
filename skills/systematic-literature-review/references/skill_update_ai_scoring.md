# AI 评分迁移备注

> 历史说明：本技能已从“脚本关键词评分”切换到“AI 直接阅读标题与摘要评分”。本文只保留迁移后的最小口径，避免重复维护旧方案细节。

## 当前口径

- 主流程：AI 直接生成 `scored_papers.jsonl`
- 后备：必要时仍可使用脚本关键词法
- 优势：
  - 语义理解更强
  - 评分与写作上下文更连贯
  - 不再依赖额外外部模型调用

## 当前产物要求

- `score`
- `subtopic`
- `rationale`
- `alignment`
- `extraction`

详见：

- `references/ai_scoring_prompt.md`
- `SKILL.md`
