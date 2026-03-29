# 原理图规划草案模板

> 用于“先规划再生成”。目标是先想清楚图要表达什么，再落节点与边，最后再写 spec。

## 最小规划项

1. 一句话核心目标：这张图到底要表达哪条机制/结构/因果链？
2. 图骨架：线性、分层、反馈、并行分支还是 hub-spoke？
3. 模块划分：建议 2-5 个
4. 节点清单：名称尽量与正文术语一致
5. 连接关系：主流向、辅助流向、可选分支
6. 布局建议：方向、强调点、配色

## 常用骨架

- `linear-pipeline`
- `layered-arch`
- `feedback-loop`
- `parallel-branch`
- `hub-spoke`

## 极简 spec 草案

```yaml
schematic:
  title: "..."
  direction: top-to-bottom
  groups:
    - id: input
      label: "输入层"
      children:
        - {id: raw_data, label: "Raw Data", kind: primary}
    - id: process
      label: "处理层"
      children:
        - {id: predictor, label: "Predictor", kind: critical}
  edges:
    - {from: raw_data, to: predictor, style: solid}
```

## 自检

- 分组数量 2-5
- 每组节点 1-6
- 总节点不宜超过 20
- 输入与输出都必须清楚可见
