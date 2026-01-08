"""
AI 内容智能优化器
自动识别并优化内容质量问题
"""

import json
import re
from typing import Dict, List, Optional
from pathlib import Path

from .ai_integration import AIIntegration
from .reference_guardian import ReferenceGuardian


class ContentOptimizer:
    """AI 内容智能优化器"""

    def __init__(self, config: dict, skill_root: str):
        self.config = config
        self.skill_root = Path(skill_root)
        self.ref_guardian = ReferenceGuardian(config)

    async def optimize_content(
        self,
        content: str,
        section_title: str,
        optimization_goals: dict,
        ai_integration: Optional[AIIntegration] = None,
    ) -> dict:
        """智能优化内容"""
        if ai_integration is None:
            ai_integration = AIIntegration(enable_ai=True, config=self.config)

        # 第一步：保护引用
        protected_content, ref_map = self.ref_guardian.protect_references(content)
        original_refs = self.ref_guardian._extract_all_references(content)

        # 第二步：AI 分析优化点
        analysis = await self._analyze_optimization_points(
            protected_content, section_title, optimization_goals, ai_integration
        )

        # 第三步：执行优化
        optimized_content = protected_content
        optimization_log = []

        for point in analysis.get("optimization_points", []):
            result = await self._apply_optimization(optimized_content, point, ai_integration)
            if result.get("success"):
                optimized_content = result["content"]
                optimization_log.append({
                    "type": point["type"],
                    "description": point["description"],
                    "action": result["action"]
                })

        # 第四步：恢复引用
        final_content = self.ref_guardian.restore_references(optimized_content, ref_map)

        # 第五步：验证引用完整性
        validation = self.ref_guardian.validate_references(final_content, original_refs)

        return {
            "original_content": content,
            "optimized_content": final_content,
            "optimization_log": optimization_log,
            "reference_validation": validation,
            "improvement_score": analysis.get("improvement_potential", 0)
        }

    async def _analyze_optimization_points(
        self,
        content: str,
        section_title: str,
        goals: dict,
        ai_integration: AIIntegration,
    ) -> dict:
        """AI 分析优化点（使用当前 AI 环境）"""
        # 构建分析提示
        goal_desc = []
        if goals.get("remove_redundancy"):
            goal_desc.append("冗余表述")
        if goals.get("improve_logic"):
            goal_desc.append("逻辑连贯性")
        if goals.get("add_evidence"):
            goal_desc.append("证据支持")
        if goals.get("improve_clarity"):
            goal_desc.append("表述清晰度")
        if goals.get("reorganize_structure"):
            goal_desc.append("段落结构")

        goals_str = "、".join(goal_desc) if goal_desc else "整体质量"

        prompt = f"""你是学术写作专家。请分析以下"{section_title}"的内容在{goals_str}方面的问题。

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
{content[:1500]}

请直接输出 JSON："""

        def fallback() -> dict:
            return self._heuristic_analysis(content, goals)

        result = await ai_integration.process_request(
            task="analyze_optimization_points",
            prompt=prompt,
            fallback=fallback,
            output_format="json",
        )

        return result if isinstance(result, dict) else fallback()

    def _heuristic_analysis(self, content: str, goals: dict) -> dict:
        """启发式分析（AI 失败时的回退方案）"""
        optimization_points = []

        if goals.get("remove_redundancy"):
            # 检测重复词（粗略启发式）
            # 1) 统计较短的中文片段出现次数（更能捕捉“测试测试测试...”这类重复）
            chunks = re.findall(r"[\u4e00-\u9fff]+", content)
            bigrams: Dict[str, int] = {}
            for chunk in chunks:
                if len(chunk) < 2:
                    continue
                for i in range(0, len(chunk) - 1):
                    bg = chunk[i : i + 2]
                    bigrams[bg] = bigrams.get(bg, 0) + 1

            if bigrams:
                bg, count = max(bigrams.items(), key=lambda x: x[1])
                if count >= 15:
                    optimization_points.append(
                        {
                            "type": "redundancy",
                            "description": f"短语'{bg}'重复{count}次（疑似冗余）",
                            "location": "全文",
                            "severity": "medium",
                            "suggestion": "替换同义词或重组表述",
                        }
                    )

            # 2) 统计连续中文“词块”重复（适合有分隔符的场景）
            if not optimization_points:
                words = re.findall(r"[\u4e00-\u9fff]{2,}", content)
                word_counts: Dict[str, int] = {}
                for word in words:
                    word_counts[word] = word_counts.get(word, 0) + 1

                for word, count in word_counts.items():
                    if count > 8:
                        optimization_points.append(
                            {
                                "type": "redundancy",
                                "description": f"词语'{word}'重复{count}次",
                                "location": "全文",
                                "severity": "medium",
                                "suggestion": "替换同义词或重组表述",
                            }
                        )
                        break

        if goals.get("improve_logic"):
            # 检测段落连接
            paragraphs = content.split('\n\n')
            if len(paragraphs) > 1 and not any('因此' in p or '总之' in p for p in paragraphs):
                optimization_points.append({
                    "type": "logic",
                    "description": "段落间缺乏过渡",
                    "location": "全文",
                    "severity": "medium",
                    "suggestion": "添加过渡句"
                })

        if goals.get("add_evidence") and len(content) < 500:
            optimization_points.append({
                "type": "evidence",
                "description": "内容可能缺乏充分论证",
                "location": "全文",
                "severity": "high",
                "suggestion": "补充数据或案例支持"
            })

        return {
            "optimization_points": optimization_points,
            "improvement_potential": min(0.7, len(optimization_points) * 0.2)
        }

    async def _apply_optimization(self, content: str, optimization_point: dict, ai_integration: AIIntegration) -> dict:
        """应用单个优化点（使用当前 AI 环境）"""
        opt_type = optimization_point["type"]
        description = optimization_point["description"]

        # 根据类型构建优化提示
        prompts = {
            "redundancy": f"""请删除以下内容中的冗余表述。

问题：{description}

要求：
1. 删除重复或不必要的表述
2. 保留核心信息和论点
3. 保持逻辑连贯

原文：
{{content}}

请直接输出优化后的内容：""",

            "logic": f"""请改进以下内容的逻辑连贯性。

问题：{description}

要求：
1. 添加适当的过渡句
2. 调整段落顺序使其更连贯
3. 保持原有论点不变

原文：
{{content}}

请直接输出优化后的内容：""",

            "evidence": f"""请为以下内容补充证据支持。

问题：{description}

要求：
1. 在适当位置添加[此处需补充数据/案例]标记
2. 不要大幅改动原有内容
3. 保持学术严谨性

原文：
{{content}}

请直接输出优化后的内容：""",

            "clarity": f"""请提高以下内容的表述清晰度。

问题：{description}

要求：
1. 简化复杂句式
2. 替换模糊表述
3. 保持专业性

原文：
{{content}}

请直接输出优化后的内容：""",

            "structure": f"""请重组以下内容的段落结构。

问题：{description}

要求：
1. 调整段落顺序
2. 合理分段
3. 保持内容完整性

原文：
{{content}}

请直接输出优化后的内容："""
        }

        prompt_template = prompts.get(opt_type)
        if not prompt_template:
            return {"success": False, "reason": f"未知优化类型: {opt_type}"}

        prompt = prompt_template.replace("{content}", content[:2000])  # 限制长度

        def fallback() -> str:
            return ""

        response = await ai_integration.process_request(
            task=f"apply_optimization_{opt_type}",
            prompt=prompt,
            fallback=fallback,
            output_format="text",
        )

        response_text = str(response or "").strip()
        if response_text:
            return {"success": True, "content": response_text, "action": f"优化{opt_type}"}
        return {"success": False, "reason": "AI 不可用或未返回内容"}

    def generate_optimization_report(self, content: str, section_title: str) -> dict:
        """生成优化报告（不执行优化，仅分析）"""
        # 简单的启发式分析
        issues = []

        # 检测可能的问题
        if content.count("\n\n") < 2:
            issues.append({
                "type": "structure",
                "severity": "low",
                "description": "段落结构可能过于简单"
            })

        if len(content) < 500:
            issues.append({
                "type": "evidence",
                "severity": "medium",
                "description": "内容可能过于简略"
            })

        # 检测重复词
        words = re.findall(r'[\u4e00-\u9fff]{2,}', content)
        word_counts = {}
        for word in words:
            word_counts[word] = word_counts.get(word, 0) + 1

        for word, count in word_counts.items():
            if count > 10:
                issues.append({
                    "type": "redundancy",
                    "severity": "low",
                    "description": f"词语'{word}'重复{count}次，可能存在冗余"
                })

        return {
            "section": section_title,
            "total_issues": len(issues),
            "issues": issues,
            "improvement_potential": min(0.8, len(issues) * 0.15)
        }
