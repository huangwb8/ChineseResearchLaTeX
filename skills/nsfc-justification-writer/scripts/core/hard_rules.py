#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, List, Mapping

from .config_access import get_bool, get_mapping, get_seq_str, get_int


@dataclass(frozen=True)
class StructureRule:
    expected_subsubsections: List[str]
    strict_title_match: bool
    min_subsubsection_count: int


@dataclass(frozen=True)
class QualityRule:
    avoid_commands: List[str]


def load_structure_rule(config: Mapping[str, Any]) -> StructureRule:
    s = get_mapping(config, "structure")
    expected = s.get("recommended_subsubsections", None)
    if expected is None:
        expected = s.get("expected_subsubsections", []) or []
    return StructureRule(
        expected_subsubsections=[str(x) for x in expected],
        strict_title_match=get_bool(s, "strict_title_match", False),
        # 没有结构配置时不把文档判为空。
        min_subsubsection_count=get_int(s, "min_subsubsection_count", 0),
    )


def load_quality_rule(config: Mapping[str, Any]) -> QualityRule:
    q = get_mapping(config, "quality")
    return QualityRule(
        avoid_commands=list(get_seq_str(q, "avoid_commands")),
    )
