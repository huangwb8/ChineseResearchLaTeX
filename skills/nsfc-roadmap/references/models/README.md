# 技术路线图模板库说明

> 本目录是“视觉参考库”，不是可直接逆向成 drawio 的模板源码。

## 目录作用

- `templates.yaml`：机器索引，负责 `template_ref -> family/render_family`
- 本 README：人类看的选型说明
- 规划脚本会生成 contact sheet，供宿主 AI 或人类先看图选型

## 使用原则

- 先看图选型，再把选择写进 `roadmap-plan.md` 或 `spec.yaml`
- 模板只提供“家族级骨架参考”，不承诺像素级复刻
- 当某 family 不是渲染器稳定骨架时，以 `render_family` 为准

## 主要家族

### `three-column`

- 适合：左右支撑列 + 中央主线
- 常见用途：研究内容 / 方法 / 支撑条件分列

### `layered-pipeline`

- 适合：纵向主流程 + 横向模块
- 常见用途：起点 → 并行模块 → 汇总输出

### `convergence-divergence`

- 适合：多输入 → 核心机制 → 多输出
- 当前渲染通常近似落到 `layered-pipeline`

### `dual-mainline`

- 适合：双主线并行推进
- 当前渲染通常近似落到 `three-column`

## 最小选型记录

在规划文档里至少写清：

- `template_ref`
- 选择理由
- 准备如何映射到分区、主线、节点密度与配色
