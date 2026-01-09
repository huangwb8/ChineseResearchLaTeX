#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List


@dataclass(frozen=True)
class StructureRule:
    expected_subsubsections: List[str]
    strict_title_match: bool
    min_subsubsection_count: int


@dataclass(frozen=True)
class QualityRule:
    high_risk_examples: List[str]
    avoid_commands: List[str]
    strict_mode: bool
    enable_ai_judgment: bool
    ai_judgment_mode: str


def load_structure_rule(config: Dict[str, Any]) -> StructureRule:
    s = config.get("structure", {}) or {}
    expected = s.get("recommended_subsubsections", None)
    if expected is None:
        expected = s.get("expected_subsubsections", []) or []
    return StructureRule(
        expected_subsubsections=[str(x) for x in expected],
        strict_title_match=bool(s.get("strict_title_match", False)),
        min_subsubsection_count=int(s.get("min_subsubsection_count", 4)),
    )


def load_quality_rule(config: Dict[str, Any]) -> QualityRule:
    q = config.get("quality", {}) or {}
    return QualityRule(
        high_risk_examples=[str(x) for x in (q.get("high_risk_examples", q.get("forbidden_phrases", [])) or [])],
        avoid_commands=[str(x) for x in (q.get("avoid_commands", []) or [])],
        strict_mode=bool(q.get("strict_mode", False)),
        enable_ai_judgment=bool(q.get("enable_ai_judgment", True)),
        ai_judgment_mode=str(q.get("ai_judgment_mode", "semantic") or "semantic"),
    )
