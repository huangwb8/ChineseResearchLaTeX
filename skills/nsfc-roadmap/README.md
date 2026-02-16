# nsfc-roadmap — 用户使用指南

本 README 面向**使用者**：如何触发并正确使用 `nsfc-roadmap` skill。
执行规范见 `SKILL.md`；默认参数见 `config.yaml`。

## 这是什么

为 NSFC 标书生成可打印、A4 可读的技术路线图，输出 `.drawio` 可编辑源文件与 `.svg`/`.png`/`.pdf` 渲染结果。

**核心价值**：
- 从标书 `.tex` 自动抽取研究内容 → 生成结构化 spec
- 多轮评估-优化循环（默认 5 轮），自动提升图面质量
- 多维度批判性自检：结构/视觉/可读性（默认启用，结果可追溯）
- 输出 draw.io 源文件，可继续人工微调
- 默认生成“主线箭头”（`Phase1 → Phase2 → …`），让成品更像路线图而不是贴纸盒子
- A4 打印可读（字号、间距、配色均针对打印优化）

**重要声明**：本技能生成的技术路线图仅用于写作与展示优化，不代表任何官方评审口径或资助结论。

## 快速开始

### 最推荐：从标书直接生成

```
请为 /path/to/your/nsfc_proposal 生成技术路线图
```

### 先规划再生成（推荐用于评审）

```
请先为 /path/to/your/nsfc_proposal 生成 roadmap-plan.md
```

> 提示：规划阶段需要提供 `proposal_path` / `proposal_file` / `context` 其一。

可选：如果你希望由宿主 AI 自主完成阶段划分与 spec 草案生成，可启用 `config.yaml:planning.planning_mode: ai`（或脚本 `plan_roadmap.py --mode ai`），脚本会输出 `plan_request.json` 并等待你写入 `roadmap-plan.md + spec_draft.yaml`。

### 指定输出目录

```
请为 /path/to/your/nsfc_proposal 生成技术路线图，输出到 ./roadmap_output/
```

### 选择模板风格（推荐）

本技能内置了 6 个“模板参考图”（见 `references/models/`），并支持两类模板家族（family）：

- `three-column`：三列式（左右支撑 + 中央主线）
- `layered-pipeline`：分层流水线（纵向主链 + 横向模块）

你可以直接说：

```
请按 three-column 风格生成技术路线图
```

或更具体地说：

```
请按模板 model-02 的风格生成技术路线图
```

> 说明：模板用于“参考而非照搬”，渲染器承诺的是“模板家族级别的稳定骨架”，不追求像素级复刻。

### 备选用法：脚本调用

```bash
python3 nsfc-roadmap/scripts/generate_roadmap.py \
  --proposal-file /path/to/extraTex/2.1.研究内容.tex \
  --output-dir ./roadmap_output \
  --rounds 5
```

## 适用场景

| 你的需求 | 推荐用法 | 说明 |
|---------|---------|------|
| 首次生成路线图 | 从标书目录直接生成 | 自动抽取研究内容 |
| 精细控制节点/连线 | 编辑 `spec_draft.yaml` 或 `spec_latest.yaml` 后重新生成 | 可复现、可迭代 |
| 快速微调 | 用 draw.io 打开 `.drawio` 编辑 | 人工精修 |
| 多轮优化 | 增加 `--rounds` 到 7-10 | 追求最佳效果 |

## 技术路线图 vs 原理图

| 特征 | 技术路线图 (nsfc-roadmap) | 原理图 (nsfc-schematic) |
|------|--------------------------|------------------------|
| 结构 | 线性阶段 + 并行任务 | 层次分组 + 任意连线 |
| 布局 | 上→下 / 左→右 流程 | 输入层→处理层→输出层 |
| 适用 | 时间线、里程碑、阶段划分 | 机制、算法架构、模块关系 |
| 例子 | 三年研究计划、实验流程图 | 深度学习架构、信号通路 |

## 输出文件

```
roadmap_output/
├── roadmap.drawio           # 可编辑源文件（推荐用 draw.io 打开）
├── roadmap.svg              # 矢量图（优先用于 LaTeX/Word 嵌入）
├── roadmap.png              # 高分辨率位图（用于预览）
├── roadmap.pdf              # 默认输出（无 CLI 时为 PNG→PDF 栅格降级）
├── roadmap-plan.md          # 规划草案（可审阅/修改）
└── .nsfc-roadmap/           # 中间产物（默认隐藏）
    ├── config_local.yaml     # 实例级局部配置覆盖（白名单字段；不改全局 config.yaml）
    ├── runs/
    │   └── run_YYYYMMDDHHMMSS/
    │       ├── round_01/
    │       │   ├── measurements.json            # 纯度量采集（不含 P0/P1/P2 判定，供宿主 AI 解读）
    │       │   ├── dimension_measurements.json  # structure/visual/readability 三维度度量
    │       │   ├── critique_structure.json
    │       │   ├── critique_visual.json
    │       │   ├── critique_readability.json
    │       │   └── evaluation.json
    │       ├── round_02/
    │       └── ...
    ├── spec_latest.yaml
    ├── optimization_report.md
    ├── config_used_best.yaml
    ├── evaluation_best.json
    ├── planning/              # planning_mode=ai 时生成：规划 request 协议
    │   ├── plan_request.json
    │   └── plan_request.md
    └── ai/                   # stop_strategy=ai_critic 时生成：证据包 + request/response
        ├── ACTIVE_RUN.txt
        └── run_YYYYMMDDHHMMSS/
            ├── ai_pack_round_01/
            ├── ai_critic_request.md
            └── ai_critic_response.yaml
```

## 迭代流程

1. **规划**：运行 `plan_roadmap.py` 生成 `roadmap-plan.md` + `spec_draft.yaml`
2. **生成初版**：基于草案/标书抽取内容 → 渲染
3. **评估**：检查字号、重叠、溢出、平衡等问题
4. **优化**：调整布局、间距、配色
5. **重复 3-4**：直到达到停止条件或跑满 rounds
6. **交付**：导出 best round 的 `.drawio` / `.svg` / `.png` / `.pdf`

## 停止策略

默认使用"平台期停止"（`config.yaml:evaluation.stop_strategy: plateau`）：

- 至少跑过 4 轮探索
- 当候选图不再变化（PNG 哈希不变）或分数停滞时停止
- 最多跑满 `config.yaml:evaluation.max_rounds`（默认 5）

可选启用 AI 自主闭环（`evaluation.stop_strategy: ai_critic`）：

- 脚本每次只渲染/评估 1 轮，并在 `output_dir/.nsfc-roadmap/ai/{run_dir}/` 生成证据包与 `ai_critic_request.md`
- 你（宿主 AI）阅读证据包后，把结构化响应写入 `ai_critic_response.yaml`（spec/config_local patch + stop/continue）
- 再次运行脚本即可自动应用 patch 并进入下一轮（不在脚本内调用外部模型 API）

> 推荐做法：把 `evaluation.stop_strategy: ai_critic` 写到 `output_dir/.nsfc-roadmap/config_local.yaml`，作为“仅本次实例生效”的开关。

补充：若启用 `evaluation.evaluation_mode: ai`（常与 `ai_critic` 搭配），每轮会额外导出 `measurements.json/dimension_measurements.json`，把“度量证据”与“阈值判定”解耦，便于宿主 AI 做上下文判断。

## 多维度自检

默认启用多维度自检（见 `config.yaml:evaluation.multi_round_self_check`）：

- `structure`：结构完整性（阶段/节点合理性、重复节点、术语一致性等）
- `visual`：视觉美学（对比度、配色区分度、打印可见性等）
- `readability`：人类可读性（字号门槛、密度分布、边缘拥挤/裁剪风险等）

每轮的自检结果会写入 `round_XX/critique_*.json`，并汇总进同目录的 `evaluation.json`。

## 评估标准

| 级别 | 问题类型 | 示例 |
|------|---------|------|
| **P0** | 致命缺陷 | 缺研究内容、逻辑断裂、孤立节点、不可读 |
| **P1** | 显著影响 | 布局混乱、重叠、配色刺眼、字号过小 |
| **P2** | 一般优化 | 间距不均、边距偏小、箭头不清晰 |

## 配色方案

默认使用 `academic-blue`（见 `config.yaml:color_scheme`）：

| 节点类型 | 填充色 | 边框色 | 用途 |
|---------|-------|-------|------|
| primary | #D9E8FF | #2F5597 | 主要研究内容 |
| secondary | #DAF2D0 | #2E7D32 | 辅助/支撑内容 |
| decision | #FFF2CC | #B07D00 | 决策/分支节点 |
| critical | #E8DFF2 | #6A4C93 | 关键节点 |
| risk | #F8D7DA | #B23A48 | 风险/备选方案 |
| auxiliary | #F2F2F2 | #666666 | 辅助说明 |

另提供两个预设（可在 `config.yaml:color_scheme.name` 切换）：

- `outline-print`：白底 + 彩色描边（更接近“打印友好”的清爽风格）
- `tint-layered`：低饱和浅填充（更适合 `layered-pipeline` 的分层/分区感）

## 常见问题

### Q：如何修改节点内容？

优先编辑 `.nsfc-roadmap/spec_latest.yaml` 或规划阶段生成的 `spec_draft.yaml`，然后重新运行生成脚本。这样可以保持可复现性。

### Q：生成后想微调布局怎么办？

用 draw.io 打开 `roadmap.drawio`，可以直接拖拽节点、修改文字、调整连线。

### Q：为什么图太小/太挤？

检查 `config.yaml:renderer.canvas` 中的画布尺寸，可以增大 `width_px` 和 `height_px`。

### Q：如何只生成不优化？

设置 `--rounds 1`，跳过多轮评估-优化循环。

### Q：导出的 SVG/PNG 中文显示异常？

确保本机安装了中文字体（见 `config.yaml:renderer.fonts.candidates`）。

## 隐私与边界

- 默认将标书内容视为敏感信息，仅处理你明确提供的文件/目录
- 输出图中仅保留科研必要术语，避免写入无关个人信息
- 默认不联网获取外部数据

## 配置说明

配置文件位于 `config.yaml`：

- `renderer`：输出尺寸、字体、配色
- `evaluation`：最大轮次、停止策略、评估阈值
- `layout`：布局模板、间距、字号（支持 `layout.template: auto|classic|three-column|layered-pipeline`；可选 `layout.template_ref: model-02`）
- `color_scheme`：配色方案

### spec 的可选字段（高级）

当你需要更“稳态”的阶段标题条（尤其 `three-column` / `layered-pipeline`），可在 spec 的 phase 上写入：

- `phase_header_override`: 用于覆盖/补充阶段标题条文本（建议短句；用于承载 tex 抽取的条目标题摘要）

## 相关技能

- `nsfc-schematic`：原理图/机制图生成
- `nsfc-reviewers`：标书评审
- `nsfc-justification-writer`：立项依据写作
- `nsfc-research-content-writer`：研究内容写作

---

版本信息见 `config.yaml:skill_info.version`。
