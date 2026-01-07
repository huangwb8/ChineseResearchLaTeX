"""
SemanticAnalyzer - AI 驱动语义分析器
🧠 AI：理解章节主题、推理资源相关性、评估内容质量
"""

from typing import List, Dict, Any
from dataclasses import dataclass
from pathlib import Path


@dataclass
class SectionTheme:
    """章节主题分析结果"""
    theme: str                      # 章节核心主题
    key_concepts: List[str]         # 关键概念列表
    writing_style: str              # 写作风格：学术/技术/说明
    suggested_resources: List[str]  # 建议的资源类型
    tone: str                       # 语调：正式/通俗
    target_audience: str            # 目标读者：专家/评审/大众


@dataclass
class ResourceRelevance:
    """资源相关性评估结果"""
    resource_path: str
    relevance_score: float          # 0-1 相关性分数
    reason: str                     # AI 给出的理由
    suggested_usage: str            # 建议的使用方式


class SemanticAnalyzer:
    """AI 驱动的语义分析器"""

    def __init__(self, llm_client):
        """
        Args:
            llm_client: LLM 客户端（Claude/OpenAI/本地模型）
        """
        self.llm = llm_client

    def analyze_section_theme(self, tex_content: str) -> SectionTheme:
        """
        分析章节的核心主题和写作意图

        Args:
            tex_content: LaTeX 文件内容（前 2000 字符）

        Returns:
            SectionTheme: 结构化的主题分析结果
        """
        prompt = f"""
你是一位专业的学术写作分析专家。请分析以下 LaTeX 章节的内容主题。

章节内容（前 2000 字符）：
{tex_content[:2000]}

请返回 JSON 格式的分析结果：
{{
  "theme": "章节的核心主题（一句话概括）",
  "key_concepts": ["关键概念1", "关键概念2", "关键概念3"],
  "writing_style": "学术/技术/说明/混合",
  "suggested_resources": ["建议的图片类型", "建议的文献领域"],
  "tone": "正式/半正式/通俗",
  "target_audience": "评审专家/同行/学生/大众"
}}
"""

        response = self.llm.complete(
            prompt,
            response_format="json",
            temperature=0.3  # 低温度保证稳定性
        )

        import json
        data = json.loads(response)
        return SectionTheme(**data)

    def reason_resource_relevance(
        self,
        resource_info: 'ResourceInfo',
        section_theme: SectionTheme
    ) -> ResourceRelevance:
        """
        推理资源与章节的相关性

        Args:
            resource_info: 资源信息（图片/代码/文献）
            section_theme: 章节主题

        Returns:
            ResourceRelevance: 相关性评估结果
        """
        prompt = f"""
你是一位专业的学术写作顾问。请评估以下资源是否适合用于指定章节。

章节信息：
- 主题：{section_theme.theme}
- 关键概念：{', '.join(section_theme.key_concepts)}
- 写作风格：{section_theme.writing_style}
- 建议资源：{', '.join(section_theme.suggested_resources)}

资源信息：
- 路径：{resource_info.path}
- 类型：{resource_info.type}
- 元数据：{resource_info.metadata}

请返回 JSON 格式的评估结果：
{{
  "relevance_score": 0.85,  // 0-1 之间的分数
  "reason": "详细说明为什么适合或不适合，100-200字",
  "suggested_usage": "建议如何使用这个资源（如：作为方法论示意图）"
}}
"""

        response = self.llm.complete(
            prompt,
            response_format="json",
            temperature=0.3
        )

        import json
        data = json.loads(response)
        return ResourceRelevance(
            resource_path=resource_info.path,
            relevance_score=data['relevance_score'],
            reason=data['reason'],
            suggested_usage=data['suggested_usage']
        )

    def generate_contextual_description(
        self,
        resource: 'ResourceInfo',
        context: str,
        usage_hint: str = None
    ) -> str:
        """
        为资源生成符合上下文的描述文字

        Args:
            resource: 资源信息
            context: 上下文内容（章节片段）
            usage_hint: 使用提示（可选）

        Returns:
            str: 自然的描述文字（50-100 字）
        """
        prompt = f"""
你是一位经验丰富的学术写作者。请为以下资源生成一段自然的描述文字。

上下文（章节片段）：
{context[:500]}

资源信息：
- 文件名：{resource.filename}
- 类型：{resource.type}
- 建议用途：{usage_hint or '未指定'}

要求：
1. 生成 50-100 字的描述文字
2. 符合学术写作风格
3. 与上下文自然衔接
4. 包含适当的引入语（如"如图 X 所示"、"根据文献 X"等）

只返回描述文字，不要解释。
"""

        return self.llm.complete(prompt, temperature=0.7)

    def evaluate_content_quality(
        self,
        content: str,
        section_theme: SectionTheme = None
    ) -> Dict[str, Any]:
        """
        评估生成内容的质量

        Args:
            content: 生成的内容
            section_theme: 章节主题（可选，用于对比）

        Returns:
            Dict: 质量评估报告
        """
        prompt = f"""
你是一位严谨的学术写作评审专家。请评估以下示例内容的质量。

评估内容：
{content[:2000]}

章节主题（供参考）：
{section_theme.theme if section_theme else '未指定'}

请返回 JSON 格式的评估报告：
{{
  "coherence": 0.92,  // 连贯性评分 0-1
  "academic_tone": 0.88,  // 学术风格评分 0-1
  "resource_integration": "自然/生硬/无",  // 资源整合评价
  "strengths": ["优点1", "优点2"],
  "weaknesses": ["不足1", "不足2"],
  "suggestions": ["改进建议1", "改进建议2"],
  "overall_score": 0.90  // 总体评分 0-1
}}
"""

        response = self.llm.complete(
            prompt,
            response_format="json",
            temperature=0.3
        )

        import json
        return json.loads(response)
