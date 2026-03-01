# nsfc-schematic — 用户使用指南

本 README 面向**使用者**：如何触发并正确使用 `nsfc-schematic` skill。
执行指令与硬性规范在 `SKILL.md`；默认参数在 `config.yaml`。

## 快速开始

### 最推荐用法（默认 draw.io，高质量矢量交付）

```
请基于我的 NSFC 标书生成原理图，优先用默认 draw.io 流程输出可直接嵌入的图。
标书在 ./projects/NSFC_General/，输出到 ./schematic_output/，优化 5 轮。
```

### 其他常见场景

#### 场景 1：已有 spec，直接生成

```
用 nsfc-schematic 读取 ./schematic_plan/spec_draft.yaml 生成原理图，输出到 ./schematic_output/，轮次 5。
```

#### 场景 2：从 TEX 自动抽取

```
请从 /path/to/main.tex 自动抽取内容生成原理图，输出到 ./schematic_output/。
```

#### 场景 3：结构性改动（ai_critic 闭环）

```
我需要结构性优化，请启用 ai_critic 闭环生成原理图，并按协议输出请求文件。
```

#### 场景 4：Nano Banana / Gemini PNG-only（仅当我明确要求）

```
我明确要用 Nano Banana（Gemini 图片模型）出图，接受仅 PNG 交付。
请基于 ./schematic_plan/spec_draft.yaml 生成原理图，输出到 ./schematic_output/。
```

## 设计理念

- **默认 draw.io**：优先输出可编辑的 `schematic.drawio` 与矢量交付（`svg/pdf`），适合标书嵌入。
- **可追溯优化**：多轮评估 + 证据产出（`evaluation.json`/`measurements.json` 等）。
- **PNG-only 备用通道**：当你明确要求 Nano Banana/Gemini 模式时，仅生成高分辨率 `schematic.png`。

## 功能概述

| 特性 | 说明 |
|------|------|
| 多轮优化 | 默认 5 轮，平台期自动收敛（`evaluation.stop_strategy=plateau`） |
| 高质量导出 | draw.io CLI 优先；缺失时内部渲染兜底 |
| PNG-only 模式 | `--renderer nano_banana`，仅当你主动提及时启用 |
| 证据可追溯 | 每轮输出 `evaluation.json`/`measurements.json` 等 |
| 并行对比 | 推荐 `parallel-vibe` 5 线程做多策略对比 |

## 提示词示例

### 示例 1：最小可用

```
你：生成 NSFC 原理图，输出到 ./schematic_output/。
技能：读取默认模板或标书内容，输出 drawio/svg/png/pdf，并生成优化报告。
```

### 示例 2：指定 spec + 轮次

```
你：用 ./schematic_plan/spec_draft.yaml 生成原理图，输出到 ./schematic_output/，优化 5 轮。
技能：按 spec 渲染并自动评估，导出最佳轮次。
```

### 示例 3：Nano Banana PNG-only（明确指定）

```
你：用 Nano Banana 生成原理图，仅输出 PNG，spec 在 ./schematic_plan/spec_draft.yaml。
技能：进行连通性检查后出图，交付 `schematic.png`。
```

## 输出文件

- `schematic.drawio` — 可编辑源文件（仅 draw.io 模式）
- `schematic.svg` — 矢量图（仅 draw.io 模式）
- `schematic.pdf` — 嵌入标书优先格式（仅 draw.io 模式）
- `schematic.png` — 预览图 / PNG-only 交付
- `.nsfc-schematic/` — 中间产物（默认隐藏）：评估证据、run 目录、最新报告

**PNG-only 模式**：仅交付 `schematic.png`（不会生成 `.drawio/.svg/.pdf`）。

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

## 配置选项（常用）

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `renderer.canvas.width_px` | 3200 | 画布宽度 |
| `renderer.canvas.height_px` | 2000 | 画布高度 |
| `renderer.drawio.cli_path` | "" | draw.io CLI 路径（可选） |
| `evaluation.max_rounds` | 5 | 最大优化轮次 |
| `evaluation.stop_strategy` | `plateau` | 停止策略（`plateau`/`ai_critic`/`none`） |
| `output.hide_intermediate` | true | 是否隐藏中间产物到 `.nsfc-schematic/` |
| `layout.font.node_label_size` | 26 | 节点字号 |
| `layout.font.edge_label_size` | 22 | 连线标签字号 |
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
A：**必须由你明确提出**（如“用 Nano Banana/Gemini 出图”）。然后使用 `--renderer nano_banana`，该模式只交付 PNG。

### Q：为什么只输出 PNG？
A：Nano Banana/Gemini 仅生成图片，不支持输出 `.drawio/.svg/.pdf`。如果需要可编辑/矢量，请使用默认 draw.io 模式。

### Q：并行优化怎么做？
A：使用 `parallel-vibe` 开 5 个隔离线程，每个线程设置不同策略，并用 `--run-tag` 标记来源。

## 更多文档

- `SKILL.md` — 技能执行指令与硬性规范
- `config.yaml` — 默认参数与配置说明
- `references/` — 模板与参考材料
