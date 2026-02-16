# nsfc-qc — 用户使用指南

本 README 面向**使用者**：如何触发并正确使用 `nsfc-qc` skill。  
执行规范与硬性约束见 `SKILL.md`；默认参数见 `config.yaml`。

## 这个 skill 做什么

对 NSFC 标书做**只读质量控制（QC）**，输出一份可审核的标准化 QC 报告：
- 文风生硬/不像人类专家写作的片段 → 给“最小改写建议”（只建议，不改稿）
- 引用问题：假引、错引、bib 缺失/不完整 → 给证据链与复核建议
- 篇幅与章节分布：总页数（软约束 30 页）、各章节比例是否失衡
- 逻辑与论证链：是否通顺、条理清晰、论证充分、是否存在歧义/跳步
- 其它常见 QC：术语一致性、缩略语定义、图表引用、夸大措辞等

## 只读声明（重要）

`nsfc-qc` **不会修改你的标书内容**（不改任何 `.tex/.bib/.cls/.sty`）。  
所有中间文件与报告都会写入 `project_root/.nsfc-qc/`，便于后续审核与追溯。

## 最推荐用法（最少信息）

```
请用 nsfc-qc 对 projects/NSFC_Young 做一次质量控制。要求：
- 开 5 个 thread（串联模式）
- 输出标准化 QC 报告
- 不允许修改标书任何内容
```

## 常见用法

### 1) 指定主入口 tex

```
请用 nsfc-qc 检查 projects/NSFC_Young，主文件是 main.tex。
```

### 2) 明确要重点核查“引用真伪/错引”

```
请用 nsfc-qc 对 projects/NSFC_Young 做 QC，并把“引用真伪/错引风险”作为最高优先级（P0/P1）。
```

### 3) 用户明确要求并行（否则默认串联）

```
请用 nsfc-qc 对 projects/NSFC_Young 做 QC：5 threads，并行跑（最多同时 3 个）。
```

## 你会得到什么输出

每次运行会创建一个 run 目录（`run_id` 为时间戳）：
- `project_root/.nsfc-qc/runs/{run_id}/final/nsfc-qc_report.md`（最终报告）
- `project_root/.nsfc-qc/runs/{run_id}/final/nsfc-qc_metrics.json`（指标）
- `project_root/.nsfc-qc/runs/{run_id}/final/nsfc-qc_findings.json`（结构化问题清单）

如果启用了 parallel-vibe，中间产物也会被归档在同一个 run 目录下的：
- `project_root/.nsfc-qc/runs/{run_id}/.parallel_vibe/...`

## 适用范围与限制

- 本 skill 适用于：NSFC 青年/面上/地区等正文标书（LaTeX 项目）。
- 若环境缺少 `parallel-vibe` 或对应 runner CLI，本 skill 会降级为单线程 QC，但仍输出同样的标准化报告，并在附录说明原因。

