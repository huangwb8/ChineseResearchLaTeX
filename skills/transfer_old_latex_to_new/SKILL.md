---
name: transfer-old-latex-to-new
description: 智能迁移旧版NSFC标书到新版模板：分析结构→AI规划→执行迁移→迭代优化→编译验证。支持2024/2025/2026版NSFC模板互迁。详见《CLAUDE.md》变更规范。
---

# LaTeX 标书智能迁移器

> **核心入口**: `python skills/transfer_old_latex_to_new/scripts/run.py --help`
>
> **配置中心**: [config.yaml](config.yaml) - 所有阈值、策略、AI参数集中配置
>
> **参考文档**: [references/](references/) 目录 - 版本差异、映射指南、迁移模式

---

## 快速开始

```bash
# 一键分析（生成结构差异报告）
python skills/transfer_old_latex_to_new/scripts/run.py analyze \
  --old /path/to/NSFC_2025 \
  --new /path/to/NSFC_2026

# 一键应用（执行迁移，apply前自动快照）
python skills/transfer_old_latex_to_new/scripts/run.py apply \
  --old /path/to/NSFC_2025 \
  --new /path/to/NSFC_2026 \
  --run_id <上一步输出的run_id>

# 一键编译（验证迁移结果）
python skills/transfer_old_latex_to_new/scripts/run.py compile \
  --new /path/to/NSFC_2026

# 一键恢复（回滚到apply前状态）
python skills/transfer_old_latex_to_new/scripts/run.py restore \
  --run_id <run_id>
```

**输出目录**: `skills/transfer_old_latex_to_new/runs/<run_id>/`

```
runs/<run_id>/
├── input_snapshot/     # 旧新项目输入快照
├── analysis/           # 结构分析JSON（sections_map_*.json, structure_diff.json）
├── plan/               # 迁移计划（migration_plan.json）
├── backup/             # Apply前新项目快照（用于restore）
├── logs/               # 执行日志（apply_result.json）
└── deliverables/       # 交付物（PDF、报告、指南）
```

---

## 前置约束（铁律）

### 修改范围白名单

**✅ 可修改**:
- `extraTex/*.tex` 内容文件（**排除** `@config.tex`）
- 新项目 `references/*.bib`（如需更新引用格式）
- 本技能运行产物：`runs/<run_id>/`（日志、分析、备份、交付物）

**❌ 禁止修改**:
- `main.tex` 模板结构文件
- `extraTex/@config.tex` 配置文件
- `.cls`、`.sty` 样式文件
- 任何影响编译环境的系统文件

### 质量底线

| 指标 | 阈值 | 说明 |
|------|------|------|
| **内容完整性** | 100% | 旧科学内容零丢失 |
| **LaTeX编译** | 无致命错误 | 允许警告但必须生成PDF |
| **引用完整性** | 修复率≥90% | `\ref`、`\cite`错误数≤配置阈值 |

---

## 核心工作流（五阶段）

### Phase 0: 参数验证与准备

**执行**: [scripts/run.py:cmd_analyze](scripts/run.py)

**核心逻辑**:
```python
# 0.1 路径验证（core/security_manager.py）
SecurityManager.validate_paths(old_project, new_project)

# 0.2 版本识别（core/project_analyzer.py）
detect_project_version(project_path)  # -> "2025" | "2026" | "unknown"

# 0.3 创建运行目录（core/run_manager.py）
run = create_run(runs_root, run_id=args.run_id)
```

**配置参考**: [config.yaml#L9-L18](config.yaml#L9-L18) - `migration.backup_mode`

---

### Phase 1: 双向结构深度分析

**执行**: [core/project_analyzer.py:analyze_project](core/project_analyzer.py)

**输出**:
- `analysis/sections_map_old.json` - 旧项目章节树
- `analysis/sections_map_new.json` - 新项目章节树

**关键解析点**:
- 章节树结构（`\section`、`\subsection` 层级）
- 内容文件映射（`\input{}` / `\include{}`）
- 标签定义（`\label{}`）与引用（`\ref{}`、`\cite{}`）

---

### Phase 2: 智能差异分析与映射

**执行**: [core/mapping_engine.py:compute_structure_diff](core/mapping_engine.py)

**输出**: `analysis/structure_diff.json`

**映射类型**:
```json
{
  "mapping": {
    "one_to_one": [{"old": "...", "new": "...", "similarity": 0.95}],
    "one_to_many": [{"old": "...", "new": ["...", "..."], "split_strategy": "semantic_split"}],
    "many_to_one": [{"old": ["...", "..."], "new": "...", "merge_strategy": "sequential_merge"}],
    "new_added": [{"file": "...", "content_source": "generate_from_context"}],
    "removed": [{"file": "...", "reason": "..."}]
  }
}
```

**配置参考**: [config.yaml#L185-L226](config.yaml#L185-L226) - `mapping_heuristics`

**AI决策规则**: [config.yaml#L132-L181](config.yaml#L132-L181) - `decision_rules`

---

### Phase 3: AI自主规划迁移策略

**执行**: [core/migration_plan.py:build_plan_from_diff](core/migration_plan.py)

**输出**: `plan/migration_plan.json`

**规划要素**:
- **任务分解**: 每个映射 → 1个迁移任务（含优先级、动作、验证、风险）
- **优化计划**: 5轮优化重点（见 [config.yaml#L232-L248](config.yaml#L232-L248)）
- **收敛标准**: 满足任一即提前退出（见 [config.yaml#L250-L259](config.yaml#L250-L259)）
- **验证检查**: LaTeX编译、章节非空、引用完整性、内容完整性

---

### Phase 4: 内容智能迁移执行

**执行**: [scripts/run.py:cmd_apply](scripts/run.py) → [core/migrator.py:apply_plan](core/migrator.py)

**Apply前安全机制**:
```python
# 自动快照新项目（core/snapshot.py）
snapshot_project_editables(new_project, run.backup_dir)

# 安卫检查（core/security_manager.py）
SecurityManager.for_new_project(new_project, runs_root)
```

**迁移类型执行**:

| 类型 | 实现函数 | 关键逻辑 |
|------|----------|----------|
| **一对一** | `migrator._migrate_one_to_one` | 直接复制+语法检查+引用更新 |
| **一对多** | `migrator._migrate_one_to_many` | AI语义拆分+过渡段生成 |
| **多对一** | `migrator._migrate_many_to_one` | 顺序拼接+去重+过渡段 |
| **新增内容** | `migrator._generate_new_content` | 调用写作技能（见 [config.yaml#L287-L329](config.yaml#L287-L329)） |

**配置参考**: [config.yaml#L20-L28](config.yaml#L20-L28) - `migration.strategy` / `content_generation`

---

### Phase 5: 迭代优化与验证

**执行**: [core/compiler.py:compile_project](core/compiler.py) + [core/reports.py](core/reports.py)

**LaTeX编译4步法**（见 [config.yaml#L58-L75](config.yaml#L58-L75)）:
```bash
xelatex → bibtex → xelatex → xelatex
```

**交付物生成** (`runs/<run_id>/deliverables/`):
- `migrated_proposal.pdf` - 迁移后PDF
- `migration_log.md` - 迁移日志
- `change_summary.md` - 变更摘要
- `structure_comparison.md` - 结构对比报告
- `restore_guide.md` - 恢复指南

---

## AI智能决策点

以下决策由AI基于 [config.yaml](config.yaml) 规则**自主完成**，无需用户确认：

| 决策点 | 输入来源 | AI规则（config.yaml） | 输出 |
|--------|----------|---------------------|------|
| **迭代轮次** | 项目规模、结构复杂度 | `decision_rules.rounds_decision` | `max_rounds: 3\|5\|7` |
| **迁移策略** | 结构差异分析结果 | `decision_rules.strategy_decision` | `conservative\|smart\|aggressive` |
| **备份方式** | 配置文件、时间戳 | `decision_rules.backup_decision` | `snapshot\|copy\|skip` |
| **编译失败处理** | 错误类型、严重程度 | `decision_rules.compilation_failure_handling` | `abort\|retry\|continue` |

---

## 版本差异参考

执行迁移前，AI自动读取以下参考文档：

| 文档 | 路径 | 用途 |
|------|------|------|
| **版本结构差异** | [references/version_differences_2025_2026.md](references/version_differences_2025_2026.md) | 理解板块重组、编号变化、新增章节 |
| **章节映射指南** | [references/structure_mapping_guide.md](references/structure_mapping_guide.md) | 决策一对一/一对多/多对一映射 |
| **常见迁移模式** | [references/migration_patterns.md](references/migration_patterns.md) | 参考历史成功案例 |

**版本兼容性**: [config.yaml#L346-L362](config.yaml#L346-L362)

---

## 质量保证检查表

### 迁移前（analyze阶段）

- [ ] 旧新项目路径有效且包含 `main.tex`
- [ ] 两个项目都有 `extraTex/` 目录
- [ ] 版本识别成功（2024/2025/2026）
- [ ] 已读取版本差异参考文档

### 迁移中（apply阶段）

- [ ] 结构分析完成（生成 `sections_map_*.json`）
- [ ] 差异分析完成（生成 `structure_diff.json`）
- [ ] 迁移计划已生成（`migration_plan.json`）
- [ ] **Apply前快照已创建**（`runs/<run_id>/backup/`）
- [ ] 安卫检查通过（未触碰白名单外文件）

### 迁移后（compile阶段）

- [ ] LaTeX编译通过（无致命错误）
- [ ] 所有章节非空（字数≥配置阈值）
- [ ] 引用完整性验证通过
- [ ] 已生成所有交付物

---

## 故障排除

### LaTeX编译失败

```bash
# 查看详细编译日志
cat runs/<run_id>/logs/compile_result.json

# 常见原因：宏包不兼容、语法错误、引用失效
# 解决：检查 core/compiler.py 日志，修复后重新 compile
```

### 迁移内容为空

```bash
# 检查映射关系
cat runs/<run_id>/analysis/structure_diff.json

# 手动调整映射后重新 apply
```

### 需要回滚

```bash
# 一键恢复到apply前状态
python skills/transfer_old_latex_to_new/scripts/run.py restore --run_id <run_id>
```

---

## 扩展开发

### 新增迁移策略

1. 更新 [config.yaml#L145-L156](config.yaml#L145-L156) - `decision_rules.strategy_decision`
2. 在 [core/mapping_engine.py](core/mapping_engine.py) 实现映射逻辑
3. 在 [core/migrator.py](core/migrator.py) 实现迁移逻辑

### 新增写作技能集成

1. 更新 [config.yaml#L287-L329](config.yaml#L287-L329) - `skill_integration.available_skills`
2. 在 [core/migrator.py:_generate_new_content](core/migrator.py) 调用新技能

### 调整质量阈值

1. 修改 [config.yaml#L36-L54](config.yaml#L36-L54) - `quality_thresholds`
2. 无需修改代码，阈值自动生效

---

## 核心模块索引

| 模块 | 路径 | 职责 |
|------|------|------|
| **入口脚本** | [scripts/run.py](scripts/run.py) | CLI命令解析、流程编排 |
| **配置加载** | [core/config_loader.py](core/config_loader.py) | 加载config.yaml、路径解析 |
| **运行管理** | [core/run_manager.py](core/run_manager.py) | 创建/获取run、目录结构管理 |
| **安全检查** | [core/security_manager.py](core/security_manager.py) | 白名单验证、路径安全检查 |
| **项目分析** | [core/project_analyzer.py](core/project_analyzer.py) | 解析LaTeX项目结构、章节树 |
| **映射引擎** | [core/mapping_engine.py](core/mapping_engine.py) | 计算结构差异、推断映射关系 |
| **迁移计划** | [core/migration_plan.py](core/migration_plan.py) | 生成迁移计划、任务分解 |
| **迁移执行** | [core/migrator.py](core/migrator.py) | 执行内容迁移、引用修复 |
| **LaTeX编译** | [core/compiler.py](core/compiler.py) | 4步法编译、错误提取 |
| **快照管理** | [core/snapshot.py](core/snapshot.py) | 项目快照、恢复 |
| **报告生成** | [core/reports.py](core/reports.py) | 生成交付物Markdown/JSON |

---

## 版本与变更

**当前版本**: v1.0.0（与 [config.yaml#metadata](config.yaml#L366-L372) 同步）

**变更历史**: 记录于根级 [CHANGELOG.md](../../../CHANGELOG.md)

---

## 技能调用示例

### 在对话中触发

```
用户: "帮我把2025年的标书迁移到2026新模板"
AI: 检测到迁移需求 → 触发本技能 → 执行完整工作流
```

### 程序化调用

```python
from core.migrator import apply_plan
from core.config_loader import load_config

config = load_config(skill_root)
result = apply_plan(old_project, new_project, plan, config, security, backup_root)
```

---

**最后更新**: 2026-01-08
**维护者**: AI Agent (Claude Code)
**许可证**: MIT
