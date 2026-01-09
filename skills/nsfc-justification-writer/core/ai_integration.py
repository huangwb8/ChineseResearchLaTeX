#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import json
import logging
from typing import Any, Awaitable, Callable, Dict, List, Optional, Union

JsonDict = Dict[str, Any]
Responder = Callable[[str, str, str], Union[str, JsonDict, None, Awaitable[Union[str, JsonDict, None]]]]


class AIIntegration:
    """
    AI 集成层（优雅降级）

    说明：
    - 本仓库内的 Python 脚本默认不假设"可直接调用宿主 AI"。
    - 若未提供 responder（或 enable_ai=False），将自动回退到 fallback。
    - 该接口为后续真正的 AI 调用预留扩展点，同时保证当前功能可用。
    """

    def __init__(
        self,
        *,
        enable_ai: bool = True,
        config: Optional[Dict[str, Any]] = None,
        responder: Optional[Responder] = None,
    ) -> None:
        self.enable_ai = bool(enable_ai)
        self.config = config or {}
        self.responder = responder

        self.fallback_mode = False
        self.request_count = 0
        self.success_count = 0

    def is_available(self) -> bool:
        return bool(self.enable_ai and (not self.fallback_mode) and (self.responder is not None))

    def get_stats(self) -> Dict[str, Any]:
        return {
            "enabled": self.enable_ai,
            "fallback_mode": self.fallback_mode,
            "request_count": self.request_count,
            "success_count": self.success_count,
            "success_rate": self.success_count / max(self.request_count, 1),
        }

    async def process_request(
        self,
        *,
        task: str,
        prompt: str,
        fallback: Callable[[], Any],
        output_format: str = "json",
    ) -> Any:
        self.request_count += 1

        if not self.enable_ai:
            self.fallback_mode = True
            self._log_fallback(task, reason="AI disabled")
            return fallback()

        if self.responder is None:
            self.fallback_mode = True
            self._log_fallback(task, reason="No responder configured")
            return fallback()

        try:
            raw = self.responder(task, prompt, output_format)
            if hasattr(raw, "__await__"):
                raw = await raw  # type: ignore[misc]

            if raw is None:
                raise ValueError("Empty AI response")

            if output_format == "json":
                if isinstance(raw, dict):
                    self.success_count += 1
                    return raw
                parsed = self._parse_json_response(str(raw))
                if parsed is None:
                    raise ValueError("Failed to parse JSON response")
                self.success_count += 1
                return parsed

            if output_format == "text":
                self.success_count += 1
                return str(raw).strip()

            raise ValueError(f"Unsupported output_format: {output_format}")
        except Exception as e:
            self.fallback_mode = True
            self._log_fallback(task, reason=str(e))
            return fallback()

    @staticmethod
    def _parse_json_response(response_text: str) -> Optional[JsonDict]:
        # 1) fenced code block
        if "```json" in response_text:
            start = response_text.find("```json") + 7
            end = response_text.find("```", start)
            if end != -1:
                candidate = response_text[start:end].strip()
                try:
                    obj = json.loads(candidate)
                    return obj if isinstance(obj, dict) else None
                except Exception:
                    return None

        # 2) first balanced {...}
        start = response_text.find("{")
        if start == -1:
            return None

        depth = 0
        for i in range(start, len(response_text)):
            ch = response_text[i]
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    candidate = response_text[start : i + 1]
                    try:
                        obj = json.loads(candidate)
                        return obj if isinstance(obj, dict) else None
                    except Exception:
                        return None

        return None

    @staticmethod
    def _log_fallback(task: str, reason: str) -> None:
        logger = logging.getLogger(__name__)
        if reason in {"AI disabled", "No responder configured"}:
            logger.info("[AIIntegration] fallback task=%s reason=%s", task, reason)
        else:
            logger.warning("[AIIntegration] fallback task=%s reason=%s", task, reason)

