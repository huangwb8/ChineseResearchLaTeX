# 测试报告（{{SESSION_NAME}}）

**测试ID**: {{TEST_ID}}  
**目标技能**: {{TARGET_SKILL_NAME}}  
**目标技能路径**: {{TARGET_SKILL_ROOT}}  
**关联规划文档**: {{PLAN_DOC_PATH}}  
**测试时间**: {{PLAN_TIME}}

---

## 结论

- 状态：✅ 通过 / ❌ 失败 / ⚠️ 部分通过
- 一句话结论：

---

## 覆盖的变更（本轮）

- 修改文件：
  - ...

---

## 执行命令与证据

按时间顺序记录，确保每条结论可复现：

1) 命令：`python3 skills/nsfc-research-content-writer/scripts/validate_skill.py`
   - 期望：
   - 实际：
   - 证据：`_artifacts/...`（如有）

2) 命令：`python3 skills/nsfc-research-content-writer/scripts/create_test_session.py --kind {{KIND_ARG}} --id {{TEST_ID}} --create-plan`
   - 期望：
   - 实际：
   - 证据：`_artifacts/...`（如有）

3) （如本轮涉及输出文件）命令：`python3 skills/nsfc-research-content-writer/scripts/check_project_outputs.py --project-root <your_project_root>`
   - 期望：
   - 实际：
   - 证据：`_artifacts/...`（如有）

4) （可选严格）命令：`python3 skills/nsfc-research-content-writer/scripts/check_project_outputs.py --project-root <your_project_root> --fail-on-risk-phrases`
   - 期望：
   - 实际：
   - 证据：`_artifacts/...`（如有）

---

## 验证点打勾清单

### P0（必须通过）
- [ ] `validate_skill.py` 通过
- [ ] 会话可复跑（不覆盖、不报错）
- [ ] （如适用）输出自检通过

### P1（强烈建议）
- [ ] README/SKILL 入口未回退
- [ ] （可选）严格风险词门禁通过（或给出不启用原因）

### P2（可选）
- [ ] 证据已保存到 `_artifacts/`

---

## 新问题（如有）

- P0/P1/P2：问题描述 + 复现步骤 + 建议处理方式
