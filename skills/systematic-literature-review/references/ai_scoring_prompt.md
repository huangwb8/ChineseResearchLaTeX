# AI 自动评分 Prompt 模板

> 用于让宿主 AI 直接阅读标题与摘要并生成 `scored_papers.jsonl`。目标是**高区分度评分 + 稳定子主题 + 同步数据抽取**。

## 使用前提

- 优先用英文主题；中文主题也可，但要尽量明确研究对象、任务和方法。
- 输入至少包含：`topic`、`title`、`abstract`、`year`、`venue`、`authors`、`doi`

## 评分 Prompt（最小版）

```text
你是一位学术文献评审专家。请评估以下论文与研究主题的相关性，并输出严格 JSON。

研究主题：{topic}
时间范围：{time_range}
核心问题：{core_question}

论文信息：
- DOI: {doi}
- 标题: {title}
- 摘要: {abstract}
- 年份: {year}
- 期刊/会议: {venue}
- 作者: {authors}

评分维度：
1. 任务匹配度
2. 方法匹配度
3. 数据模态匹配度
4. 应用价值

评分标准：
- 9.0-10.0：相同任务 + 相同方法 + 相同模态
- 7.0-8.9：相同任务，方法或模态略有差异
- 5.0-6.9：同领域但任务/方法/模态差异明显
- 3.0-4.9：仅部分概念或技术重叠
- 1.0-2.9：几乎无关

子主题规则：
- 仅当 score >= 5.0 时填写 subtopic
- score < 5.0 时，subtopic 必须为 ""
- 子主题应尽量收敛到 5-7 个簇，避免细分过度

请同步提取：
- design：研究设计/方法（5-15字）
- key_findings：关键结果（尽量含数字）
- limitations：局限性；若无证据则填“未明确提及”

只输出 JSON：
{
  "doi": "{doi}",
  "score": 0.0,
  "subtopic": "",
  "rationale": "",
  "alignment": {
    "task": "完全匹配/部分匹配/不匹配",
    "method": "完全匹配/部分匹配/不匹配",
    "modality": "完全匹配/部分匹配/不匹配"
  },
  "extraction": {
    "design": "",
    "key_findings": "",
    "limitations": ""
  }
}
```

## 子主题收敛规则

- 相似 CNN 架构统一并到 `CNN分类`
- Transformer / Attention / ViT 统一并到 `Transformer分类`
- 弱监督 / 半监督 / 多实例学习统一并到 `弱监督学习`
- 迁移学习 / 微调 / 预训练统一并到 `迁移学习`
- 单例子主题优先并入最接近的大类

## 输出质量自检

- 高分论文大约 20-40%
- 中分论文大约 40-60%
- 低分论文大约 10-30%
- 子主题总数控制在 5-7 个
- `design` 不能只写“深度学习”
- `key_findings` 尽量含样本量或性能指标
- `limitations` 没证据时写“未明确提及”
