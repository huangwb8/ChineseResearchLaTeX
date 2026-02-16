# 技术路线图模板库（references/models）

本目录包含 6 个“成品感较强”的路线图风格示例（JPEG），以及一份结构化模板索引：

- 机器可读（单一真相来源）：`templates.yaml`
- 人类可读索引（本文件）：帮助快速挑选模板与理解“参考约束”

重要说明：

- 这里的模板用于“参考而非照搬”；本技能不做像素级复刻，也不从 JPEG 逆向生成可编辑 drawio。
- 渲染器只承诺提供“模板家族级别”的稳定骨架（例如三列式/分层流水线），不承诺完全一致的细节。

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

参考约束（建议）：

- 以“中央主线”为第一叙事；左右列用于支撑、方法、评估或数据来源
- 每一层/区块用标题条或虚线容器增强分区感
- 低饱和配色、信息层级明确（标题 > 主线节点 > 支撑节点）

### layered-pipeline

纵向主流程 + 横向分层/模块；常见于“起点 → 并行模块 → 汇总输出”的流水线呈现。

覆盖模板：

- `model-03` → `roadmap-model-03.jpeg`
- `model-06` → `roadmap-model-06.jpeg`

参考约束（建议）：

- 纵向主链清晰（读者能一眼从上到下读完主线）
- 并行模块用横向分层/容器承载，避免堆成单列长列表
- 输出/交付在底部汇总（对评审更友好）

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

