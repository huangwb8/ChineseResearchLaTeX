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
    forbidden_phrases: List[str]
    avoid_commands: List[str]


def load_structure_rule(config: Dict[str, Any]) -> StructureRule:
    s = config.get("structure", {}) or {}
    expected = s.get("expected_subsubsections", []) or []
    return StructureRule(
        expected_subsubsections=[str(x) for x in expected],
        strict_title_match=bool(s.get("strict_title_match", True)),
        min_subsubsection_count=int(s.get("min_subsubsection_count", 4)),
    )


def load_quality_rule(config: Dict[str, Any]) -> QualityRule:
    q = config.get("quality", {}) or {}
    return QualityRule(
        forbidden_phrases=[str(x) for x in (q.get("forbidden_phrases", []) or [])],
        avoid_commands=[str(x) for x in (q.get("avoid_commands", []) or [])],
    )

