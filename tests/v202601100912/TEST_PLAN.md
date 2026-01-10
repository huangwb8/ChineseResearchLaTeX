# 轻量测试计划：nsfc-justification-writer（P0–P2 安全修复验证）

**创建日期**：2026-01-10  
**范围**：`skills/nsfc-justification-writer/`（配置加载/guardrails 加固/prompt 风险提示/备份回滚定位）  
**目标**：验证 `plans/v202601100912.md` 中 P0–P2 改动已落地且可运行。  

---

## 测试约束（目录与中间文件）

- 所有测试产生的中间文件必须写入 `tests/v202601100912/` 目录树内。
- 本次测试使用 `tests/v202601100912/work/` 作为临时工作目录（由测试脚本创建/清理）。

---

## 测试用例

### T1：无 PyYAML 时 `load_config()` 可降级运行且 guardrails 仍生效（P1）

- 方法：在测试脚本中模拟 `import yaml` 失败，调用 `core.config_loader.load_config(...)`
- 预期：
  - 不抛异常
  - `config["_config_loader"]["yaml_available"] == False`
  - `guardrails.allowed_write_files` 不为空且默认为安全白名单

### T2：guardrails 被置空/清空时不会导致“白名单失效”（P0）

- 方法：构造 `config={"guardrails": None}` 或 `{"guardrails": {"allowed_write_files": []}}`，调用 `core.security.build_write_policy()`
- 预期：
  - 仍返回非空白名单（回退到默认安全值）
  - `validate_write_target()` 对非白名单目标拒绝写入

### T3：prompt 外部路径风险提示（P2）

- 方法：构造 `prompts.*` 指向 skill_root 外路径（如 `/etc/passwd`），调用 `load_config()` 的 warnings 收集逻辑
- 预期：
  - `_config_loader.warnings` 包含外部路径提示（风险提示而非阻断）

### T4：备份/回滚按相对路径优先定位，并兼容旧版按文件名回退（P2）

- 方法：
  - 构造新式备份路径：`backup/<run_id>/<relpath>`
  - 构造旧式备份路径：`backup/<run_id>/<filename>`
  - 调用 `core.versioning.find_backup_for_run_v2(...)`
- 预期：
  - 新式存在时按 relpath 命中
  - 新式不存在时回退到旧式 filename 命中

---

## 执行命令

在仓库根目录运行：

```bash
python3 tests/v202601100912/run_light_tests.py
```

---

## 验收标准

- `tests/v202601100912/TEST_REPORT.md` 记录每个用例的结果（PASS/FAIL）与关键输出。
- 所有用例 PASS；若有 FAIL，需在本次改动中修复并重新运行，直至 PASS。

---

本文件不记录变更历史；变更历史统一记录在 `CHANGELOG.md`。

