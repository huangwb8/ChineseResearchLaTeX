# 轻量测试计划（TEST_PLAN）

**测试ID**: {{TEST_ID}}  
**目标技能**: {{TARGET_SKILL_NAME}}  
**目标技能路径**: {{TARGET_SKILL_ROOT}}  
**轮次类型**: {{ROUND_KIND}}  
**关联规划文档**: {{PLAN_DOC_PATH}}  
**计划时间**: {{PLAN_TIME}}

---

## 目标

- 本轮要验证的核心行为是什么？
- 本轮要解决/验证的 P0-P2 问题是什么？
- 本轮的“通过”标准是什么？

---

## 变更范围（本轮）

- 修改文件：
  - ...
- 重要行为变化：
  - ...

---

## 验证点（轻量测试）

### P0（必须通过）
- [ ] `python3 skills/nsfc-research-content-writer/scripts/validate_skill.py`
- [ ] 本轮会话可复跑：`python3 skills/nsfc-research-content-writer/scripts/create_test_session.py --kind {{KIND_ARG}} --id {{TEST_ID}} --create-plan`
- [ ] （如本轮涉及输出文件）`python3 skills/nsfc-research-content-writer/scripts/check_project_outputs.py --project-root <your_project_root>`

### P1（强烈建议通过）
- [ ] 关键文档入口未回退（README/SKILL 链接、命令仍可用）
- [ ] 风险词门禁（可选严格）：`python3 skills/nsfc-research-content-writer/scripts/check_project_outputs.py --project-root <your_project_root> --fail-on-risk-phrases`

### P2（可选）
- [ ] 关键检查输出已保存到 `_artifacts/`（如 stdout/stderr）

---

## 执行步骤

1. 按验证点执行，并记录证据
2. 发现新问题：记录到 `TEST_REPORT.md` 的“新问题”并标注优先级
