---
name: nsfc-roadmap
description: 当用户明确要求"生成 NSFC 技术路线图/技术路线图绘制/roadmap/flowchart"或需要把标书研究内容转成"可打印、A4 可读"的技术路线图时使用。输出可编辑源文件（`.drawio`）与可嵌入文档的渲染结果（`.svg`/`.png`/`.pdf`）。⚠️ 不适用：用户只是想修改某张已有图片的格式/尺寸（应使用图片处理技能）、只是想润色技术路线文字描述（应直接改写正文）。
metadata:
  author: Bensz Conan
  short-description: 生成 NSFC 技术路线图（drawio + SVG/PNG/PDF）
  keywords:
    - nsfc-roadmap
    - nsfc
    - roadmap
    - flowchart
    - drawio
    - svg
---

# NSFC 技术路线图生成器

## 重要声明（非官方）

- 本技能生成的技术路线图仅用于写作与展示优化，不代表任何官方评审口径或资助结论。

## 安全与隐私（硬规则）

- 默认将标书内容视为敏感信息：仅处理用户明确提供的文件/目录；不擅自扩展扫描范围。
- 输出中避免复述不必要的个人信息/单位信息；图中节点仅保留科研相关内容。
- 默认不联网获取外部数据；若用户明确要求联网补充素材，先提醒风险再执行。

## 输入

用户至少提供其一：

- `proposal_path`：标书目录（包含 `.tex` / `.md` 等；推荐，AI 将自动读取立项依据与研究内容）
- `proposal_file`：单个输入文件（仅在无法提供目录时使用；推荐优先提供 `proposal_path`）
- `spec_file`：结构化图规格文件（推荐，便于可控迭代）

可选：

- `rounds`：评估-优化轮次（默认 5，单一真相来源见 `config.yaml:evaluation.max_rounds`）
- `output_dir`：输出目录（默认在当前工作目录下创建 `roadmap_output/`）
- `layout`：布局模板名（默认 `auto`，见 `config.yaml:layout`；支持 `classic/three-column/layered-pipeline`）
- `template_ref`：具体模板 id（如 `model-02`；高级选项；默认“纯 AI 规划”不需要也不建议设置）

## 输出

在 `output_dir` 下生成（默认启用隐藏中间产物）：

- **交付根目录（可直接交付）**：
  - `roadmap.drawio`：draw.io 可编辑源文件（用于人工微调）
  - `roadmap.svg`：矢量输出（优先用于 LaTeX/Word 嵌入）
  - `roadmap.png`：高分辨率位图（用于预览与兜底）
  - `roadmap.pdf`：默认生成（无 draw.io CLI 时为 PNG→PDF 栅格降级）
  - `roadmap-plan.md`：规划阶段产出（可审阅/修改）
- **隐藏中间产物**：`output_dir/.nsfc-roadmap/`
  - `runs/run_YYYYMMDDHHMMSS/`：本次运行隔离目录（包含各轮 `round_XX/`）
    - `round_XX/measurements.json`：纯度量采集（密度/溢出/阶段平衡/连线/字体等；不含 P0/P1/P2 判定）
    - `round_XX/dimension_measurements.json`：structure/visual/readability 三维度度量（供宿主 AI 语义解读）
    - `round_XX/critique_structure.json`：结构完整性评估（术语一致性/重复节点/阶段合理性等）
    - `round_XX/critique_visual.json`：视觉美学评估（对比度/配色区分度等）
    - `round_XX/critique_readability.json`：人类可读性评估（字号门槛/密度分布/边缘拥挤等）
  - `spec_latest.yaml`：最新 spec 快照（可复现）
  - `optimization_report.md`：迭代记录（每轮缺陷与修改点）
  - `config_used_best.yaml` / `evaluation_best.json`：best round 复现证据
  - `config_local.yaml`：实例级局部配置覆盖（白名单字段；用于“只覆盖本次图参数/停止策略”，不改全局 `config.yaml`；其中 `color_scheme.name` 仅允许 `{academic-blue, tint-layered}`）
  - `ai/`：AI 证据包与 request/response 协议（仅在 `stop_strategy=ai_critic` 工作流中使用）
    - `ai/ACTIVE_RUN.txt`：当前 ai_critic 活跃 run（用于 resume）
    - `ai/{run_dir}/ai_pack_round_XX/`：本轮 AI 证据包（供宿主 AI 读图批判）
    - `ai/{run_dir}/ai_critic_request.md`：宿主 AI 请求（固定格式）
    - `ai/{run_dir}/ai_critic_response.yaml`：宿主 AI 响应（结构化：spec/config_local patch + stop/continue）

## 工作流（执行规范）

### 读取配置（强制）

开始前先读取本技能目录下 `config.yaml`，以下字段作为执行时单一真相来源：

- `renderer`：输出尺寸与格式、字体与配色
- `evaluation`：最大轮次与提前终止规则
- `layout`：布局与字号门槛
- `color_scheme`：配色方案

### 阶段一：规划（推荐）

若你已准备好 `spec_file`，可跳过规划阶段。

#### 纯 AI 规划（默认）

本技能默认启用 `config.yaml:planning.planning_mode=ai`：规划阶段不要求/不建议选择单一 `template_ref`。

工作流：

1. 运行 `plan_roadmap.py` 生成规划请求协议（`plan_request.json/plan_request.md` + 模型画廊）。
2. 宿主 AI 按 `plan_request.md` 写出 `roadmap-plan.md + spec_draft.yaml`。
3. 再次运行 `plan_roadmap.py`，脚本将校验 `spec_draft.yaml` 是否满足 `scripts/spec.py:load_spec()` 约束。

（兼容旧流程）如需让脚本按确定性规则直接生成草案（模板规划），使用 `--mode template` 或设置 `planning_mode=template`。

#### 步骤 1：调查标书

读取标书目录下的关键 tex 文件，彻底了解整个标书的情况。至少读取：

- `extraTex/1.立项依据.tex`（或等效文件）：研究背景、科学问题、研究假说
- `extraTex/2.1.研究内容.tex`（或等效文件）：具体研究内容、技术路线

仅看研究内容是不够的；立项依据提供了科学逻辑的全貌，有助于更准确地把握路线图的叙事结构与路线叙事设计。

#### 步骤 2：视觉参考（学习优秀结构），生成 roadmap-plan.md

优先基于“视觉参考”来学习优秀结构（不要求也不建议固定到某个 `template_ref`）：

- 运行规划脚本后，查看 `output_dir/.nsfc-roadmap/planning/models_contact_sheet.png`（模型画廊 contact sheet）
- 或直接查看 `references/models/` 下的单张参考图

然后在 `roadmap-plan.md` 中明确写出：

- 视觉/结构学习点（例如：分区方式、主链走向、信息密度控制、配色层级）
- 路线图整体结构设计（分区/列/主线、节点密度上限、配色层级等）

#### 步骤 3：生成 spec.yaml

基于 `roadmap-plan.md` 生成 `spec.yaml`（结构化图规格），必须满足：

- 3–5 个阶段（phases），每个阶段 2–6 个节点（boxes）
- 术语与正文一致（同一概念不出现多种叫法）
- 输入输出闭合（每个模块/关键节点有明确产出）
- 风险与备选方案可见（至少 1 个风险/对照节点）

### 阶段二：从 roadmap-plan.md 落到 spec（结构化图规格）

优先路径（按优先级）：

1. **用户提供 `spec_file`**：直接使用（可控、可复现）
2. **阶段一已完成**：使用阶段一生成的 `spec.yaml`（或脚本规划产物 `spec_draft.yaml`）
3. **跳过阶段一**：从输入文件中自动抽取"研究内容/技术路线"相关段落生成初版 spec

模板字段（可选，推荐在 spec 中记录以便可复现与复盘）：

- `layout_template: auto|classic|three-column|layered-pipeline`（可选；不写也可以）
- `template_ref: model-01..model-10`（可选；默认不建议使用，以避免把复杂场景“框死”在单一模板上）

### 阶段三：渲染（确定性脚本）

目标：以 `spec.yaml` 为单一真相来源，确定性生成交付文件（drawio + svg/png/pdf）。

运行（示例）：

```bash
python3 nsfc-roadmap/scripts/generate_roadmap.py \
  --spec-file ./roadmap_output/spec.yaml \
  --output-dir ./roadmap_output \
  --rounds 5
```

脚本职责：

- 将最新 spec 固化到 `output_dir/.nsfc-roadmap/spec_latest.yaml`
- 输出 `roadmap.drawio`（可编辑源文件）
- 输出 `roadmap.svg` / `roadmap.png` / `roadmap.pdf`（交付结果）

### 阶段四：评估-优化循环（默认 5 轮）

目标：围绕阶段一在 `roadmap-plan.md` 中声明的叙事与版式约束，迭代改进可读性与专业感；必要时回写 spec 并复跑。

每轮必须产出结构化缺陷清单（建议 JSON）：

- `P0`：会被评审直接扣分（缺研究内容、逻辑断裂、孤立节点、不可读）
- `P1`：显著影响专业印象（布局混乱、重叠、刺眼配色、字号过小）
- `P2`：一般优化（间距不均、边距偏小、箭头不清晰、信息拥挤）

纠偏原则（避免“越优化越不可读”）：

- **density（拥挤）通常是内容问题**：优先改 `spec`（缩短节点文案/合并相近节点/减少节点数）；不要用缩字号来“通过阈值”。
- **overflow 才是缩字号的正确触发条件**：出现文字溢出/接近溢出时，才考虑减字号或增大 box 高度。
- **字号偏小应增大字体**：当评估为“字号偏小/过小”且没有 overflow 风险时，应增大字号，优先保证 A4 打印可读。
- **配色干扰是 spec 层面的 kind 分配问题**：优先减少 kind 种类、修正 kind 语义；不要用切换到黑白方案替代结构修正。

停止策略以 `config.yaml:evaluation` 为准：

- `early_stop`：legacy 提前终止规则（可选开启）
- `stop_strategy: plateau`：默认启用的“平台期停止”（基于 PNG 哈希与分数提升阈值）
- `stop_strategy: ai_critic`：AI 自主闭环（脚本不调用外部模型；每轮生成 request 并暂停等待宿主 AI 的 response）

评估模式以 `config.yaml:evaluation.evaluation_mode` 为准：

- `heuristic`（默认）：脚本启发式评估 + 多维度自检（可复现、可离线）
- `ai`：额外导出纯度量证据 `measurements.json/dimension_measurements.json` 供宿主 AI 解读（常与 `stop_strategy=ai_critic` 搭配）

补充：多维度自检（默认启用，配置见 `config.yaml:evaluation.multi_round_self_check`）：

- 在每轮渲染后并行运行 `structure/visual/readability` 三个维度评估
- 每个维度产出独立的 `critique_*.json`，并汇总进 `evaluation.json`
- 评分采用“基础评估分数 - 维度缺陷惩罚”的保守策略，避免遗漏人类感知问题

### AI 自主闭环（可选：stop_strategy=ai_critic）

当你希望把“怎么画图/是否继续/改哪儿”交给宿主 AI 决策时，启用 `ai_critic` 模式：

- 在本次输出目录的隐藏中间产物里创建/编辑：`output_dir/.nsfc-roadmap/config_local.yaml`
- 在其中设置：`evaluation.stop_strategy: ai_critic`（这是实例级开关，不改全局 `config.yaml`）
- 运行 `generate_roadmap.py` 后脚本会：
  - 只渲染 1 轮（或在已有 run 上继续渲染下一轮）
  - 生成证据包：`output_dir/.nsfc-roadmap/ai/{run_dir}/ai_pack_round_XX/`（含 `roadmap.png/spec_latest.yaml/config_used.yaml/evaluation.json/measurements.json/dimension_measurements.json/critique_*.json`）
  - 写出固定请求：`ai_critic_request.md`
  - 暂停等待你（宿主 AI）写入：`ai_critic_response.yaml`
- 你把宿主 AI 的结构化响应写入 `ai_critic_response.yaml` 后，再次运行脚本即可自动应用 patch 并进入下一轮。

#### ai_critic_response.yaml 最小协议（version=1）

```yaml
version: 1
based_on_round: 1
action: both  # spec_only|config_only|both|stop
reason: "一句话说明本轮行动与停止/继续依据"

# 推荐：直接给完整 spec（避免 patch 合并歧义）
# spec:
#   title: ...
#   phases: ...

# 可选：给 config_local patch（仅允许 renderer/layout/color_scheme/evaluation.stop_strategy 的安全子集）
# config_local:
#   color_scheme:
#     name: tint-layered
```

### 阶段五：交付与自检

交付前自检清单：

- A4 可读（不依赖放大）
- 主流向清晰（上→下、左→右）
- 配色 ≤ 3 种主色调（允许辅助灰）
- 节点命名与正文一致
- 输出包含 `roadmap.drawio` 与至少一种可嵌入格式（`svg` 或 `png`）
