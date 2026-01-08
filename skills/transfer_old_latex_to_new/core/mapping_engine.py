#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .config_loader import get_ai_config, get_mapping_thresholds
from .latex_utils import safe_read_text
from .project_analyzer import ProjectAnalysis


@dataclass(frozen=True)
class MappingCandidate:
    old: str
    new: str
    score: float
    confidence: str
    reason: str


@dataclass(frozen=True)
class OneToOne:
    old: str
    new: str
    score: float
    confidence: str
    reason: str


@dataclass(frozen=True)
class StructureDiff:
    one_to_one: List[OneToOne]
    new_added: List[Dict[str, str]]
    removed: List[Dict[str, str]]
    low_confidence: List[Dict[str, str]]

    def to_dict(self) -> Dict:
        return {
            "mapping": {
                "one_to_one": [asdict(x) for x in self.one_to_one],
                "new_added": self.new_added,
                "removed": self.removed,
                "low_confidence": self.low_confidence,
            }
        }


def _build_file_context(old_analysis: ProjectAnalysis, new_analysis: ProjectAnalysis, old_rel: str, new_rel: str) -> str:
    """
    为 AI 构建文件上下文信息，用于语义判断映射关系
    """
    # 旧文件信息
    old_info = old_analysis.tex_files.get(old_rel)
    old_path = old_analysis.root_path / old_rel
    old_content = safe_read_text(old_path) if old_path.exists() else ""

    # 新文件信息
    new_info = new_analysis.tex_files.get(new_rel)
    new_path = new_analysis.root_path / new_rel
    new_content = safe_read_text(new_path) if new_path.exists() else ""

    # 构建上下文
    context_parts = [
        "=== 旧项目文件 ===",
        f"路径: {old_rel}",
        f"文件名: {Path(old_rel).name}",
    ]

    if old_info:
        if old_info.headings:
            context_parts.append("章节结构:")
            for h in old_info.headings[:3]:  # 只取前3个标题，避免 token 过多
                level = h.get("level", "")
                title = h.get("title", "")
                if title:
                    context_parts.append(f"  {level} {title}")

        if old_info.summary:
            context_parts.append(f"内容摘要: {old_info.summary}")

    # 取内容前500字符作为预览
    if old_content:
        preview = old_content[:500].replace("\n", " ")
        context_parts.append(f"内容预览: {preview}...")

    context_parts.extend([
        "",
        "=== 新项目文件 ===",
        f"路径: {new_rel}",
        f"文件名: {Path(new_rel).name}",
    ])

    if new_info:
        if new_info.headings:
            context_parts.append("章节结构:")
            for h in new_info.headings[:3]:
                level = h.get("level", "")
                title = h.get("title", "")
                if title:
                    context_parts.append(f"  {level} {title}")

        if new_info.summary:
            context_parts.append(f"内容摘要: {new_info.summary}")

    if new_content:
        preview = new_content[:500].replace("\n", " ")
        context_parts.append(f"内容预览: {preview}...")

    return "\n".join(context_parts)


def _extract_ai_mapping_response(response_text: str) -> Optional[Dict[str, Any]]:
    """
    从 AI 响应中提取结构化的映射判断结果
    支持格式：
    1. JSON 格式
    2. 格式化文本（用特定关键字）
    """
    # 尝试解析 JSON
    try:
        # 尝试提取 JSON 块
        if "```json" in response_text:
            json_start = response_text.find("```json") + 7
            json_end = response_text.find("```", json_start)
            json_str = response_text[json_start:json_end].strip()
            return json.loads(json_str)
        elif "{" in response_text:
            # 尝试找到第一个完整的 JSON 对象
            start = response_text.find("{")
            # 找到匹配的结束括号
            depth = 0
            for i in range(start, len(response_text)):
                if response_text[i] == "{":
                    depth += 1
                elif response_text[i] == "}":
                    depth -= 1
                    if depth == 0:
                        json_str = response_text[start:i+1]
                        return json.loads(json_str)
    except (json.JSONDecodeError, ValueError):
        pass

    # 尝试从文本中提取关键信息
    result = {
        "should_map": False,
        "confidence": "low",
        "score": 0.0,
        "reason": "",
    }

    lines = response_text.split("\n")
    for line in lines:
        line_lower = line.lower()
        if "should map" in line_lower or "应该映射" in response_text[:200]:
            if "true" in line_lower or "yes" in line_lower or "是" in line:
                result["should_map"] = True
        if "confidence" in line_lower or "置信度" in response_text[:200]:
            if "high" in line_lower or "高" in line:
                result["confidence"] = "high"
            elif "medium" in line_lower or "中" in line:
                result["confidence"] = "medium"
        if "score" in line_lower or "评分" in response_text[:200]:
            # 尝试提取数字
            import re
            numbers = re.findall(r"[\d.]+", line)
            if numbers:
                score = float(numbers[0])
                result["score"] = min(score, 1.0)  # 确保不超过 1.0

    # 如果 AI 认为应该映射，给一个默认分数
    if result["should_map"] and result["score"] == 0.0:
        if result["confidence"] == "high":
            result["score"] = 0.85
        elif result["confidence"] == "medium":
            result["score"] = 0.75
        else:
            result["score"] = 0.65

    return result if result["should_map"] else None


async def _ai_judge_mapping(
    old_analysis: ProjectAnalysis,
    new_analysis: ProjectAnalysis,
    old_rel: str,
    new_rel: str,
    config: Dict,
) -> Optional[Dict[str, Any]]:
    """
    让 AI 判断两个文件是否应该映射，返回结构化结果

    注意：这是一个异步函数占位符。在实际集成时，需要通过
    Skill 工具调用 AI 模型进行判断。
    """
    # 构建上下文
    context = _build_file_context(old_analysis, new_analysis, old_rel, new_rel)

    # AI 判断提示词
    prompt = f"""你是一个 NSFC 标书迁移专家。请判断以下两个文件是否应该建立映射关系。

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

    # TODO: 这里需要实际调用 AI 模型
    # 目前返回 None 表示使用回退策略（简单的字符串匹配）
    return None


def _fallback_score_pair(old_rel: str, new_rel: str) -> Tuple[float, str]:
    """
    回退策略：当 AI 不可用时，使用简单的启发式规则

    这是一个保守的回退方案，只在 AI 不可用时使用
    """
    from .latex_utils import jaccard, normalize_filename, tokenize

    old_stem = normalize_filename(Path(old_rel).stem)
    new_stem = normalize_filename(Path(new_rel).stem)

    # 文件名完全匹配
    if old_stem == new_stem:
        return 1.0, f"文件名完全匹配: {old_stem}"

    # 文件名包含关系
    if old_stem in new_stem or new_stem in old_stem:
        return 0.8, f"文件名包含关系: {old_stem} <-> {new_stem}"

    # Jaccard 相似度
    tokens_old = tokenize(old_stem)
    tokens_new = tokenize(new_stem)
    if tokens_old and tokens_new:
        score = jaccard(tokens_old, tokens_new)
        if score >= 0.7:
            return score, f"文件名相似度: {score:.2f}"

    return 0.0, "无足够相似度"


async def compute_structure_diff_async(
    old_analysis: ProjectAnalysis,
    new_analysis: ProjectAnalysis,
    config: Dict,
    ai_available: bool = True,
) -> StructureDiff:
    """
    AI 驱动的结构差异分析（异步版本）

    Args:
        old_analysis: 旧项目分析结果
        new_analysis: 新项目分析结果
        config: 配置字典
        ai_available: AI 是否可用（如果不可用，使用回退策略）

    Returns:
        StructureDiff: 结构差异对象
    """
    thresholds = get_mapping_thresholds(config)

    old_candidates = [p for p in old_analysis.extra_tex_files if p != "extraTex/@config.tex"]
    new_candidates = [p for p in new_analysis.extra_tex_files if p != "extraTex/@config.tex"]

    scored: List[MappingCandidate] = []

    # 如果 AI 可用，使用 AI 判断
    if ai_available:
        for o in old_candidates:
            for n in new_candidates:
                # 调用 AI 判断
                ai_result = await _ai_judge_mapping(old_analysis, new_analysis, o, n, config)

                if ai_result:
                    scored.append(
                        MappingCandidate(
                            old=o,
                            new=n,
                            score=ai_result.get("score", 0.0),
                            confidence=ai_result.get("confidence", "low"),
                            reason=ai_result.get("reason", ""),
                        )
                    )
    else:
        # 回退到简单的字符串匹配
        from .latex_utils import jaccard, normalize_filename, tokenize

        for o in old_candidates:
            for n in new_candidates:
                old_stem = normalize_filename(Path(o).stem)
                new_stem = normalize_filename(Path(n).stem)

                # 简单的文件名匹配
                if old_stem == new_stem:
                    scored.append(
                        MappingCandidate(
                            old=o,
                            new=n,
                            score=1.0,
                            confidence="high",
                            reason=f"文件名完全匹配: {old_stem}",
                        )
                    )
                elif old_stem in new_stem or new_stem in old_stem:
                    scored.append(
                        MappingCandidate(
                            old=o,
                            new=n,
                            score=0.8,
                            confidence="medium",
                            reason=f"文件名包含关系: {old_stem} <-> {new_stem}",
                        )
                    )
                else:
                    # Jaccard 相似度
                    tokens_old = tokenize(old_stem)
                    tokens_new = tokenize(new_stem)
                    if tokens_old and tokens_new:
                        score = jaccard(tokens_old, tokens_new)
                        if score >= thresholds.low:
                            scored.append(
                                MappingCandidate(
                                    old=o,
                                    new=n,
                                    score=score,
                                    confidence="medium" if score >= thresholds.medium else "low",
                                    reason=f"文件名相似度: {score:.2f}",
                                )
                            )

    # 按分数排序
    scored.sort(key=lambda x: x.score, reverse=True)

    # 构建一对一映射（贪心算法：每个文件只映射一次）
    used_old = set()
    used_new = set()
    one_to_one: List[OneToOne] = []
    low_confidence: List[Dict[str, str]] = []

    for cand in scored:
        if cand.old in used_old or cand.new in used_new:
            continue
        if cand.score < thresholds.low:
            continue

        used_old.add(cand.old)
        used_new.add(cand.new)

        if cand.confidence == "low":
            low_confidence.append(
                {
                    "old": cand.old,
                    "new": cand.new,
                    "score": f"{cand.score:.3f}",
                    "reason": cand.reason,
                    "action": "needs_review",
                }
            )
        else:
            one_to_one.append(
                OneToOne(
                    old=cand.old,
                    new=cand.new,
                    score=round(cand.score, 3),
                    confidence=cand.confidence,
                    reason=cand.reason,
                )
            )

    removed = [{"file": o, "reason": "未找到可靠映射"} for o in old_candidates if o not in used_old]
    new_added = [{"file": n, "reason": "新模板存在但未映射"} for n in new_candidates if n not in used_new]

    return StructureDiff(
        one_to_one=one_to_one,
        new_added=new_added,
        removed=removed,
        low_confidence=low_confidence,
    )


def compute_structure_diff(old_analysis: ProjectAnalysis, new_analysis: ProjectAnalysis, config: Dict) -> StructureDiff:
    """
    结构差异分析（同步版本，兼容旧代码）

    注意：这是同步版本，实际上不会调用 AI。
    如果需要 AI 功能，请使用 compute_structure_diff_async
    """
    import asyncio

    # 创建事件循环（如果不存在）
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    # 运行异步版本（AI 不可用，使用回退策略）
    return loop.run_until_complete(compute_structure_diff_async(old_analysis, new_analysis, config, ai_available=False))
