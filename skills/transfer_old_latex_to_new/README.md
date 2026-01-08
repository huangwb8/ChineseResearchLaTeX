# LaTeX 标书智能迁移器

**技能名称**: `transfer-old-latex-to-new`
**版本**: v1.1.0
**最后更新**: 2026-01-08

---

## 📖 这是什么？

**LaTeX 标书智能迁移器**是国自然科学基金（NSFC）标书跨版本迁移的 AI 助手。当你需要：

- 把旧版标书迁移到新版模板
- 不同版本的 NSFC 模板互相转换
- 应对模板结构变化（章节拆分、合并、新增）

**只需一句话**，AI 会自动完成结构分析、内容迁移、格式调整、编译验证。

---

## 🎯 核心能力

| 能力 | 说明 |
|------|------|
| **AI 语义映射** | 让 AI 真正理解文件内容后判断映射关系（不是硬编码规则） |
| **自动识别版本** | 自动识别各年份 NSFC 模板版本 |
| **智能结构映射** | 自动处理章节的一对一、一对多、多对一映射 |
| **内容零丢失** | 无法自动迁移的内容会标记，确保不遗漏 |
| **一键恢复** | 迁移前自动备份，不满意可随时回滚 |
| **编译验证** | 自动运行 LaTeX 4步法编译，确保生成 PDF |

---

## 💡 如何使用

直接告诉 AI 你的需求：

```
请使用 skills/transfer-old-latex-to-new 迁移标书：
- 旧项目：/Users/xxx/Documents/NSFC_Old
- 新项目：/Users/xxx/Documents/NSFC_New
```

AI 会自动执行迁移并输出结果。

---

## 📥 输入

迁移前需要准备：

| 输入项 | 说明 | 示例 |
|--------|------|------|
| **旧项目路径** | 旧版本标书所在目录的**绝对路径** | `/Users/xxx/Documents/NSFC_Old/` |
| **新项目路径** | 新模板项目的**绝对路径**（需提前创建） | `/Users/xxx/Documents/NSFC_New/` |

**要求**：
- 两个目录都必须存在且可访问

---

## 📤 输出

迁移完成后，会在 `skills/transfer_old_latex_to_new/runs/<run_id>/` 目录生成：

### 核心交付物

| 文件 | 说明 |
|------|------|
| **deliverables/migrated_proposal.pdf** | 迁移后的标书 PDF |
| **deliverables/change_summary.md** | 变更摘要（哪些章节迁移了） |
| **deliverables/structure_comparison.md** | 结构对比报告 |
| **deliverables/unmapped_old_content.md** | 未映射的旧内容（需人工处理） |
| **deliverables/restore_guide.md** | 恢复指南 |

### 分析与日志

| 目录/文件 | 说明 |
|-----------|------|
| **analysis/** | 结构分析 JSON（章节树、差异分析） |
| **plan/** | 迁移计划 JSON |
| **logs/** | 执行日志（apply_result.json） |
| **backup/** | Apply 前的新项目快照（用于恢复） |

---

## ⚠️ 重要说明

### 迁移前

- ✅ 新项目需要提前创建好

### 迁移中

- ✅ AI 只修改新项目的 `extraTex/*.tex` 内容文件
- ✅ AI 会自动备份新项目的内容文件（可随时恢复）
- ❌ 绝不修改 `main.tex`、`@config.tex`、`.cls`、`.sty` 等系统文件

### 迁移后

- ✅ 通读生成的 PDF，检查逻辑连贯性
- ✅ 重点查看 `unmapped_old_content.md`（如有未迁移的内容）
- ⚠️ 部分内容可能需要人工润色

---

## 📖 参考文档

| 文档 | 路径 | 说明 |
|------|------|------|
| **版本差异指南** | [references/version_differences_2025_2026.md](references/version_differences_2025_2026.md) | 2025→2026 结构变化详解 |
| **映射指南** | [references/structure_mapping_guide.md](references/structure_mapping_guide.md) | 章节映射决策参考 |
| **迁移模式库** | [references/migration_patterns.md](references/migration_patterns.md) | 常见迁移模式案例 |

---

## 📋 版本与变更

**当前版本**: v1.1.0（与 [config.yaml](config.yaml) 同步）

**变更记录**: 见根级 [CHANGELOG.md](../../../CHANGELOG.md)

---

**最后更新**: 2026-01-08
**维护者**: AI Agent (Claude Code)
