---
name: nsfc-schematic
description: 当用户明确要求"生成 NSFC 原理图/机制图/schematic diagram/mechanism diagram"或需要把标书中的研究机制、算法架构、模块关系转成"可编辑 + 可嵌入文档"的图示时使用。输出可编辑源文件（`.drawio`）和可交付渲染文件（`.svg`/`.png`，可选 `.pdf`），支持多轮评估优化。⚠️ 不适用：用户只是想润色正文文本（应直接改写文本）、只是想改已有图片格式/尺寸（应使用图片处理技能）、没有明确"原理图/机制图"意图。
metadata:
  author: Bensz Conan
  short-description: 生成 NSFC 原理图（drawio + SVG/PNG）
  keywords:
    - nsfc-schematic
    - nsfc
    - schematic
    - mechanism diagram
    - drawio
    - architecture diagram
---

# NSFC 原理图生成器

## 重要声明（非官方）

- 本技能仅用于科研写作与可视化表达优化，不代表任何官方评审口径或资助结论。

## 安全与隐私（硬规则）

- 默认将标书内容视为敏感信息：仅处理用户明确提供的文件或目录。
- 输出图中仅保留科研必要术语，避免写入无关个人信息。
- 默认不联网抓取素材；如用户要求联网补充，应先说明风险。

## 输入

用户至少提供其一：

- `spec_file`：结构化图规格文件（推荐，最可控）
- `proposal_file`：单个标书文件（如 `main.tex` 或 `extraTex/*.tex`）
- `proposal_path`：标书目录（自动搜索 `.tex`）

可选：

- `rounds`：优化轮次（默认见 `config.yaml:evaluation.max_rounds`）
- `output_dir`：输出目录（可选；默认使用 `config.yaml:output.dirname`，相对当前工作目录）
- `config`：配置文件路径（可选；默认使用技能自带 `nsfc-schematic/config.yaml`；用于为某个项目单独覆盖 `output.hide_intermediate` 等参数）
- `context`：自然语言机制描述（仅用于“规划模式”；由 `plan_schematic.py` 生成规划草案与 spec 草案）
- `template_ref`：图类型模板 id/family（高级选项；默认“纯 AI 规划”不需要也不建议设置）

## 输出

在 `output_dir` 下生成（每次运行会创建隔离的 `run_*/round_*`，避免历史残留混入）：

- `schematic.drawio`：可编辑源文件
- `schematic.svg`：矢量图（优先用于文档嵌入）
- `schematic.png`：预览图
- `schematic.pdf`：可选（若启用并渲染器支持）
- `.nsfc-schematic/`：中间产物目录（默认开启隐藏；目录名可配置）
  - `optimization_report.md`：latest 优化记录（每次运行覆盖更新）
  - `spec_latest.yaml`：latest 使用的 spec（便于复现/追溯）
  - `config_used_best.yaml` / `evaluation_best.json`：latest 最佳轮次复现证据
  - `runs/run_YYYYMMDDHHMMSS/`：本次运行目录（含 `round_*`、每轮评估与渲染产物）
  - `legacy/`：自动迁移/收纳的历史残留（如旧版输出的 `run_*`、`spec*.yaml`、`config_*.yaml`、`evaluation_*.json` 等）

默认情况下，`output_dir` 根目录**只保留交付文件**（drawio/svg/png/pdf）与隐藏目录 `.nsfc-schematic/`，避免中间文件污染用户工作目录。

兼容模式：
- 如需恢复旧行为（中间文件与 `run_*` 直接写在 `output_dir` 根目录），设置 `config.yaml:output.hide_intermediate=false`。

每个 `round_*/` 默认会生成以下“可追溯证据”（可通过 `config.yaml:evaluation.*` 关闭）：
- `evaluation.json`：主评估器结果（含 `score_base/score_penalty/score_total`）
- `critique_structure.json / critique_visual.json / critique_readability.json`：多维度批判性自检证据（`evaluation.multi_round_self_check`；仅在启发式评估或 AI 回退路径下生成，避免与 AI 口径重复扣分）
- `_candidates/`：每轮有限候选对比（`evaluation.exploration.candidates_per_round`）

当 `config.yaml:evaluation.evaluation_mode=ai` 时（可选增强），脚本会输出离线协议文件（脚本不在本地调用外部模型）：
- `round_*/_candidates/cand_*/ai_eval_request.md` + `ai_eval_response.json`：AI 评估请求/响应（主评估）
- `run_*/ai_tex_request.md` + `ai_tex_response.json`：当输入来自 TEX 且未提供 spec_file 时，用于“AI 直接读 TEX → 生成 spec 草案”的离线请求/响应（如未响应则自动降级为正则抽取）

规划模式额外交付：
- `schematic-plan.md`：规划草案（写在**当前工作目录**，便于用户快速审阅；可用 `plan_schematic.py --no-workspace-plan` 禁用）

## 工作流

### 读取配置（强制）

开始前读取 `config.yaml`，以此作为执行单一真相来源：

- `renderer`：画布尺寸、字体、渲染行为
- `renderer.drawio`：draw.io CLI 缺失时的提示/（可选）自动安装策略
- `layout`：自动布局参数
- `layout.template_ref`：图类型模板（高级选项；默认不启用；模型画廊仅用于学习，见 `references/models/templates.yaml`）
- `layout.title`：是否将 `spec.title` 落图，以及为标题预留的顶部空间（避免标题配置僵尸化）
- `layout.text_fit`：节点文案“自动扩容”策略（避免导出后文字溢出/遮挡）
- `layout.auto_expand_canvas`：当节点/分组被自动扩容后，是否自动扩展画布以避免越界
- `layout.canvas_fit`：画布拟合策略（可选按内容边界收缩，避免极端比例与大量空白）
- `layout.routing`：路由避让参数（更保守的障碍 padding、避让分组标题栏）
- `layout.font.edge_label_size`：连线标签字号（edge label 不会自动跟随 `node_label_size`，需单独配置）
- `color_scheme`：配色方案
- `evaluation`：评分阈值、停止策略（stop_strategy）、权重与多轮探索参数
- `evaluation.evaluation_mode`：评估模式（默认 `heuristic`；`ai` 为可选增强：输出离线 AI 协议文件并消费宿主 AI 响应；无响应则自动降级）
- `evaluation.thresholds.min_edge_font_px/warn_edge_font_px`：连线标签字号门禁阈值（含缩印等效字号检查）
- `output.hide_intermediate` / `output.intermediate_dir`：中间文件隐藏策略与目录名
- `output.max_history_runs`：最多保留最近 N 次 `run_*`（仅在 hide_intermediate=true 时生效）
- `planning.models_file`：图类型模板库路径（默认 `references/models/templates.yaml`）
- `planning.planning_mode`：规划模式（`ai|template`；默认 `ai`：纯 AI 规划协议）

### 规划模式（推荐首次使用）

当用户首次为标书生成原理图时，推荐先“规划 → 审阅 → 再生成”：

1. 调查标书并生成“规划请求协议”（脚本会综合提取“立项依据 + 研究内容/技术路线”，并生成模型画廊供学习；**不要求选模板**）：

```bash
python3 nsfc-schematic/scripts/plan_schematic.py \
  --proposal /path/to/proposal/ \
  --output ./schematic_plan/
```

（兼容旧流程）如需让脚本按确定性规则直接生成草案（模板规划），使用：

```bash
python3 nsfc-schematic/scripts/plan_schematic.py \
  --mode template \
  --proposal /path/to/proposal/ \
  --output ./schematic_plan/
```

或使用自然语言描述：

```bash
python3 nsfc-schematic/scripts/plan_schematic.py \
  --context "用一句话/一段话描述机制与模块关系..." \
  --output ./schematic_plan/
```

2. 宿主 AI 纯规划：根据 `./schematic_plan/.nsfc-schematic/planning/plan_request.md` 的要求，写出：

- `./schematic_plan/PLAN.md`
- `./schematic_plan/spec_draft.yaml`

（视觉学习可选）规划脚本会（尽力）在 `--output` 目录下生成“模型画廊”（用于学习优秀结构/风格）：

- `./schematic_plan/.nsfc-schematic/planning/models_simple_contact_sheet.png`：骨架/模式图（推荐优先看）
- `./schematic_plan/.nsfc-schematic/planning/models_contact_sheet.png`：完整参考图（用于风格与细节补全）

3. 再次运行规划脚本进行合法性校验（脚本将校验 spec 结构，并给出 P0/WARN 提示）：

```bash
python3 nsfc-schematic/scripts/plan_schematic.py \
  --proposal /path/to/proposal/ \
  --output ./schematic_plan/
```

4. 审阅 `schematic_plan/PLAN.md` 与 `schematic_plan/spec_draft.yaml`：确认模块划分、节点清单、连接关系与布局建议是否合理。
   - 如需手动起草规划草案，可参考：`nsfc-schematic/references/plan_template.md`
5. 用 `generate_schematic.py` 进入多轮生成与优化：

```bash
python3 nsfc-schematic/scripts/generate_schematic.py \
  --spec-file ./schematic_plan/spec_draft.yaml \
  --output-dir ./schematic_output/ \
  --rounds 5
```

### 生成流程（默认入口）

```bash
python3 nsfc-schematic/scripts/generate_schematic.py \
  --spec-file nsfc-schematic/references/spec_examples/ccs_framework.yaml \
  --output-dir ./schematic_output \
  --rounds 5
```

流程拆解：

1. 解析 spec（`spec_parser.py`）并自动补全布局。
2. 生成 draw.io XML（`schematic_writer.py`）。
3. **预检（P0）**：对 `.drawio` 做 XML well-formed 校验；失败则立即停止并给出可读错误。
4. 渲染 SVG/PNG/PDF（`render_schematic.py`）。
5. 评估图质量（`evaluate_schematic.py`），并增强“近空白渲染/内容丢失”的识别与分级。
6. 多维度自检（`evaluate_dimension.py`）：结构/视觉/可读性独立证据落盘，并按缺陷线性扣分得到 `score_total`。
7. 记录每轮结果并导出 best round。

### 脚本职责

- `scripts/spec_parser.py`：解析/校验 spec，补全自动布局，校验边。
- `scripts/schematic_writer.py`：将规范化 spec 转为 draw.io XML。
- `scripts/render_schematic.py`：优先 draw.io CLI 渲染；缺失时内部兜底渲染。
- `scripts/ai_evaluate.py`：生成/消费 AI 评估离线协议（ai_eval_request.md / ai_eval_response.json），不在脚本内调用外部模型。
- `scripts/ai_extract_tex.py`：生成/消费 AI TEX 提取离线协议（ai_tex_request.md / ai_tex_response.json），不在脚本内调用外部模型。
- `scripts/measure_schematic.py`：主评估的“纯度量采集层”（几何/路由/像素 proxy），保留用于启发式评估与降级兜底。
- `scripts/measure_dimension.py`：多维度自检的“纯度量采集层”（structure/visual/readability），保留用于启发式自检与降级兜底。
- `scripts/evaluate_schematic.py`：启发式评估（兜底）；启用 `evaluation_mode=ai` 时输出离线 AI 协议并消费宿主 AI 的评审响应（缺失时自动回退启发式）。
- `scripts/evaluate_dimension.py`：启发式多维度自检（用于 penalty 扣分；当 AI 主评估生效时默认跳过，避免口径重复）。
- `scripts/routing.py`：确定性正交路由（waypoints），用于渲染兜底、drawio 写入与评估口径对齐。
- `scripts/extract_from_tex.py`：从 TEX 抽取术语用于初版 spec 填充。
- `scripts/generate_schematic.py`：一键编排多轮迭代。

## 评估标准

重点检查 6 个维度：

- 文字可读性（字号阈值）
- 节点重叠（交叠比例）
- 箭头完整性（端点有效、交叉数量）
- 画布溢出（越界/贴边）
- 视觉平衡（重心偏移）
- 整体美观（基于渲染产物的本地代理评估）

硬门槛（必须满足，否则视为 P0）：

- **文字不得溢出/被遮挡**：节点文案不应超出节点边界，也不应被连线覆盖（通过 draw.io 元素层级：分组底层、连线中层、节点顶层 来降低风险）。

额外增强维度（更贴近“缩印可读性/审稿人观感”）：

- 长对角线连线惩罚（鼓励更清晰的层次与对齐）
- 连线穿越/贴近节点惩罚（减少穿字/贴字风险）
- 连线标签缩印可读性门禁（edge label 的字号与缩印后等效字号）
- 节点文案拥挤度 proxy（提示缩短文案或增大节点）

AI 自主评估模式（离线协议）

- 触发：设置 `config.yaml:evaluation.evaluation_mode=ai`
- 行为：脚本输出 `ai_eval_request.md` + `ai_eval_response.json`（以及 TEX 场景下的 `ai_tex_request.md` + `ai_tex_response.json`）模板；宿主 AI 可基于 spec+config+PNG/TEX 做语义判定并写回 response；若 response 缺失或不合法，脚本自动回退到启发式评估，保证流程可跑通。

## 失败处理

- draw.io CLI 不可用时：
  - 默认使用内部渲染兜底并给出强提示（内部渲染可用，但最终交付质量通常不如 CLI 导出）；
  - 若 `config.yaml:renderer.allow_internal_fallback=false`，则直接失败并提示安装 draw.io。
- spec 校验失败时：立即返回错误，指出字段路径。

## 维护者自检

- 版本号仅记录在 `config.yaml:skill_info.version`。
- 修改脚本后至少运行 1 组示例（`references/spec_examples/*.yaml`）。
- 新增/调整输出字段时同步更新 README 与 CHANGELOG。

## 交付与自检（交付前必须过）

- A4/屏幕可读（不依赖放大）
- 主流向清晰（上→下 或 左→右）
- 配色 ≤ 3 种主色调（允许辅助灰）
- 节点命名与正文一致
- 输出包含 `schematic.drawio` 与至少一种可嵌入格式（svg 或 png）
- 连线标签可读（缩印后等效字号 ≥ 10px）
