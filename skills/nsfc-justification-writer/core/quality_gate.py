#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from .ai_integration import AIIntegration
from .boastful_expression_checker import BoastfulExpressionAI
from .hard_rules import load_quality_rule
from .latex_parser import strip_comments
from .limits import ai_max_input_chars


@dataclass(frozen=True)
class QualityGateResult:
    forbidden_phrases_hits: List[str]
    avoid_commands_hits: List[str]
    ai_issues: List[Dict[str, Any]]
    ai_summary: Dict[str, Any]
    ai_used: bool
    strict_mode: bool

    @property
    def ok(self) -> bool:
        if self.avoid_commands_hits:
            return False
        if self.strict_mode and self.forbidden_phrases_hits:
            return False
        if self.ai_used and self.ai_issues:
            return False
        return True


def check_new_body_quality(
    *,
    new_body: str,
    config: Dict[str, Any],
    ai: Optional[AIIntegration] = None,
    cache_dir: Optional[Path] = None,
    fresh: bool = False,
) -> QualityGateResult:
    rule = load_quality_rule(config)
    t = strip_comments(new_body or "")
    forbidden_hits = [p for p in rule.high_risk_examples if p and (p in t)]
    cmd_hits = [c for c in rule.avoid_commands if c and (c in t)]

    ai_issues: List[Dict[str, Any]] = []
    ai_summary: Dict[str, Any] = {}
    ai_used = False
    if rule.enable_ai_judgment and (ai is not None) and ai.is_available() and (str(rule.ai_judgment_mode).strip().lower() == "semantic"):
        try:
            obj = asyncio.run(
                BoastfulExpressionAI(ai).check(
                    tex_text=new_body,
                    max_chars=ai_max_input_chars(config),
                    cache_dir=cache_dir,
                    fresh=fresh,
                )
            )
            issues = obj.get("issues", []) if isinstance(obj, dict) else []
            if isinstance(issues, list):
                ai_issues = [it for it in issues if isinstance(it, dict)]
            ai_summary = obj.get("summary") if isinstance(obj.get("summary"), dict) else {}
            ai_used = True
        except RuntimeError:
            ai_used = False

    return QualityGateResult(
        forbidden_phrases_hits=forbidden_hits,
        avoid_commands_hits=cmd_hits,
        ai_issues=ai_issues,
        ai_summary=ai_summary,
        ai_used=ai_used,
        strict_mode=bool(rule.strict_mode),
    )
