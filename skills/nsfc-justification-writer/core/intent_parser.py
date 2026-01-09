#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

from .ai_integration import AIIntegration
from .prompt_templates import INTENT_PARSE_PROMPT


@dataclass(frozen=True)
class ParsedIntent:
    action: Optional[str]
    target: Optional[str]
    focus: Optional[str]
    constraints: Optional[str]
    reason: Optional[str] = None


async def parse_intent(
    *,
    instruction: str,
    ai: AIIntegration,
) -> ParsedIntent:
    prompt = INTENT_PARSE_PROMPT.format(instruction=instruction.strip())

    def _fallback() -> Dict[str, Any]:
        return {"action": None, "target": None, "focus": None, "constraints": None, "reason": "ai_unavailable"}

    obj = await ai.process_request(task="intent_parse", prompt=prompt, fallback=_fallback, output_format="json")
    if not isinstance(obj, dict):
        obj = _fallback()

    return ParsedIntent(
        action=obj.get("action"),
        target=obj.get("target"),
        focus=obj.get("focus"),
        constraints=obj.get("constraints"),
        reason=obj.get("reason"),
    )

