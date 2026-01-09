#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

from typing import Any, Dict, Optional

from .ai_integration import AIIntegration
from .latex_parser import strip_comments


class BoastfulExpressionAI:
    """
    AI 主导的“可能引起评审不适的表述”识别。

    说明：
    - 不依赖禁词表，而是基于语义判断是否存在无对照/无证据的自我夸大
    - AI 不可用时返回空 issues（不阻断），由硬编码高风险示例做快速提示
    """

    def __init__(self, ai: AIIntegration) -> None:
        self.ai = ai

    async def check(
        self,
        *,
        tex_text: str,
        cache_dir: Optional[Any] = None,
        fresh: bool = False,
    ) -> Dict[str, Any]:
        prompt = """
请分析以下立项依据文本，识别“可能引起评审专家不适的表述”。

评审专家通常反感的表述类型：
1) 绝对化表述：无对照的“最/首/唯一/领先/首创”
2) 填补空白式：“填补空白”“开创性”无具体指标
3) 无依据夸大：“重大/重要/关键”无数据/对比支撑
4) 自我定性：用绝对形容词自我评价（无第三方引用）

请注意区分：
- 有数据/引用支撑的结论是 OK 的（如“相比 X 方法提升 30%”“引用自 Y 期刊”）
- 无依据的自我夸大需要标记

要求：
- 只输出 JSON，不要解释
- 原文片段请截取不超过 50 字
- 不要杜撰文献引用与 DOI

返回 JSON：
{
  "issues": [
    {
      "category": "绝对化表述|填补空白|无依据夸大|自我定性",
      "text": "原文片段（不超过 50 字）",
      "reason": "为何会引起评审不适",
      "suggestion": "如何改为可验证/可对照的表述"
    }
  ],
  "summary": {
    "total_issues": 3,
    "by_category": {"绝对化表述": 2, "无依据夸大": 1}
  }
}
""".strip()

        cleaned = strip_comments(tex_text or "")[:20000]
        prompt = prompt + "\n\n文本内容（去注释后，最多 20000 字符）：\n" + cleaned

        def _fallback() -> Dict[str, Any]:
            return {"issues": [], "summary": {"total_issues": 0, "by_category": {}}, "_mode": "fallback"}

        obj = await self.ai.process_request(
            task="boastful_expression_check",
            prompt=prompt,
            fallback=_fallback,
            output_format="json",
            cache_dir=cache_dir,
            fresh=fresh,
        )
        if not isinstance(obj, dict):
            return _fallback()
        obj.setdefault("_mode", "ai" if self.ai.is_available() else "fallback")
        return obj

