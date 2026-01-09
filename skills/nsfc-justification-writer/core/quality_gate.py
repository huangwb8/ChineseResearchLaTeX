#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List

from .hard_rules import load_quality_rule
from .latex_parser import strip_comments


@dataclass(frozen=True)
class QualityGateResult:
    forbidden_phrases_hits: List[str]
    avoid_commands_hits: List[str]

    @property
    def ok(self) -> bool:
        return (not self.forbidden_phrases_hits) and (not self.avoid_commands_hits)


def check_new_body_quality(*, new_body: str, config: Dict[str, Any]) -> QualityGateResult:
    rule = load_quality_rule(config)
    t = strip_comments(new_body or "")
    forbidden_hits = [p for p in rule.forbidden_phrases if p and (p in t)]
    cmd_hits = [c for c in rule.avoid_commands if c and (c in t)]
    return QualityGateResult(forbidden_phrases_hits=forbidden_hits, avoid_commands_hits=cmd_hits)

