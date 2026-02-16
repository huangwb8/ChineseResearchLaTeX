# nsfc-reviewers — 用户使用指南

本 README 面向**使用者**：如何触发并正确使用 `nsfc-reviewers` skill。
执行规范见 `SKILL.md`；默认参数见 `config.yaml`。

## 这是什么

模拟领域专家视角对 NSFC 标书进行多维度评审，输出分级问题与可执行修改建议。

**核心价值**：
- 5 位专家角色（创新性/可行性/基础/严格/建设性）独立评审
- 支持多组并行评审（最多 5 组 × 5 专家 = 25 人次）
- 问题分级（P0 致命 → P1 重要 → P2 建议）+ 证据锚点
- 跨组共识识别 + 最小修改序列

**重要声明**：本技能输出仅用于写作改进与自查，不代表任何官方评审口径，也不构成资助结论。

## 快速开始

### 开发者推荐

```
使用 nsfc-reviewers skill 开 3 组评审团对本标书进行评审，结果保存在 ./ai-reviewers/review-YYYYMMDDHHMM/ 里
```

### 最推荐：让 AI 直接评审

```
请评审 /path/to/your/nsfc_proposal 这个国自然标书
```

### 指定评审组数（增强置信度）

```
请用 3 组评审专家评审 /path/to/your/nsfc_proposal
```

### 保存到指定路径

```
请评审 /path/to/your/nsfc_proposal，把意见保存到 /path/to/review_report.md
```

### 重点关注某维度

```
请评审 /path/to/your/nsfc_proposal，重点关注创新性和可行性
```

## 使用场景

| 你的需求 | 推荐用法 | 说明 |
|---------|---------|------|
| 提交前快速自查 | 1 组评审 | 5 位专家，适合早期版本 |
| 正式提交前准备 | 2-3 组评审 | 跨组共识更可靠 |
| 关键标书深度打磨 | 5 组评审 | 最大覆盖，但成本较高 |
| 定向改进某方面 | `focus=创新性` | 聚焦特定维度 |

## 并行评审模式

默认启用并行多组评审：

- **默认组数**：2 组（10 位专家人次）
- **最大组数**：5 组（25 位专家人次）
- **每组专家**：5 位（创新性/可行性/基础与团队/严格综合/建设性）
- **依赖技能**：`parallel-vibe`（若不可用会自动退化为单组模式）

**成本参考**：
- 每组评审约消耗 5 次完整评审的 token
- 建议：1 组自查 → 2-3 组正式准备 → 5 组关键标书

## 输出文件

默认输出到标书目录下（最终交付一眼可见；中间过程统一隐藏）：

```
/path/to/your/nsfc_proposal/
├── comments-from-nsfc-reviewers.md    # 【最终交付】跨组聚合报告
├── panels/                            # 【最终交付】各组原始评审
│   ├── G001.md
│   ├── G002.md
│   └── ...
└── .nsfc-reviewers/                   # 【中间过程】parallel-vibe 环境、日志与快照
    ├── parallel-vibe/                 # 并行运行环境（按 project_id 归档）
    ├── logs/                          # master prompt 与计划文件（用于追溯）
    │   ├── master_prompt.txt
    │   └── plans/
    └── snapshot/                      # 可选：标书快照
```

说明：
- `comments-from-nsfc-reviewers.md` 的默认文件名见 `config.yaml:output_settings.default_filename`。
- `panels/` 目录名见 `config.yaml:output_settings.panel_dir`。
- `.nsfc-reviewers/` 目录名见 `config.yaml:output_settings.intermediate_dir`。

## 输出整理（强制，推荐脚本）

当你使用并行评审（多组）时，根目录可能会出现 `.parallel_vibe/`、`master_prompt.txt`、`plan*.json` 等中间文件。为保证评审过程可追溯，推荐在最后统一“输出整理”：

```bash
# DRY-RUN：仅打印动作
python3 scripts/finalize_output.py --review-path /path/to/your/nsfc_proposal --panel-count 3

# APPLY：实际整理（会将并行环境/日志/快照迁移到 .nsfc-reviewers/）
python3 scripts/finalize_output.py --review-path /path/to/your/nsfc_proposal --panel-count 3 --apply
```

## 清理中间文件（可选）

当你确认不再需要复现 parallel-vibe 运行过程，或中间文件过大时，可用本技能自带脚本清理：

```bash
# 默认 DRY-RUN：只输出将要执行的动作
python3 scripts/cleanup_intermediate.py --review-path /path/to/your/nsfc_proposal --delete-parallel-vibe

# 实际执行删除（不可逆）
python3 scripts/cleanup_intermediate.py --review-path /path/to/your/nsfc_proposal --delete-parallel-vibe --apply
```

**报告结构**（并行模式）：

```markdown
# 国自然标书评审意见

## 评审配置
- 评审组数：N 组
- 每组专家：5 位
- 总专家人次：N×5 人次

## 跨组共识（多组一致指出）
### P0 级（致命问题）
### P1 级（重要问题）

## 独立观点（单一组提出）
### 来自组 G001

## 修改建议汇总
（按 P0 → P1 → P2 排序的最小修改序列）

## 附录：各组原始评审报告（可选）
```

## 评审维度

来自 `config.yaml:review_dimensions`：

| 维度 | 权重 | 关注点 |
|------|------|--------|
| 创新性评价 | 25% | 原创性、前沿性、颠覆性假说 |
| 科学假说与问题 | 20% | 假说可检验性、问题聚焦度 |
| 研究方案与可行性 | 20% | 技术路线、方法先进性、风险预案 |
| 研究基础 | 15% | 前期工作、论文支撑 |
| 研究团队 | 10% | 背景、分工、协作能力 |
| 预期成果与科学意义 | 10% | 成果可量化、应用前景 |

## 问题分级

| 级别 | 含义 | 处理优先级 |
|------|------|-----------|
| **P0** | 致命问题，严重影响资助判断 | 必须修改 |
| **P1** | 重要问题，显著影响专业印象 | 重点修改 |
| **P2** | 建议改进，不影响主体成立 | 可选优化 |

每条 P0/P1 问题包含：
- **证据锚点**：文件名 + 章节标题/关键句
- **现象**：为什么这是问题
- **影响**：如何影响评审判断
- **建议**：可执行的修改方案
- **验证**：改完如何自检

## 隐私与边界

- 默认将标书视为敏感内容，仅处理你明确给出的路径
- 除非你明确要求，默认不联网、不外发原文大段内容
- 本技能只做文本读取与评审，不执行 LaTeX 编译或其他脚本

## 常见问题

### Q：评审需要多长时间？

单组评审约需 5-10 分钟（取决于标书长度）；多组并行评审会叠加时间，但并行模式下各组可同时执行。

### Q：专家画像是什么？

5 位专家角色分别关注不同维度：
1. **学术前沿与创新性专家**：创新性、科学假说
2. **研究方法与可行性专家**：方法、预期成果
3. **研究基础与团队评估专家**：基础、团队
4. **严格综合评审专家**：全局视角，更挑剔
5. **建设性评审专家**：关注改进空间

### Q：跨组共识如何判定？

默认阈值 60%（见 `config.yaml:parallel_review.aggregation.consensus_threshold`），即 N 组中至少 `ceil(N × 0.6)` 组指出同一问题才认定为跨组共识。

### Q：如何只看 P0 问题？

评审报告按 P0 → P1 → P2 顺序组织，你可以只关注 P0 章节。

## 配置说明

配置文件位于 `config.yaml`：

- `review_dimensions`：评审维度、权重、要点
- `severity_levels`：P0/P1/P2 分级口径
- `parallel_review`：并行评审配置（组数、专家画像引用、聚合策略）
- `output_settings`：输出文件名、`panels/` 目录、中间过程隐藏目录与章节开关；以及输出整理校验（`enforce_output_finalization` / `validation_level`）

专家画像模板位于 `references/expert_*.md`。

## 相关技能

- `parallel-vibe`：并行多工作区执行基础设施
- `nsfc-justification-writer`：立项依据写作
- `nsfc-research-content-writer`：研究内容写作
- `nsfc-research-foundation-writer`：研究基础写作
- `nsfc-roadmap`：技术路线图生成
- `nsfc-schematic`：原理图/机制图生成

---

版本信息见 `config.yaml:skill_info.version`。
