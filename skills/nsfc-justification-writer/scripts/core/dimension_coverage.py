#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from .ai_integration import AIIntegration
from .latex_parser import strip_comments


@dataclass(frozen=True)
class DimensionCoverageResult:
    dimensions: Dict[str, Dict[str, Any]]
    missing_dimensions: List[str]
    suggestions: List[str]
    mode: str  # ai | fallback


def _fallback_heuristic(tex_text: str) -> DimensionCoverageResult:
    text = strip_comments(tex_text or "")
    text = re.sub(r"\\[a-zA-Z@]+(?:\*?)\s*(?:\[[^\\]]*\\])?\s*\{[^}]*\}", " ", text)
    text = re.sub(r"\\[a-zA-Z@]+(?:\*?)\b", " ", text)
    text = re.sub(r"\s+", " ", text).strip()

    dims: Dict[str, List[str]] = {
        "价值与必要性": ["痛点", "需求", "必要", "亟需", "迫切", "挑战", "问题", "负担", "成本", "影响"],
        "现状与不足": ["现状", "已有", "研究", "方法", "工作", "不足", "局限", "瓶颈", "然而", "仍然", "尚无"],
        "科学问题/假说": ["科学问题", "关键科学问题", "核心假说", "科学假设", "假说", "假设", "我们提出", "本研究提出"],
        "项目切入点": ["本项目", "我们将", "拟", "计划", "切入点", "提出", "建立", "开发", "设计", "针对"],
    }

    out_dims: Dict[str, Dict[str, Any]] = {}
    missing: List[str] = []
    suggestions: List[str] = []
    for name, kws in dims.items():
        hit = next((k for k in kws if k and (k in text)), "")
        covered = bool(hit)
        conf = 0.55 if covered else 0.3
        out_dims[name] = {"covered": covered, "confidence": conf, "evidence": (hit or "")}
        if not covered:
            missing.append(name)
            suggestions.append(f"建议补充“{name}”相关表述（当前未检测到明显信号词）。")

    return DimensionCoverageResult(
        dimensions=out_dims,
        missing_dimensions=missing,
        suggestions=suggestions[:6],
        mode="fallback",
    )


class DimensionCoverageAI:
    """
    AI 主导的内容维度覆盖检查（不依赖标题用词）。
    """

    def __init__(self, ai: AIIntegration) -> None:
        self.ai = ai

    async def check(
        self,
        *,
        tex_text: str,
        max_chars: int,
        cache_dir: Optional[Any] = None,
        fresh: bool = False,
    ) -> Dict[str, Any]:
        prompt = """
请分析以下立项依据文本是否覆盖了 4 个必要维度（不依赖标题用词）：
1) 价值与必要性：说明为什么要做、痛点是什么
2) 现状与不足：现有工作及其局限性
3) 科学问题/假说：核心假说与关键科学问题
4) 项目切入点：本项目相对现有工作的差异化切口

要求：
- 只输出 JSON，不要解释
- 证据字段请引用原文“片段”（不超过 50 字），不要杜撰引用与 DOI

返回 JSON：
{
  "dimensions": {
    "价值与必要性": {"covered": true, "confidence": 0.95, "evidence": "..."},
    "现状与不足": {"covered": true, "confidence": 0.88, "evidence": "..."},
    "科学问题/假说": {"covered": false, "confidence": 0.40, "evidence": ""},
    "项目切入点": {"covered": true, "confidence": 0.83, "evidence": "..."}
  },
  "missing_dimensions": ["科学问题/假说"],
  "suggestions": ["建议补充核心假说..."]
}
""".strip()

        cleaned = strip_comments(tex_text or "")
        max_chars = max(int(max_chars), 1000)
        cleaned = cleaned[:max_chars]
        prompt = prompt + f"\n\n文本内容（去注释后，最多 {max_chars} 字符）：\n" + cleaned

        def _fallback() -> Dict[str, Any]:
            fb = _fallback_heuristic(cleaned)
            return {
                "dimensions": fb.dimensions,
                "missing_dimensions": fb.missing_dimensions,
                "suggestions": fb.suggestions,
                "_mode": fb.mode,
            }

        obj = await self.ai.process_request(
            task="dimension_coverage",
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


def format_dimension_coverage_markdown(obj: Dict[str, Any]) -> str:
    dims = obj.get("dimensions") if isinstance(obj.get("dimensions"), dict) else {}
    missing = obj.get("missing_dimensions") if isinstance(obj.get("missing_dimensions"), list) else []
    sugg = obj.get("suggestions") if isinstance(obj.get("suggestions"), list) else []

    lines: List[str] = []
    covered_count = 0
    for name in ["价值与必要性", "现状与不足", "科学问题/假说", "项目切入点"]:
        info = dims.get(name) if isinstance(dims, dict) else None
        covered = bool(info.get("covered")) if isinstance(info, dict) else False
        if covered:
            covered_count += 1

    lines.append(f"- ⚠️ 内容维度覆盖度：{covered_count}/4")
    for name in ["价值与必要性", "现状与不足", "科学问题/假说", "项目切入点"]:
        info = dims.get(name) if isinstance(dims, dict) else None
        covered = bool(info.get("covered")) if isinstance(info, dict) else False
        conf = float(info.get("confidence", 0.0)) if isinstance(info, dict) else 0.0
        tag = "✅" if covered else "❌"
        conf_txt = ""
        if conf > 0:
            conf_txt = "（高置信度）" if conf >= 0.85 else ("（中置信度）" if conf >= 0.6 else "（低置信度）")
        lines.append(f"  - {tag} {name}{conf_txt}")

    if missing:
        lines.append("  - ❌ 缺失维度：" + "、".join([str(x) for x in missing if str(x).strip()][:4]))
    if sugg:
        lines.append("  - 建议：" + "；".join([str(x) for x in sugg if str(x).strip()][:3]))
    mode = str(obj.get("_mode", "") or "").strip()
    if mode:
        lines.append(f"  - 来源：{mode}")
    return "\n".join(lines).strip() + "\n"
