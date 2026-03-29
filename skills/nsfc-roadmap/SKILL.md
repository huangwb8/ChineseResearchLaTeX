---
name: nsfc-roadmap
description: 当用户明确要求"生成 NSFC 技术路线图/技术路线图绘制/roadmap/flowchart"或需要把标书研究内容转成"可打印、A4 可读"的技术路线图时使用。默认输出可编辑源文件（`.drawio`）与可嵌入文档的渲染结果（`.svg`/`.png`/`.pdf`）；当用户主动提及 Nano Banana/Gemini 图片模型时，可切换为 PNG-only 模式。⚠️ 不适用：用户只是想修改某张已有图片的格式/尺寸（应使用图片处理技能）、只是想润色技术路线文字描述（应直接改写正文）。
metadata:
  author: Bensz Conan
  short-description: 生成 NSFC 技术路线图（默认 drawio + SVG/PNG/PDF；可选 Nano Banana PNG-only）
  keywords:
    - nsfc-roadmap
    - nsfc
    - roadmap
    - flowchart
    - drawio
    - svg
---

# NSFC 技术路线图生成器

## 与 bensz-collect-bugs 的协作约定

- 当用户环境中出现因本 skill 设计缺陷导致的 bug 时，优先使用 `bensz-collect-bugs` 按规范记录到 `~/.bensz-skills/bugs/`，严禁直接修改用户本地 Claude Code / Codex 中已安装的 skill 源码。
- 若 AI 仍可通过 workaround 继续完成用户任务，应先记录 bug，再继续完成当前任务。
- 当用户明确要求“report bensz skills bugs”等公开上报动作时，调用本地 `gh` 与 `bensz-collect-bugs`，仅上传新增 bug 到 `huangwb8/bensz-bugs`；不要 pull / clone 整个 bug 仓库。

## 定位

- 用于把 NSFC 标书中的研究内容、技术路线和风险控制转成可打印、A4 可读的路线图。
- 默认工作流是确定性的 `drawio` 渲染；只有用户明确要求 Nano Banana/Gemini 时才允许切到 PNG-only。
- 本技能只服务科研写作与可视化表达，不代表任何官方评审口径或资助结论。

## 输入

至少提供其一：

- `proposal_path`：标书目录，推荐。
- `proposal_file`：单个输入文件。
- `spec_file`：结构化图规格文件，最可控。

可选：

- `rounds`：默认读 `config.yaml:evaluation.max_rounds`
- `output_dir`：默认 `roadmap_output/`
- `renderer`：默认 `drawio`；仅用户明确要求时才用 `nano_banana`
- `dotenv`：仅 `nano_banana` 用
- `style_ref_images`：仅 `nano_banana` 用，最多前 4 张
- `layout` / `template_ref`：高级选项，默认不需要

## 输出

默认交付：

- `roadmap.drawio`
- `roadmap.svg`
- `roadmap.png`
- `roadmap.pdf`
- `roadmap-plan.md`

隐藏中间产物位于 `output_dir/.nsfc-roadmap/`：

- `runs/run_*/round_*`
- `spec_latest.yaml`
- `optimization_report.md`
- `config_used_best.yaml`
- `evaluation_best.json`
- `config_local.yaml`
- `ai/`：`stop_strategy=ai_critic` 时的请求/响应协议

Nano Banana / Gemini 模式仅交付：

- `roadmap.png`
- `roadmap_compacted.png`

## 硬规则

- 先读 `config.yaml`，以下字段视为单一真相来源：`renderer`、`evaluation`、`layout`、`color_scheme`、`planning`、`output`。
- 仅处理用户明确提供的文件或目录；默认把标书视为敏感信息。
- 默认不联网补素材；如用户要求联网，应先提醒风险。
- 默认保持 `drawio` 流程；不要因为“图片模型更快”就擅自切换渲染后端。
- 若内容拥挤，优先改 `spec` 的节点文案、分组或结构，不要靠缩字号硬过阈值。

## 工作流

### 1. 规划

- 若已提供 `spec_file`，可跳过。
- 默认使用 `config.yaml:planning.planning_mode=ai`：
  1. 运行 `plan_roadmap.py` 生成 `plan_request.json/plan_request.md`
  2. 宿主 AI 写 `roadmap-plan.md` 和 `spec_draft.yaml`
  3. 再次运行脚本校验 `spec_draft.yaml`
- 规划阶段要同时看立项依据与研究内容，不只看 `2.1 研究内容`。

### 2. 落到 spec

- 优先级：用户自带 `spec_file` > 规划阶段的 `spec_draft.yaml` > 从输入文件自动抽取。
- spec 至少明确阶段、节点、输入输出和风险/备选方案。
- 模板字段可选；默认不强制绑定某个 `template_ref`。

### 3. 确定性渲染

```bash
python3 nsfc-roadmap/scripts/generate_roadmap.py \
  --spec-file ./roadmap_output/spec.yaml \
  --output-dir ./roadmap_output \
  --rounds 5
```

- 渲染时固化 `spec_latest.yaml`
- 生成交付文件与每轮证据
- `draw.io CLI` 缺失时按配置决定提示、降级或停止

### 4. 评估与优化

- 默认最多 5 轮，具体以 `config.yaml:evaluation` 为准。
- 每轮至少识别三类问题：
  - `P0`：缺研究内容、逻辑断裂、孤立节点、不可读
  - `P1`：布局混乱、配色干扰、字号过小
  - `P2`：间距、边距、箭头清晰度等一般优化
- 停止策略只看配置：`early_stop`、`stop_strategy=plateau` 或 `stop_strategy=ai_critic`
- 多维度自检默认覆盖 `structure / visual / readability`

### 5. 可选：AI 自主闭环

- 若希望由宿主 AI 决定“是否继续、改哪里”，在 `config_local.yaml` 中启用 `evaluation.stop_strategy: ai_critic`。
- 脚本会在 `output_dir/.nsfc-roadmap/ai/` 下生成：
  - `ai_critic_request.md`
  - `ai_critic_response.yaml`
  - 每轮 `ai_pack_round_XX/`

### 6. 可选：Nano Banana / Gemini PNG-only

- 只有用户明确要求时才启用。
- 先做连通性检查：

```bash
python3 nsfc-roadmap/scripts/nano_banana_check.py
```

- 然后再生成 PNG：

```bash
python3 nsfc-roadmap/scripts/generate_roadmap.py \
  --spec-file ./roadmap_output/spec.yaml \
  --output-dir ./roadmap_output \
  --rounds 1 \
  --renderer nano_banana
```

## 常用命令

```bash
# 规划
python3 nsfc-roadmap/scripts/plan_roadmap.py --proposal /path/to/proposal --output ./roadmap_output

# 生成
python3 nsfc-roadmap/scripts/generate_roadmap.py --spec-file ./roadmap_output/spec.yaml --output-dir ./roadmap_output --rounds 5

# 图片模型连通性
python3 nsfc-roadmap/scripts/nano_banana_check.py
```

## 参考材料

- `config.yaml`
- `references/models/templates.yaml`
- `references/models/README.md`
- `assets/evaluation_rubric.md`
