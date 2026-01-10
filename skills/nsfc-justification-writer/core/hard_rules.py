#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, List, Mapping

from .config_access import get_bool, get_mapping, get_seq_str, get_str, get_int


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


def load_structure_rule(config: Mapping[str, Any]) -> StructureRule:
    s = get_mapping(config, "structure")
    expected = s.get("recommended_subsubsections", None)
    if expected is None:
        expected = s.get("expected_subsubsections", []) or []
    return StructureRule(
        expected_subsubsections=[str(x) for x in expected],
        strict_title_match=get_bool(s, "strict_title_match", False),
        min_subsubsection_count=get_int(s, "min_subsubsection_count", 4),
    )


def load_quality_rule(config: Mapping[str, Any]) -> QualityRule:
    q = get_mapping(config, "quality")
    high_risk = get_seq_str(q, "high_risk_examples") or get_seq_str(q, "forbidden_phrases")
    return QualityRule(
        high_risk_examples=list(high_risk),
        avoid_commands=list(get_seq_str(q, "avoid_commands")),
        strict_mode=get_bool(q, "strict_mode", False),
        enable_ai_judgment=get_bool(q, "enable_ai_judgment", True),
        ai_judgment_mode=get_str(q, "ai_judgment_mode", "semantic") or "semantic",
    )
