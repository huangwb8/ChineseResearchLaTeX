# transfer-old-latex-to-new 约定符合性速记

> 本文只保留当前仍有价值的“合规检查清单”。历史上关于旧命名、旧 frontmatter 和旧 NSFC 专用定位的长篇评估，已不再作为当前技能行为依据。

## 当前口径

- 当前 skill 名称：`transfer-old-latex-to-new`
- 当前定位：把旧材料迁移到 **ChineseResearchLaTeX 现有模板项目的内容层**
- 当前硬边界：
  - 不改 `packages/`
  - 不改 `projects/` 的模板骨架、样式和入口
  - 只写 `extraTex/**/*.tex`（排除 `@config.tex`）与 `references/**/*.bib`

## 需要持续满足的合规点

### Frontmatter 与可发现性

- `name` 与 skill 真实名称一致
- `description` 同时说明：
  - 做什么
  - 何时用
- `metadata.keywords` 含 skill 名与核心触发词

### SKILL.md 与正文一致性

- 触发范围、输入输出、默认写入边界一致
- `scripts/run.py`、`scripts/migrate.sh` 仅作为 legacy CLI，不得被写成主工作流
- 如更新了引用文档，检查 `SKILL.md` 中的引用是否仍准确

### 目录与文档分层

- `SKILL.md`：主流程与硬约束
- `references/`：补充细则、legacy 差异、排障
- `README.md` / `CHANGELOG.md`：面向人类，不拿来承载 AI 执行规则

## 常见失配

- 把 skill 描述回旧的“NSFC 任意年份模板迁移器”
- 把 legacy CLI 当成默认入口
- 把可写范围从内容层偷偷扩到模板骨架
- 在 references 中保留大量历史评审意见，却不再对应当前实现

## 维护动作

- 改技能行为时，先改 `SKILL.md`
- 若只是补充案例或边缘说明，再改 `references/`
- 若变更影响用户认知，再同步 `README.md` 与 `CHANGELOG.md`
