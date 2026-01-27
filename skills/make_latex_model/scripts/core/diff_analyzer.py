#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
差异分析器（DiffAnalyzer）

从像素对比产出的结构化特征（diff_features.json）中推断：
- 根因类别（换行/边距/垂直偏移/标题区差异等）
- 受影响区域
- 候选参数（及相关性）

本模块不依赖外部 AI，可作为 DecisionReasoner 的输入。
"""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class DiffContext:
    diff_ratio: float
    iteration: int
    root_cause: str
    affected_regions: List[str]
    confidence: float
    evidence: Dict[str, Any]
    parameter_candidates: List[Dict[str, Any]]


class DiffAnalyzer:
    """基于像素对比特征的差异分析器"""

    ROOT_CAUSES = (
        "line_break_mismatch",
        "vertical_offset",
        "margin_mismatch",
        "heading_area_mismatch",
        "unknown",
    )

    def analyze(
        self,
        diff_ratio: float,
        iteration: int,
        features_path: Optional[Path] = None,
        features: Optional[Dict[str, Any]] = None,
    ) -> DiffContext:
        if features is None and features_path and features_path.exists():
            try:
                features = json.loads(features_path.read_text(encoding="utf-8"))
            except Exception:
                features = None

        evidence: Dict[str, Any] = {}
        affected_regions: List[str] = []

        # 默认：只能用 diff_ratio 粗判
        if not features:
            root_cause = "unknown"
            confidence = 0.3
            candidates = self._candidates_from_root_cause(root_cause)
            return DiffContext(
                diff_ratio=diff_ratio,
                iteration=iteration,
                root_cause=root_cause,
                affected_regions=affected_regions,
                confidence=confidence,
                evidence=evidence,
                parameter_candidates=candidates,
            )

        pages = features.get("pages", [])
        if not pages:
            root_cause = "unknown"
            confidence = 0.3
            candidates = self._candidates_from_root_cause(root_cause)
            return DiffContext(
                diff_ratio=diff_ratio,
                iteration=iteration,
                root_cause=root_cause,
                affected_regions=affected_regions,
                confidence=confidence,
                evidence={"features": features},
                parameter_candidates=candidates,
            )

        # 新增：paragraph mode（逐段对齐特征）
        if str(features.get("mode") or "").lower() == "paragraph":
            p0 = pages[0]
            pv = float(p0.get("paragraph_position_variance", 0.0))
            sv = float(p0.get("paragraph_spacing_variance", 0.0))
            iv = float(p0.get("avg_internal_line_variance", 0.0))
            indent_v = float(p0.get("indent_variance", 0.0))
            match_count = int(p0.get("match_count", 0) or 0)

            evidence.update(
                {
                    "mode": "paragraph",
                    "page_1": {
                        "match_count": match_count,
                        "paragraph_position_variance": pv,
                        "paragraph_spacing_variance": sv,
                        "avg_internal_line_variance": iv,
                        "indent_variance": indent_v,
                    },
                }
            )

            # 启发式阈值：所有方差单位均为 pt^2，取偏保守阈值（避免误报）
            root_cause = "unknown"
            confidence = 0.45

            # 缩进/边距不一致
            if indent_v >= 1.0 and diff_ratio >= 0.01:
                root_cause = "margin_mismatch"
                confidence = 0.75
            # 段间距/垂直漂移（段落之间的 gap 差异波动更强）
            elif (sv >= 4.0 or pv >= 4.0) and diff_ratio >= 0.01:
                root_cause = "vertical_offset"
                confidence = 0.70
            # 段内行距/换行不一致
            elif iv >= 0.5 and diff_ratio >= 0.01:
                root_cause = "line_break_mismatch"
                confidence = 0.65

            candidates = self._candidates_from_root_cause(root_cause, affected_regions=affected_regions)
            return DiffContext(
                diff_ratio=diff_ratio,
                iteration=iteration,
                root_cause=root_cause,
                affected_regions=affected_regions,
                confidence=confidence,
                evidence=evidence,
                parameter_candidates=candidates,
            )

        # 以第一页为主（NSFC 正文模板通常第一页最敏感：标题/版心/首段）
        p0 = pages[0]
        region = p0.get("region_ratios", {})
        row_var = float(p0.get("row_variance", 0.0))
        col_var = float(p0.get("col_variance", 0.0))

        evidence.update(
            {
                "page_1": {
                    "region_ratios": region,
                    "row_variance": row_var,
                    "col_variance": col_var,
                }
            }
        )

        top = float(region.get("top", 0.0))
        middle = float(region.get("middle", 0.0))
        bottom = float(region.get("bottom", 0.0))

        # 受影响区域
        region_items = [("top", top), ("middle", middle), ("bottom", bottom)]
        for name, ratio in sorted(region_items, key=lambda x: x[1], reverse=True):
            if ratio > 0.02:  # 经验阈值：单区差异超过 2%
                affected_regions.append(name)

        # 根因分类（启发式）
        root_cause = "unknown"
        confidence = 0.4

        # 强水平条纹：多为换行/行距导致的行位差异
        if row_var > col_var * 2.0 and diff_ratio >= 0.01:
            root_cause = "line_break_mismatch"
            confidence = 0.75
        # 强垂直条纹：多为边距/缩进导致的横向错位
        elif col_var > row_var * 2.0 and diff_ratio >= 0.01:
            root_cause = "margin_mismatch"
            confidence = 0.75
        # 顶部差异显著：可能标题区/提纲提示语对齐问题
        elif top > (middle + bottom) and top > 0.03:
            root_cause = "heading_area_mismatch"
            confidence = 0.65
        # 中部/底部均匀：更像行距/段距累积偏移
        elif (middle + bottom) > top and diff_ratio >= 0.01:
            root_cause = "vertical_offset"
            confidence = 0.6

        if root_cause not in self.ROOT_CAUSES:
            root_cause = "unknown"

        candidates = self._candidates_from_root_cause(root_cause, affected_regions=affected_regions)
        return DiffContext(
            diff_ratio=diff_ratio,
            iteration=iteration,
            root_cause=root_cause,
            affected_regions=affected_regions,
            confidence=confidence,
            evidence=evidence,
            parameter_candidates=candidates,
        )

    def _candidates_from_root_cause(
        self, root_cause: str, affected_regions: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        affected_regions = affected_regions or []

        # 统一用“参数名 + relevance”结构，避免提前绑定到具体 LaTeX 实现细节
        if root_cause == "line_break_mismatch":
            candidates = [
                {"name": "xiaosi_font_size", "relevance": 0.90},
                {"name": "char_spacing", "relevance": 0.55},
                {"name": "margin_right", "relevance": 0.45},
                {"name": "margin_left", "relevance": 0.30},
            ]
        elif root_cause == "vertical_offset":
            candidates = [
                {"name": "baselinestretch", "relevance": 0.80},
                {"name": "parskip", "relevance": 0.55},
                {"name": "margin_top", "relevance": 0.45},
                {"name": "margin_bottom", "relevance": 0.35},
            ]
        elif root_cause == "margin_mismatch":
            candidates = [
                {"name": "margin_left", "relevance": 0.80},
                {"name": "margin_right", "relevance": 0.80},
                {"name": "title_indent", "relevance": 0.45},
                {"name": "list_leftmargin", "relevance": 0.35},
            ]
        elif root_cause == "heading_area_mismatch":
            candidates = [
                {"name": "title_indent", "relevance": 0.80},
                {"name": "xiaosi_font_size", "relevance": 0.50},
                {"name": "baselinestretch", "relevance": 0.35},
                {"name": "caption_skip", "relevance": 0.25},
            ]
        else:
            candidates = [
                {"name": "xiaosi_font_size", "relevance": 0.40},
                {"name": "baselinestretch", "relevance": 0.40},
                {"name": "margin_right", "relevance": 0.30},
                {"name": "margin_left", "relevance": 0.30},
            ]

        # 小幅提升“标题相关参数”在 top 受影响时的权重
        if "top" in affected_regions:
            for item in candidates:
                if item["name"] in ("title_indent", "caption_skip"):
                    item["relevance"] = min(1.0, float(item["relevance"]) + 0.1)

        return sorted(candidates, key=lambda x: float(x.get("relevance", 0)), reverse=True)
