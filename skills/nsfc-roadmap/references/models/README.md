# 技术路线图模板库（references/models）

本目录包含 10 个“成品感较强”的路线图风格示例（JPEG/PNG），供**视觉参考选型**使用。

配套文件：

- `templates.yaml`：**最小机器索引**（`id/file/family/render_family`），用于 `template_ref → 渲染骨架` 的稳定映射与兜底。
- 本 README：**人类可读说明**（经验性解释/选型提示）。
- 规划脚本会生成“模型画廊（contact sheet）”，让宿主 AI / 人类直接看图选型。

重要说明（请先读）：

- 这里的模板用于“参考而非照搬”；本技能不做像素级复刻，也不从 JPEG 逆向生成可编辑 drawio。
- 渲染器只承诺提供“模板家族级别”的稳定骨架，不承诺完全一致的细节。
- 部分概念家族会“近似落地”：当 `family` 非渲染器稳定支持的骨架时，将按 `render_family` 回退（见 `templates.yaml`）。

## 如何使用（给使用者/AI）

推荐工作流：先“看图选型”，再把选择固化为 `template_ref`（用于可复现）。

1) 运行规划脚本（推荐 `--mode ai`，让宿主 AI 直接看图选）后，会在输出目录生成：

- `output_dir/.nsfc-roadmap/planning/models_contact_sheet.png`（模型画廊，推荐先看这一张）
- `output_dir/.nsfc-roadmap/planning/models/`（单张参考图）

2) 在 `roadmap-plan.md` 写清楚：

- 选用的 `template_ref`（例如 `model-02`）
- 选用理由（基于**视觉风格**与叙事结构：三列/流水线/收敛-发散/双主线等）
- 你打算如何把参考风格落到 spec（分区/主线/节点密度/配色语义）

3) 在 `spec.yaml`（或 `spec_draft.yaml`）中写入（可选但推荐）：

```yaml
template_ref: model-02
layout_template: auto  # 或 classic/three-column/layered-pipeline
```

## 模板家族（family）

### three-column

三列式：左右支撑列 + 中央主线；常见于“研究框架/研究内容/研究方法”的结构化呈现。

覆盖模板：

- `model-01` → `roadmap-model-01.jpeg`
- `model-02` → `roadmap-model-02.jpeg`
- `model-04` → `roadmap-model-04.jpeg`
- `model-05` → `roadmap-model-05.jpeg`
- `model-10` → `roadmap-model-10.png`（双主线概念；渲染时近似落到 three-column 骨架）

参考约束（建议）：

- 以“中央主线”为第一叙事；左右列用于支撑、方法、评估或数据来源
- 每一层/区块用标题条或虚线容器增强分区感
- 低饱和配色、信息层级明确（标题 > 主线节点 > 支撑节点）

### layered-pipeline

纵向主流程 + 横向分层/模块；常见于“起点 → 并行模块 → 汇总输出”的流水线呈现。

覆盖模板：

- `model-03` → `roadmap-model-03.jpeg`
- `model-06` → `roadmap-model-06.jpeg`
- `model-07` → `roadmap-model-07.png`
- `model-08` → `roadmap-model-08.png`（收敛-发散概念；渲染时近似落到 layered-pipeline 骨架）
- `model-09` → `roadmap-model-09.png`（收敛-发散概念；渲染时近似落到 layered-pipeline 骨架）

参考约束（建议）：

- 纵向主链清晰（读者能一眼从上到下读完主线）
- 并行模块用横向分层/容器承载，避免堆成单列长列表
- 输出/交付在底部汇总（对评审更友好）

### convergence-divergence

收敛-发散型：多输入在中部汇聚为核心概念，再向下发散为多输出；常见于“多来源 → 核心机制 → 多体系输出”的漏斗/轮辐叙事。

覆盖模板：

- `model-08` → `roadmap-model-08.png`
- `model-09` → `roadmap-model-09.png`

说明：

- 当前渲染器会按 `templates.yaml:render_family` 将该家族近似落到 `layered-pipeline` 骨架（即：风格参考仍在，但骨架以可稳定渲染为准）。

### dual-mainline

双主线并行型：左右两条主线（两个驱动力/两个维度）并行推进，中央为核心研究内容，每层横向展开。

覆盖模板：

- `model-10` → `roadmap-model-10.png`

说明：

- 当前渲染器会按 `templates.yaml:render_family` 将该家族近似落到 `three-column` 骨架（即：双主线是概念参考，骨架以可稳定渲染为准）。

## 模板索引（template id）

下表用于快速定位图片文件（以及一个“经验性”适用场景提示）。最终以“看图选型”为准。

| id | file | family | 适用场景（简述） |
|---|---|---|---|
| model-01 | roadmap-model-01.jpeg | three-column | 三列式主线清晰，中央分层叙事 |
| model-02 | roadmap-model-02.jpeg | three-column | 三列同层强对齐、支撑与主线绑定 |
| model-03 | roadmap-model-03.jpeg | layered-pipeline | 起点→并行模块→汇总输出 |
| model-04 | roadmap-model-04.jpeg | three-column | 分组/容器更强，区块感更突出 |
| model-05 | roadmap-model-05.jpeg | three-column | 阶段标题条更强，适合扫读 |
| model-06 | roadmap-model-06.jpeg | layered-pipeline | 分层流水线更明显，偏树状/模块化 |
| model-07 | roadmap-model-07.png | layered-pipeline | 多来源输入汇聚 + 底部三列并行模块 |
| model-08 | roadmap-model-08.png | convergence-divergence | 漏斗：多输入→核心机制→多体系输出（渲染近似落地） |
| model-09 | roadmap-model-09.png | convergence-divergence | 轮辐：多维度→核心概念→多维度输出（渲染近似落地） |
| model-10 | roadmap-model-10.png | dual-mainline | 双主线驱动中央内容（渲染近似落地） |
