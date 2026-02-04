# 优化计划（{{TEST_ID}}）

**计划日期**: {{PLAN_DATE}}  
**计划ID**: {{TEST_ID}}  
**目标技能**: {{TARGET_SKILL_NAME}}  
**目标技能路径**: {{TARGET_SKILL_ROOT}}  
**计划时间**: {{PLAN_TIME}}

---

## 独立评估声明（强制）

- [ ] 本轮仅基于目标 skill 的当前状态进行审查（不依赖历史 `plans/` / `tests/`）
- [ ] 已扫描：`SKILL.md`、`config.yaml`、`scripts/`、`references/`、`templates/`

**扫描证据（建议填入命令）**：
- `rg -n \"...\" skills/nsfc-research-content-writer`
- `find skills/nsfc-research-content-writer -maxdepth 2 -type f`

---

## 问题清单（按优先级）

> 每个问题至少包含：位置（文件:行号）、现象、影响、修复方案、验证方法。

### P0（必须修复）

1) 标题：
- 位置：
- 现象：
- 影响：
- 修复：
- 验证：

### P1（建议修复）

1) 标题：
- 位置：
- 现象：
- 影响：
- 修复：
- 验证：

### P2（可选）

1) 标题：
- 位置：
- 现象：
- 影响：
- 修复：
- 验证：

---

## 执行步骤（按顺序）

1) ...
2) ...

---

## 本轮轻量测试

- 会话目录：`{{SESSION_DIR_REL}}/`
- 测试计划：`{{TEST_PLAN_REL}}`
- 测试报告：`{{TEST_REPORT_REL}}`

