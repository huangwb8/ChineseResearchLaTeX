# 技术路线图模板库（references/models）

本目录包含 10 个“成品感较强”的路线图风格示例（JPEG/PNG），以及一份结构化模板索引：

- 机器可读（单一真相来源）：`templates.yaml`
- 人类可读索引（本文件）：帮助快速挑选模板与理解“参考约束”

重要说明：

- 这里的模板用于“参考而非照搬”；本技能不做像素级复刻，也不从 JPEG 逆向生成可编辑 drawio。
- 渲染器只承诺提供“模板家族级别”的稳定骨架，不承诺完全一致的细节。
- 部分模板家族目前会“近似落地”：模板的 `family` 用于规划参考；真正渲染时可能按 `templates.yaml:render_family` 回退到已支持的骨架。

## 如何使用（给使用者/AI）

- 若用户明确要求：按 `model-02` / `three-column` / `layered-pipeline` 风格生成
  - 规划阶段应在 `roadmap-plan.md` 中写明：选用的 `template_ref`（模板 id 或 family）+ 选用原因 + 将如何落到 spec 的约束清单
  - 生成阶段可在 `spec.yaml` 中写入：
    - `template_ref: model-02`
    - `layout_template: auto|classic|three-column|layered-pipeline`

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

- 当前渲染器会按 `templates.yaml:render_family` 将该家族近似落到 `layered-pipeline` 骨架。

### dual-mainline

双主线并行型：左右两条主线（两个驱动力/两个维度）并行推进，中央为核心研究内容，每层横向展开。

覆盖模板：

- `model-10` → `roadmap-model-10.png`

说明：

- 当前渲染器会按 `templates.yaml:render_family` 将该家族近似落到 `three-column` 骨架。

## 模板索引（template id）

下表用于快速选型；详细 token 见 `templates.yaml`。

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
