# 优化计划（{{TEST_ID}}）

**计划日期**: {{PLAN_DATE}}  
**计划ID**: {{TEST_ID}}  
**目标技能**: {{TARGET_SKILL_NAME}}  
**目标技能路径**: {{TARGET_SKILL_ROOT}}

---

## 问题清单（按优先级）

> 每个问题至少包含：位置（文件:行号）、影响、修复方式、验证方法。
> 每轮至少 10 条（P0+P1+P2 合计），鼓励 15–20 条。

### P0（必须修复）

1) 标题：
- 位置：`path/to/file:line`
- 影响：
- 修复：
- 验证：

### P1（强烈建议）

1) 标题：
- 位置：`path/to/file:line`
- 影响：
- 修复：
- 验证：

### P2（可选）

1) 标题：
- 位置：`path/to/file:line`
- 影响：
- 修复：
- 验证：

---

## 执行步骤（按顺序）

1) ...
2) ...

---

## 本轮轻量测试

- 会话目录：`tests/{{TEST_ID}}/`
- 测试计划：`tests/{{TEST_ID}}/TEST_PLAN.md`
- 测试报告：`tests/{{TEST_ID}}/TEST_REPORT.md`
- 最小门禁：`python3 skills/nsfc-research-content-writer/scripts/validate_skill.py`
- 输出自检（如涉及写入）：`python3 skills/nsfc-research-content-writer/scripts/check_project_outputs.py --project-root <your_project_root>`
- 风险词门禁（可选严格）：`python3 skills/nsfc-research-content-writer/scripts/check_project_outputs.py --project-root <your_project_root> --fail-on-risk-phrases`
