# 章节写作指南

这个文档是 `paper-write-sci` 的通用章节写作参考。

- 它补充 `references/styles/*.md` 中的作者/领域风格
- 它提供“每一节最低应该做到什么”的稳定基线
- 它不替代具体风格文件，只负责跨风格通用的写作要求

## `.tex` 分段分点基线

- 新段落必须通过 `1` 个或以上空行显式表达；空行在 `.tex` 中不只是视觉分隔，而是段落边界
- 多个点仍属于同一段时，优先采用“同段分点换行”：不插空行，但让每个“并列信息单元”各占一个物理行
- 这里的“点”优先指并列证据单元、并列 panel、并列比较项、并列局限项，而不是任意一句普通叙述
- 优先用于多图/多表证据、多组对比、panel-by-panel legend、连续展开的观点或局限
- 不要机械地把每一句都拆行；只有当“逐点定位”确实能帮助人类读源码时再使用
- 仅用于纯正文自然语言段落；不要主动改写 `%` 注释拼接、宏参数、大括号内文本、命令密集行、环境头尾等行敏感 LaTeX 结构

简例：

```tex
The primary finding was supported by three coordinated observations:
Subtype A achieved the highest response rate in the discovery cohort (Fig. 2A).
The same ranking pattern was reproduced in the validation cohort (Fig. 2B).
Survival separation followed the same direction in Fig. 2C.

This is a new paragraph because the text shifts from result reporting to interpretation.
```

## Abstract

- 用最短路径交代“问题、方法、关键结果、意义”
- 结果句优先放最能代表贡献的数字
- 不写抽象空话，不把引言背景复制进摘要

## Introduction

- 用问题推动，而不是只堆背景
- 局限性要具体，可用 First/Second/Third 或等价结构组织
- 结尾明确本文解决什么问题、贡献是什么

## Methods

- 以可复现为底线
- 软件、包、版本、阈值、统计方法要交代清楚
- 避免把 Results 的结论偷写进 Methods

## Results

- 只陈述事实，不做 Discussion 式解释
- 每段有清楚的小目标
- 关键数字能回溯到 Figure/Table/源材料
- 子节顺序应服务于主线，而不是机械跟随编号
- 同一段内若需要连续呈现多个证据点、多个组别对比或主结果 + 验证结果，优先同段分点换行，让每一行都对应一个可定位的结果点
- `Results` 的具体性主要体现在数字、比较、图表锚点和跨队列验证，不要把意义阐释提前写成 `Discussion`

## Discussion

- 先解释核心发现，再谈意义和局限
- 局限性要诚实且具体
- 与已有文献的关系要清楚，但避免堆砌文献摘要
- 同一段内串联多个解释、局限或 future direction 时，可一观点一行；只有在语义切换为新段时才插空行
- `Discussion` 不是压缩版 `Results`；不要逐图复述 `AUC/ORR/HR/p value`、图号和检验名
- 每段默认最多保留 `1` 个核心定量锚点，而且这个锚点必须直接服务于后续解释
- `Discussion` 的具体性主要体现在机制解释、临床定位、文献对位、边界条件和未来验证路径，而不是数字堆叠

## Conclusion

- 精炼，避免引入新结果
- 强调贡献边界，不夸大

## Figure Legends

- 标题应先点出图的主题对象或主要任务，而不只是罗列图形元素
- 子图说明至少回答三件事：`这个 panel 在展示什么`、`图形编码分别代表什么`、`读者该怎样判读`
- x/y 轴、行列、颜色方向、点大小、顶部或侧边条形图、注释轨道、聚类方式、参考线等视觉编码要写清楚
- 若使用标准化、z-score、不同 y 轴尺度、隐藏标签、灰色表示非显著或缺失，要补一句说明其判读方式或这样做的原因
- 缩写和专业术语首次出现时给出全称；这里的“首次出现”按整篇论文所有正文 tex 联合判断，不按当前文件单独判断；如果对非领域读者不直观，补一个简短的人话解释
- 统计标注、样本量、删失标记、risk table、显著性星号等可视符号要完整解码
- Supplementary Figure legend 默认与主图同等详尽，不要简写成提纲
- 避免两种坏写法：只机械复述 `(A)(B)(C)` 面板标题；或者把整段 Methods 搬进图注
- 同一条 legend 下，不同 panel、不同判读动作或不同图表证据点优先逐行写；如果仍属于同段，就不要插空行
