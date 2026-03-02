# nsfc-schematic — 用户使用指南

本 README 面向**使用者**：如何触发并正确使用 `nsfc-schematic` skill。
执行指令与硬性规范在 `SKILL.md`；默认参数在 `config.yaml`。

## 快速开始

### 最推荐用法

- 默认 draw.io，高质量矢量交付）

```
使用 nsfc-schematic skill的 draw.io 模式，基于我的标书生成xxx的原理图。
输入： ./projects/NSFC_General/
输出： ./schematic_output/
```

- nano banana 模式

```
使用 nsfc-schematic skill的 Nano Banana模式，基于我的标书生成xxx的原理图。
输入： ./projects/NSFC_General/
输出： ./schematic_output/
```

### 更高级的参数定义

```
{常规Prompt}
此外:
- 自优化的轮次上限是10，不允许早停。
- 高宽比为1:1.2
```

## 两种出图模式

本技能支持两种出图模式，开始前建议先了解它们的区别：

| 对比维度 | draw.io 模式（默认） | Nano Banana 模式 |
|---------|---------------------|-----------------|
| **输出格式** | `.drawio` + `.svg` + `.png` + `.pdf` | `schematic.png`（4K）+ `schematic_compacted.png`（更小体积） |
| **矢量图** | ✅ SVG 矢量，可无损缩放 | ❌ 仅位图 |
| **可编辑性** | ✅ 用 draw.io 打开可直接拖拽微调 | ❌ 不可后期编辑 |
| **出图质量** | 取决于多轮优化轮次 | 高（Gemini 图片模型直接生成） |
| **出图速度** | 较慢（多轮评估-优化循环） | 快 |
| **调整成本** | 高（多轮对话 + 理解 spec/yaml 结构） | 低（重跑即可） |
| **中文渲染** | 稳定（受本机字体影响） | 偶有扭曲/模糊风险 |
| **额外配置** | 无 | 需要配置 Gemini API（见下文） |
| **触发方式** | 默认启用 | 需明确说"用 Nano Banana 出图" |

**如何选择**：
- 优先用 **draw.io 模式**：需要嵌入标书的矢量图、需要后期精修布局、对图面质量有严格要求。
- 选 **Nano Banana 模式**：已配置 Gemini API、追求快速出图、接受仅 PNG 交付、不需要矢量格式。

## 设计理念

- **默认 draw.io**：优先输出可编辑的 `schematic.drawio` 与矢量交付（`svg/pdf`），适合标书嵌入。
- **可追溯优化**：多轮评估 + 证据产出（`evaluation.json`/`measurements.json` 等）。
- **PNG-only 备用通道**：当你明确要求 Nano Banana/Gemini 模式时，生成 **4K** `schematic.png` + 更小体积的 `schematic_compacted.png`（适合嵌入标书 PDF）。

## 功能概述

| 特性 | 说明 |
|------|------|
| 多轮优化 | 默认 5 轮，AI 离线闭环（`evaluation.stop_strategy=ai_critic`；可切换 `plateau` 无人值守收敛） |
| 高质量导出 | draw.io CLI 优先；缺失时内部渲染兜底 |
| PNG-only 模式 | `--renderer nano_banana`，仅当你主动提及时启用 |
| 证据可追溯 | 每轮输出 `evaluation.json`/`measurements.json` 等 |
| 并行对比 | 推荐 `parallel-vibe` 5 线程做多策略对比 |

## Gemini API 配置（Nano Banana 模式）

如果你要使用 **Nano Banana / Gemini 图片生成模式**，需先配置 Gemini API。

### 配置方式

在**项目根目录**创建或编辑 `.env` 文件，添加以下内容：

```bash
# Gemini API
# 官方: https://generativelanguage.googleapis.com/v1beta
# 第三方代理示例: https://xingjiabiapi.org/v1
GEMINI_BASE_URL=https://generativelanguage.googleapis.com/v1beta
GEMINI_API=你的API密钥
GEMINI_MODEL=gemini-3.1-flash-image-preview
```

### 环境变量说明

| 变量 | 必需 | 说明 |
|------|------|------|
| `GEMINI_BASE_URL` | ✅ | Gemini API 地址（官方或代理） |
| `GEMINI_API` | ✅ | API 密钥（也支持 `GEMINI_API_KEY` / `GOOGLE_API_KEY`） |
| `GEMINI_MODEL` | ✅ | 模型名称（如 `gemini-3.1-flash-image-preview`） |

### 验证连通性

```bash
python3 nsfc-schematic/scripts/nano_banana_check.py
```

成功时会输出：
```
OK: dotenv=/path/to/.env, base_url=https://..., model=gemini-3.1-flash-image-preview
```

### 获取 API 密钥

1. **官方渠道**：访问 [Google AI Studio](https://aistudio.google.com/apikey) 获取
2. **第三方代理**：如使用代理服务，请按代理方文档配置 `GEMINI_BASE_URL`

---

## Nano Banana 模式工作原理

理解这个模式的内部机制，有助于正确使用和调优。

### 实际流程

```
[准备] 规划 spec（分组/节点/连接关系）
   ↓
[Round N]
  1. 脚本从 spec 确定性构建纯文本 prompt
     （_build_nano_banana_prompt：硬编码拼接，不由宿主 AI 生成）
  2. 调用 Gemini API（默认只传文本；当宿主 AI 写 `style_continuity: true` 时，会额外把上一轮 PNG 作为参考图一并传入以延续风格）→ 得到新 PNG
  3. 脚本对 PNG 做启发式评估，生成证据包（evaluation.json 等）
  4. 宿主 AI 读证据包（含 PNG），写回 ai_critic_response.yaml
     → 默认修改 spec 或 config_local；也可选写 `nano_banana_color_advice` / `nano_banana_prompt` 来影响下一轮绘图
  5. 下一轮用更新后的 spec 重新构建 prompt，从头生成新 PNG
   ↓
满足停止条件（达轮次上限，或宿主 AI 写 action: stop）→ 导出最终 PNG
```

### 两个常见误解

| 误解 | 实际行为 |
|------|----------|
| "宿主 AI 直接写 prompt 传给 Gemini" | 默认 prompt 由脚本从 spec 确定性生成；但在 `ai_critic_response.yaml` 中可选提供 `nano_banana_prompt`（full/patch）覆盖下一轮 prompt |
| "把上一轮 PNG 传回 Gemini 做图上修改" | 默认每轮只传纯文本、从头生成新 PNG；但当宿主 AI 写 `style_continuity: true` 时，下一轮会把上一轮 PNG 作为参考图传入，用于**延续风格**（不是像素级局部编辑） |

### 优化思路

- **想改图的内容/结构** → 让宿主 AI 修改 spec（节点 label、分组划分、连接关系）
- **想改图的视觉参数** → 让宿主 AI 修改 config_local（字号、画布尺寸、配色等）
- **想并行对比多种方案** → 用 `parallel-vibe` 开多个隔离工作区，每个线程用不同 spec 或 config

---

## 配置选项（常用）

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `renderer.canvas.width_px` | 3200 | 画布宽度 |
| `renderer.canvas.height_px` | 2000 | 画布高度 |
| `renderer.drawio.cli_path` | "" | draw.io CLI 路径（可选） |
| `evaluation.max_rounds` | 5 | 最大优化轮次 |
| `evaluation.stop_strategy` | `ai_critic` | 停止策略（`ai_critic`/`plateau`/`none`） |
| `output.hide_intermediate` | true | 是否隐藏中间产物到 `.nsfc-schematic/` |
| `layout.font.node_label_size` | 26 | 节点字号 |
| `layout.font.edge_label_size` | 24 | 连线标签字号 |
| `layout.canvas_fit.center_content` | true | 自动布局下将内容 bbox 居中（减少单侧留白；显式布局默认不启用） |
| `color_scheme.name` | `academic-blue` | 配色方案 |

在 `config.yaml` 中修改这些参数。

## 备选用法（脚本/硬编码流程）

### 步骤 1：规划（推荐先做）

```bash
# 生成规划草案（plan_request.md + spec_draft.yaml）
python3 nsfc-schematic/scripts/plan_schematic.py \
  --proposal /path/to/proposal/ \
  --output ./schematic_plan/
```

### 步骤 2：默认 draw.io 生成（推荐）

```bash
# 默认 draw.io，输出 drawio/svg/png/pdf
python3 nsfc-schematic/scripts/generate_schematic.py \
  --spec-file ./schematic_plan/spec_draft.yaml \
  --output-dir ./schematic_output/ \
  --rounds 5
```

### 步骤 3：Nano Banana PNG-only（仅当你明确要求）

```bash
# 连通性检查（读取 .env）
python3 nsfc-schematic/scripts/nano_banana_check.py

# PNG-only 生成
python3 nsfc-schematic/scripts/generate_schematic.py \
  --renderer nano_banana \
  --spec-file ./schematic_plan/spec_draft.yaml \
  --output-dir ./schematic_output/ \
  --rounds 5
```

## 常见问题（FAQ）

### Q：draw.io CLI 没装会怎样？
A：会自动回退到内部渲染兜底，仍能生成 PNG/PDF，但质量可能略低。建议安装并在 `renderer.drawio.cli_path` 指定。

### Q：如何触发 Nano Banana 模式？
A：**必须由你明确提出**（如“用 Nano Banana/Gemini 出图”）。然后使用 `--renderer nano_banana`，该模式只交付 PNG（`schematic.png` + `schematic_compacted.png`）。

### Q：为什么只输出 PNG？
A：Nano Banana/Gemini 仅生成图片，不支持输出 `.drawio/.svg/.pdf`。如果需要可编辑/矢量，请使用默认 draw.io 模式。

### Q：Nano Banana 图里文字容易扭曲/不规整，怎么缓解？
A：该模式的 prompt 已内置“打印级文字排版”约束（禁止文字扭曲/旋转/艺术字；建议黑字+白底标签框）。如果仍不理想，通常按下面顺序调：

1. **先缩短文字**：把节点/连线标签改成更短的短语（优先 4–10 字），避免长句。
2. **再增大字号/画布**：提高 `layout.font.node_label_size` / `layout.font.edge_label_size`，必要时增大 `renderer.canvas.width_px/height_px`。
3. **仍需“绝对可读 + 可控字体”**：回到默认 draw.io 模式（可编辑/矢量），或用 draw.io/Inkscape 后期统一替换文字。

### Q：并行优化怎么做？
A：使用 `parallel-vibe` 开 5 个隔离线程，每个线程设置不同策略，并用 `--run-tag` 标记来源。

## 更多文档

- `SKILL.md` — 技能执行指令与硬性规范
- `config.yaml` — 默认参数与配置说明
- `references/` — 模板与参考材料
