# AI 提示词模板
# 用于减少代码中的硬编码提示词

# 映射引擎提示词
MAPPING_JUDGE_TEMPLATE = """你是一个 NSFC 标书迁移专家。请判断以下两个文件是否应该建立映射关系。

{context}

请从以下维度判断：
1. **文件名语义**：文件名是否表示相同或相似的内容
2. **章节结构**：LaTeX 章节结构是否对应
3. **内容语义**：内容的主题和目的是否一致
4. **迁移合理性**：将旧文件内容迁移到新文件是否符合逻辑

请按以下格式回复（必须严格按格式）：
```json
{{
    "should_map": true/false,
    "confidence": "high/medium/low",
    "score": 0.0-1.0,
    "reason": "详细说明理由（中文）"
}}
```

评分标准：
- score >= 0.85: high confidence，高度确定应该映射
- 0.7 <= score < 0.85: medium confidence，比较确定应该映射
- 0.5 <= score < 0.7: low confidence，可能应该映射，需人工确认
- score < 0.5: 不应该映射
"""

# 内容优化提示词模板
OPTIMIZE_ANALYZE_TEMPLATE = """你是学术写作专家。请分析以下"{section_title}"的内容在{goals_str}方面的问题。

要求：
1. 识别 2-4 个最需要优化的问题点
2. 每个问题点包括：类型、位置、严重程度（high/medium/low）、改进建议
3. 仅输出 JSON 格式，不要额外解释

JSON 格式：
{{
  "optimization_points": [
    {{
      "type": "redundancy|logic|evidence|clarity|structure",
      "description": "问题描述",
      "location": "第X段",
      "severity": "high|medium|low",
      "suggestion": "改进建议"
    }}
  ],
  "improvement_potential": 0.7
}}

原文：
{content}

请直接输出 JSON："""

# 优化类型提示词
OPTIMIZE_TYPE_PROMPTS = {
    "redundancy": """请删除以下内容中的冗余表述。

问题：{description}

要求：
1. 删除重复或不必要的表述
2. 保留核心信息和论点
3. 保持逻辑连贯

原文：
{{content}}

请直接输出优化后的内容：""",

    "logic": """请改进以下内容的逻辑连贯性。

问题：{description}

要求：
1. 添加适当的过渡句
2. 调整段落顺序使其更连贯
3. 保持原有论点不变

原文：
{{content}}

请直接输出优化后的内容：""",

    "evidence": """请为以下内容补充证据支持。

问题：{description}

要求：
1. 在适当位置添加[此处需补充数据/案例]标记
2. 不要大幅改动原有内容
3. 保持学术严谨性

原文：
{{content}}

请直接输出优化后的内容：""",

    "clarity": """请提高以下内容的表述清晰度。

问题：{description}

要求：
1. 简化复杂句式
2. 替换模糊表述
3. 保持专业性

原文：
{{content}}

请直接输出优化后的内容：""",

    "structure": """请重组以下内容的段落结构。

问题：{description}

要求：
1. 调整段落顺序
2. 合理分段
3. 保持内容完整性

原文：
{{content}}

请直接输出优化后的内容："""
}

# 字数适配提示词模板
WORD_COUNT_EXPAND_TEMPLATE = """你是 NSFC 标书写作专家。请扩展以下"{section_title}"的内容。

要求：
1. 扩展约 {deficit} 字（当前约 {current_count} 字，目标约 {target_count} 字）
2. 保持原有逻辑和核心论点
3. 增加论据、案例、数据支撑
4. 深化分析层次
5. 保持学术严谨性

原文：
{content}

请直接输出扩展后的完整内容，不要解释。"""

WORD_COUNT_COMPRESS_TEMPLATE = """你是 NSFC 标书写作专家。请精简以下"{section_title}"的内容。

要求：
1. 精简约 {excess} 字（当前约 {current_count} 字，目标约 {target_count} 字）
2. 保留所有核心论点和关键信息
3. 删除冗余表述和重复内容
4. 保持逻辑连贯性
5. 保持学术严谨性

原文：
{content}

请直接输出精简后的完整内容，不要解释。"""
