# nsfc-schematic — 用户使用指南

本 README 面向**使用者**：如何触发并正确使用 `nsfc-schematic` skill。
执行规范见 `SKILL.md`；默认参数见 `config.yaml`。

## 这是什么

将 NSFC 标书中的机制描述、算法结构、模块关系转成可交付原理图，输出 `.drawio` 可编辑源文件与 `.svg`/`.png` 渲染结果。

**核心价值**：
- 支持分组（输入层/处理层/输出层）+ 任意连线
- 多轮评估-优化循环（默认 5 轮），自动提升图面质量
- 节点文案自动扩容，避免导出后文字溢出/遮挡
- 图类型模板库（5 类常用骨架 + 多个 `model-xx` 视觉参考）+ 规划阶段自动选型，提升“第一次就画对”的概率
- 输出 draw.io 源文件，可继续人工微调

**重要声明**：本技能仅用于科研写作与可视化表达优化，不代表任何官方评审口径或资助结论。

## 快速开始

### 最推荐：规划模式（首次使用）

```
请为 /path/to/your/nsfc_proposal 生成原理图
```

AI 会先生成规划草案（`PLAN.md`）和 spec 草案（`spec_draft.yaml`），你审阅后再进入生成。

### 从已有 spec 直接生成

```
请用 ./schematic_plan/spec_draft.yaml 生成原理图，输出到 ./schematic_output/
```

### 指定优化轮次

```
请为 /path/to/your/nsfc_proposal 生成原理图，优化 7 轮
```

## 适用场景

| 你的需求 | 推荐用法 | 说明 |
|---------|---------|------|
| 首次生成原理图 | 规划模式 | 先审阅 PLAN.md 再生成 |
| 已有 spec 草案 | 直接生成 | 可控、可复现 |
| 快速预览效果 | `--rounds 1` | 跳过优化循环 |
| 精细控制分组/连线 | 编辑 `spec.yaml` | 结构化迭代 |
| 人工微调 | 用 draw.io 编辑 `.drawio` | 最终精修 |

## 原理图 vs 技术路线图

| 特征 | 原理图 (nsfc-schematic) | 技术路线图 (nsfc-roadmap) |
|------|------------------------|--------------------------|
| 结构 | 层次分组 + 任意连线 | 线性阶段 + 并行任务 |
| 布局 | 输入层→处理层→输出层 | 上→下 / 左→右 流程 |
| 适用 | 机制、算法架构、模块关系 | 时间线、里程碑、阶段划分 |
| 例子 | 深度学习架构、信号通路 | 三年研究计划、实验流程图 |

## 输出文件

默认启用"隐藏中间文件"（`config.yaml:output.hide_intermediate=true`）：

```
schematic_output/
├── schematic.drawio         # 可编辑源文件（推荐用 draw.io 打开）
├── schematic.svg            # 矢量图（优先用于 LaTeX/Word 嵌入）
├── schematic.png            # 预览图
├── schematic.pdf            # 默认尝试导出（需 draw.io CLI；否则仅导出 svg/png）
└── .nsfc-schematic/         # 隐藏目录（中间产物）
    ├── optimization_report.md
    ├── spec_latest.yaml
    ├── config_used_best.yaml
    ├── evaluation_best.json
    ├── ai/                  # ai_critic 闭环工作区（ACTIVE_RUN / ai_pack / request/response）
    └── runs/
        └── run_YYYYMMDDHHMMSS/
            ├── round_01/
            ├── round_02/
            └── ...
```

每个 `round_*/` 默认会包含：
- `evaluation.json`：本轮评估结果（含 `score_base/score_penalty/score_total`）
- `layout_debug.json`：布局诊断（节点/分组几何信息）
- `edge_debug.json`：连线诊断（edge id、kind、route、waypoints）
- `measurements.json`：主评估纯度量证据
- `dimension_measurements.json`：结构/视觉/可读性维度证据
- `critique_structure.json / critique_visual.json / critique_readability.json`：多维度自检证据（可在 `config.yaml:evaluation.multi_round_self_check` 关闭）
- `_candidates/`：每轮有限候选对比（数量见 `config.yaml:evaluation.exploration.candidates_per_round`）

兼容模式：如需中间文件直接写在输出根目录，设置 `config.yaml:output.hide_intermediate=false`。

## 规划模式（推荐首次使用）

当你首次为标书生成原理图时，推荐"规划 → 审阅 → 再生成"：

### 步骤 1：生成规划请求（纯 AI 规划协议）

```bash
python3 nsfc-schematic/scripts/plan_schematic.py \
  --proposal /path/to/proposal/ \
  --output ./schematic_plan/
```

当 `--proposal` 为目录且包含标准 NSFC 结构（如 `extraTex/1.1.立项依据.tex` + `extraTex/2.1.研究内容.tex`）时，规划阶段会优先综合提取两者用于术语提示与规划证据。

或用自然语言描述：

```bash
python3 nsfc-schematic/scripts/plan_schematic.py \
  --context "描述你的机制与模块关系..." \
  --output ./schematic_plan/
```

该命令会在 `./schematic_plan/.nsfc-schematic/planning/` 下生成 `plan_request.md/plan_request.json` 与“模型画廊”（contact sheet）。随后由宿主 AI 写出 `PLAN.md + spec_draft.yaml`，再复跑脚本完成合法性校验。

（兼容旧流程）如需让脚本按确定性规则直接生成草案（模板规划），加 `--mode template`。

### 步骤 2：宿主 AI 写出规划与 spec 草案

根据 `./schematic_plan/.nsfc-schematic/planning/plan_request.md` 的要求，写出：

- `./schematic_plan/PLAN.md`
- `./schematic_plan/spec_draft.yaml`

可选：为便于审阅，也可在当前工作目录额外写出扁平交付文件 `schematic-plan.md`（同名覆盖更新）。

模型画廊用于学习优秀结构与视觉风格（不要求也不建议把复杂场景固定到单一 `template_ref`）：

- `models_simple_contact_sheet.png`：骨架/模式图（推荐优先看，更利于抓住 schematic 的基础架构）
- `models_contact_sheet.png`：完整参考图（用于风格与细节补全）

### 步骤 3：复跑脚本做合法性校验

再次运行同一条命令即可校验（脚本将检查 spec 结构合法性，并给出 P0/WARN 提示）：

```bash
python3 nsfc-schematic/scripts/plan_schematic.py \
  --proposal /path/to/proposal/ \
  --output ./schematic_plan/
```

然后打开 `schematic-plan.md`（如你有生成）或 `schematic_plan/PLAN.md`，确认：
- 模块划分是否合理
- 节点命名是否与正文一致
- 连线关系是否准确

### 步骤 4：按需修改 spec

编辑 `schematic_plan/spec_draft.yaml`，调整节点、连线、分组。

### 步骤 5：生成原理图

```bash
python3 nsfc-schematic/scripts/generate_schematic.py \
  --spec-file ./schematic_plan/spec_draft.yaml \
  --output-dir ./schematic_output \
  --rounds 5
```

## 直接生成（已有 spec）

```bash
python3 nsfc-schematic/scripts/generate_schematic.py \
  --spec-file nsfc-schematic/references/spec_examples/ccs_framework.yaml \
  --output-dir ./schematic_output \
  --rounds 5
```

或从标书 TEX 直接生成（自动抽取）：

```bash
python3 nsfc-schematic/scripts/generate_schematic.py \
  --proposal-file /path/to/main.tex \
  --output-dir ./schematic_output
```

## Spec v2（兼容旧版）

- `node.id` 可选：未提供时脚本会按 `group + label + index` 生成稳定 id（可复现）。
- `edges` 支持显式边协议（推荐复杂图使用）：

```yaml
edges:
  - id: e_input_core
    from: input_layer.data_input
    to: process_layer.core_module
    kind: main        # main|aux|risk|validate
    route: orthogonal # orthogonal|straight|auto
    label: 输入数据
```

- 渲染优先级：提供 `edges` 时严格按显式边；不提供时回退 `layout.auto_edges`（`minimal|off`）。

## 出版级图面

本技能针对"缩印后可读性"做了多项优化：

- **节点文案自动扩容**：避免导出后文字溢出或贴边（见 `config.yaml:layout.text_fit`）
- **元素层级保护**：分组底层、连线中层、节点顶层，降低"线压字"风险
- **连线标签门禁**：edge label 字号单独配置，并检查缩印 50% 后的等效字号
- **标题落图**：默认将 `spec.title` 写入图中（可关闭：`config.yaml:layout.title.enabled=false`）

## 停止策略

默认使用"平台期停止"（`config.yaml:evaluation.stop_strategy: plateau`）：

- 至少跑过 4 轮探索
- 当候选图不再变化（PNG 哈希不变）或分数停滞时停止
- 最多跑满 `config.yaml:evaluation.max_rounds`（默认 5）

可选：`stop_strategy: ai_critic`
- 每次运行只推进 1 轮，并在 `.nsfc-schematic/ai/{run}/` 生成 `ai_pack_round_XX/` 与 `ai_critic_request.md`
- 宿主 AI 按协议写回 `ai_critic_response.yaml`（`spec_only|config_only|both|stop`），再次运行脚本自动续跑
- `config_local.yaml` 补丁会做白名单校验（安全子集），脚本不在本地调用任何外部模型

## AI 自主评估模式（离线协议）

默认评估为启发式模式（`config.yaml:evaluation.evaluation_mode: heuristic`）。如需启用 AI 离线协议增强，可设置为 `ai`（无响应自动回退启发式，保证生成流程可跑通）。

- 开关：`config.yaml:evaluation.evaluation_mode: ai`
- 产物：在每个 `round_*/_candidates/cand_*/` 下生成
  - `ai_eval_request.md` + `ai_eval_response.json`
- 用法：宿主 AI 读取 `ai_eval_request.md`（必要时用 Read 工具查看 PNG），把结构化评审结果写回 `ai_eval_response.json`
- 兜底：若 response 缺失或不合法，脚本会自动回退到启发式评估，保证生成流程可跑通

TEX 场景（未提供 `--spec-file` 且启用 AI 模式）：
- 脚本会在 `run_*/` 下生成 `ai_tex_request.md` + `ai_tex_response.json`，允许宿主 AI 直接读 TEX 并输出 `spec_draft`；无响应则自动降级为正则抽取术语。

## 评估标准

重点检查 6 个维度：

| 维度 | 检查内容 |
|------|---------|
| 文字可读性 | 字号阈值、缩印后等效字号 |
| 节点重叠 | 交叠比例 |
| 箭头完整性 | 端点有效、交叉数量 |
| 画布溢出 | 越界/贴边 |
| 视觉平衡 | 重心偏移 |
| 整体美观 | 基于渲染产物的本地评估 |

**硬门槛**：文字不得溢出/被遮挡，否则视为 P0。

## draw.io CLI（强烈推荐）

本技能优先使用 draw.io CLI 导出高质量 SVG/PNG。若未检测到 CLI，将退回内部渲染兜底（可用，但质量通常不如 CLI）。

**安装方式**：

| 平台 | 命令/方法 |
|------|----------|
| macOS | `brew install --cask drawio` |
| Windows | 安装 draw.io Desktop（diagrams.net） |
| Linux | 安装 draw.io 并确保 `drawio` 在 PATH 中 |

**调试**：强制走内部渲染 → 设置环境变量 `NSFC_SCHEMATIC_FORCE_INTERNAL_RENDER=1`

## Spec 示例

见 `nsfc-schematic/references/spec_examples/`：

- `ccs_framework.yaml`：典型分组结构
- `transformer.yaml`：深度学习架构

## 常见问题

### Q：原理图和技术路线图有什么区别？

原理图强调"层次关系 + 模块交互"（如算法架构），技术路线图强调"时间线 + 阶段划分"（如三年计划）。选错了？用另一个 skill 重做即可。

### Q：如何修改节点/连线？

优先编辑 `spec.yaml`，然后重新生成。这样可以保持可复现性。小改动也可以直接用 draw.io 编辑 `.drawio`。

### Q：为什么连线穿过了节点？

尝试调整布局参数（`config.yaml:layout.auto`），或手动在 draw.io 中调整节点位置。

### Q：导出的图中文显示为方框？

确保本机安装了中文字体（见 `config.yaml:renderer.fonts.candidates`）。

### Q：如何关闭标题显示？

设置 `config.yaml:layout.title.enabled=false`。

### Q：中间文件太多，如何清理？

默认已启用隐藏模式，中间文件在 `.nsfc-schematic/` 中。你可以直接删除该目录，不影响交付文件。

## 隐私与边界

- 默认将标书内容视为敏感信息，仅处理你明确提供的文件/目录
- 输出图中仅保留科研必要术语，避免写入无关个人信息
- 默认不联网抓取素材

## 配置说明

配置文件位于 `config.yaml`：

- `renderer`：画布尺寸、字体、渲染行为
- `layout`：分组、间距、字号、自动扩容
- `layout.auto_edges`：未提供显式 `edges` 时的自动连线策略（`minimal|off`）
- `evaluation`：评估阈值、停止策略（含 `evaluation.evaluation_mode`）
- `output`：输出目录、隐藏模式
- `output_dir/.nsfc-schematic/config_local.yaml`：实例级覆盖（白名单字段，适合单项目微调）

## 相关技能

- `nsfc-roadmap`：技术路线图生成
- `nsfc-reviewers`：标书评审
- `nsfc-justification-writer`：立项依据写作
- `nsfc-research-content-writer`：研究内容写作

---

版本信息见 `config.yaml:skill_info.version`。
