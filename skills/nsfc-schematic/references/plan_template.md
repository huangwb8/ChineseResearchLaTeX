# 原理图规划草案

> 说明：本模板用于“先规划再生成”的工作流。建议先写清楚“这张图要表达什么”，再落到节点与连线，最后给出可执行的 spec 草案。

## 核心目标

一句话描述：这张图要传达的核心机制/结构/因果链条是什么？

## 图类型模板（可选但推荐）

优先先确定“这张图的叙事骨架”，再填节点与连线：

- `linear-pipeline`：输入→处理→输出（最稳健默认）
- `layered-arch`：分层架构（数据层/表征层/模型层/应用层）
- `feedback-loop`：反馈/调控闭环
- `parallel-branch`：并行分支→汇合输出
- `hub-spoke`：核心枢纽→多个下游效应

模板库见：`references/models/templates.yaml`（可通过规划脚本 `--template-ref model-xx` 强制指定）。

提示：`references/models/` 下可能存在 `*.simple.*` 的“骨架/模式图”（更精炼）。在确定叙事骨架时，建议优先参考 simple 版本，再用完整参考图补齐风格与细节。

## 模块划分

建议 2-5 个模块，每个模块职责清晰、边界明确。

| 模块 ID | 模块名称 | 职责说明 | 节点数 |
|---------|----------|----------|--------|
| input   | 输入层   | 数据采集与预处理 | 2 |
| process | 处理层   | 核心算法/方法 | 3 |
| output  | 输出层   | 结果输出与应用 | 2 |

## 节点清单

按模块列出节点；节点命名尽量与正文术语保持一致。

### input（输入层）

| 节点 ID | 节点名称 | 类型 | 说明 |
|---------|----------|------|------|
| raw_data | Raw Data | primary | 原始输入数据 |
| phenotype | Phenotype | decision | 表型标签 |

### process（处理层）

| 节点 ID | 节点名称 | 类型 | 说明 |
|---------|----------|------|------|
| dr_nd | DR (nD) | secondary | 高维降维 |
| dr_2d | DR (2D) | secondary | 二维可视化 |
| predictor | CCS Predictor | critical | 核心预测模型 |

### output（输出层）

| 节点 ID | 节点名称 | 类型 | 说明 |
|---------|----------|------|------|
| norm_ccs | Normalized CCS | primary | 标准化输出 |
| pred_ccs | Predicted CCS | critical | 预测结果 |

## 连接关系

### 主流向（实线）

- raw_data → dr_nd → dr_2d → predictor → norm_ccs
- predictor → pred_ccs（粗线，强调核心输出）

### 辅助连接（虚线）

- phenotype → predictor（辅助输入）

### 可选/分支

- （无）

## 布局建议

- 方向：top-to-bottom / left-to-right
- 层次：输入 → 处理 → 输出
- 配色：academic-blue（或其他）
- 备注：是否需要强调某个关键模块/关键连线？

## Spec 草案

```yaml
schematic:
  title: "..."
  direction: top-to-bottom
  groups:
    - id: input
      label: "输入层"
      style: dashed-border
      children:
        - {id: raw_data, label: "Raw Data", kind: primary}
        - {id: phenotype, label: "Phenotype", kind: decision}
    - id: process
      label: "处理层"
      style: solid-border
      children:
        - {id: predictor, label: "Predictor", kind: critical}
    - id: output
      label: "输出层"
      style: background-fill
      children:
        - {id: pred_ccs, label: "Predicted CCS", kind: critical}
  edges:
    - {from: raw_data, to: predictor, style: solid}
    - {from: predictor, to: pred_ccs, style: thick}
```

## 自检

- 分组数量：2-5 个
- 每组节点数：1-6 个（过多会影响可读性）
- 总节点数：不建议超过 20（建议拆分多图）
- 连接密度：不建议超过 1.5 × 节点数（过密会影响清晰度）
- 输入/输出：必须各至少 1 个节点（否则读者无法识别起点/终点）
