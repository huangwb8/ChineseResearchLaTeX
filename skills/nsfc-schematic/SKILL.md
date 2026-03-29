---
name: nsfc-schematic
description: 当用户明确要求"生成 NSFC 原理图/机制图/schematic diagram/mechanism diagram"或需要把标书中的研究机制、算法架构、模块关系转成"可编辑 + 可嵌入文档"的图示时使用。默认输出可编辑源文件（`.drawio`）与渲染文件（`.pdf`/`.svg`/`.png`）；当用户主动提及 Nano Banana/Gemini 图片模型时，可切换为 PNG-only 模式。⚠️ 不适用：用户只是想润色正文文本（应直接改写文本）、只是想改已有图片格式/尺寸（应使用图片处理技能）、没有明确"原理图/机制图"意图。
metadata:
  author: Bensz Conan
  short-description: 生成 NSFC 原理图（默认 drawio + PDF/SVG/PNG；可选 Nano Banana PNG-only）
  keywords:
    - nsfc-schematic
    - nsfc
    - schematic
    - mechanism diagram
    - drawio
    - architecture diagram
---

# NSFC 原理图生成器

## 与 bensz-collect-bugs 的协作约定

- 当用户环境中出现因本 skill 设计缺陷导致的 bug 时，优先使用 `bensz-collect-bugs` 按规范记录到 `~/.bensz-skills/bugs/`，严禁直接修改用户本地 Claude Code / Codex 中已安装的 skill 源码。
- 若 AI 仍可通过 workaround 继续完成用户任务，应先记录 bug，再继续完成当前任务。
- 当用户明确要求“report bensz skills bugs”等公开上报动作时，调用本地 `gh` 与 `bensz-collect-bugs`，仅上传新增 bug 到 `huangwb8/bensz-bugs`；不要 pull / clone 整个 bug 仓库。

## 定位

- 把机制链、算法架构、模块关系或实验闭环画成可编辑、可嵌入的科研图。
- 默认使用 `drawio` 生成 `drawio/pdf/svg/png`；只有用户明确要求 Nano Banana/Gemini 时才允许切到 PNG-only。
- 仅用于科研写作与表达优化，不代表评审口径。

## 输入

至少提供其一：

- `spec_file`：结构化图规格文件，优先。
- `proposal_file`：单个标书文件。
- `proposal_path`：标书目录。

可选：

- `rounds`
- `renderer`
- `output_dir`
- `config`
- `style_ref_images`
- `context`：自然语言机制描述，供规划模式生成草案
- `template_ref`

## 输出

默认交付：

- `schematic.drawio`
- `schematic.pdf`
- `schematic.svg`
- `schematic.png`

隐藏中间产物写入 `output_dir/.nsfc-schematic/`：

- `optimization_report.md`
- `spec_latest.yaml`
- `config_used_best.yaml`
- `evaluation_best.json`
- `runs/run_*/round_*`
- `ai/`：`stop_strategy=ai_critic` 工作区
- `legacy/`：历史残留收纳区

Nano Banana / Gemini 模式仅交付：

- `schematic.png`
- `schematic_compacted.png`

## 硬规则

- 开始前强制读取 `config.yaml`，以 `renderer`、`layout`、`color_scheme`、`evaluation`、`planning`、`output` 为单一真相来源。
- 默认仅处理用户明确提供的文件或目录，不联网抓素材。
- 默认保持 `drawio` 流程；未被用户点名时，不要切到图片模型。
- 拥挤优先改 `spec`，不要优先缩字号；只有出现 overflow 风险时才减字号。
- 配色问题优先改 `kind` 分配或结构，不用黑白方案掩盖结构错误。

## 主流程

### 1. 规划

- 推荐首次使用时先走“规划 → 审阅 → 生成”。
- 默认 `planning_mode=ai`：
  1. `plan_schematic.py` 生成规划请求
  2. 宿主 AI 产出 `schematic-plan.md` 和 `spec_draft.yaml`
  3. 复跑脚本做合法性校验
- 若用户只给自然语言描述，也可直接以 `--context` 启动规划。

### 2. 生成

```bash
python3 nsfc-schematic/scripts/generate_schematic.py \
  --spec-file ./schematic_plan/spec_draft.yaml \
  --output-dir ./schematic_output \
  --rounds 5
```

- 流程包括：解析 spec、生成 draw.io XML、XML 预检、渲染、主评估、多维度自检、导出 best round。
- 如提供显式 `edges`，渲染器必须优先复现；否则按 `layout.auto_edges` 自动连线。

### 3. 评估与优化

- 默认最多 5 轮，阈值与停止策略只看 `config.yaml:evaluation`。
- 每轮至少输出：
  - `evaluation.json`
  - `layout_debug.json`
  - `edge_debug.json`
  - `measurements.json`
  - `dimension_measurements.json`
  - `critique_structure.json`
  - `critique_visual.json`
  - `critique_readability.json`

### 4. 可选：AI 自主闭环

- 当需要宿主 AI 根据证据包决定下一轮时，启用 `evaluation.stop_strategy: ai_critic`。
- 协议文件位于 `.nsfc-schematic/ai/`，主要包括：
  - `ai_critic_request.md`
  - `ai_critic_response.yaml`
  - `ai_pack_round_XX/`

### 5. 可选：Nano Banana / Gemini PNG-only

- 只有用户明确要求时启用。
- 先做连通性检查：

```bash
python3 nsfc-schematic/scripts/nano_banana_check.py
```

- 再执行 PNG-only 生成：

```bash
python3 nsfc-schematic/scripts/generate_schematic.py \
  --renderer nano_banana \
  --spec-file ./schematic_plan/spec_draft.yaml \
  --output-dir ./schematic_output \
  --rounds 5
```

## 常用命令

```bash
# 规划
python3 nsfc-schematic/scripts/plan_schematic.py --proposal /path/to/proposal --output ./schematic_plan

# 生成
python3 nsfc-schematic/scripts/generate_schematic.py --spec-file ./schematic_plan/spec_draft.yaml --output-dir ./schematic_output --rounds 5

# 连通性检查
python3 nsfc-schematic/scripts/nano_banana_check.py
```

## 参考材料

- `config.yaml`
- `references/plan_template.md`
- `references/design_principles.md`
- `references/models/templates.yaml`
- `references/spec_examples/`
