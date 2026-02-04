# 轻量测试计划（{{SESSION_NAME}}）

**测试ID**: {{TEST_ID}}  
**轮次类型**: {{ROUND_KIND}}  
**目标技能**: {{TARGET_SKILL_NAME}}  
**目标技能路径**: {{TARGET_SKILL_ROOT}}  
**关联规划文档**: {{PLAN_DOC_PATH}}  
**计划时间**: {{PLAN_TIME}}

---

## 本轮目标

- 验证本轮修复点是否生效（P0/P1/P2 全闭环）
- 确认自检脚本可运行：`scripts/validate_skill.py` / `scripts/run_checks.py`

---

## 变更范围（本轮）

- 修改文件：
  - （填写本轮实际改动文件）

---

## 验证点（按优先级）

### P0（必须通过）
- [ ] `python3 scripts/validate_skill.py` 通过
- [ ] `python3 scripts/create_test_session.py --kind a --id {{TEST_ID}} --create-plan` 可运行（不覆盖已有文件时应无异常）

### P1（建议通过）
- [ ] `python3 scripts/run_checks.py`（不带 --project-root）通过

### P2（可选）
- [ ] 如提供样例项目：`python3 scripts/check_project_outputs.py --project-root <path>` 通过

