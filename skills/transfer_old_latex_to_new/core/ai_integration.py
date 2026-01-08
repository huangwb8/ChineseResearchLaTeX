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
    - 支持批量调用优化（v1.3.0）
    """

    def __init__(
        self,
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
        self.batch_count = 0  # 批量调用计数

        # 批量配置
        ai_cfg = (config.get("ai", {}) or {}) if isinstance(config, dict) else {}
        self.batch_mode = bool(ai_cfg.get("batch_mode", False))
        self.batch_size = int(ai_cfg.get("batch_size", 10))

    def is_available(self) -> bool:
        return bool(self.enable_ai and (not self.fallback_mode) and (self.responder is not None))

    def get_stats(self) -> Dict[str, Any]:
        return {
            "enabled": self.enable_ai,
            "fallback_mode": self.fallback_mode,
            "request_count": self.request_count,
            "success_count": self.success_count,
            "batch_count": self.batch_count,
            "success_rate": self.success_count / max(self.request_count, 1),
            "batch_mode_enabled": self.batch_mode,
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

    async def process_batch_requests(
        self,
        *,
        task: str,
        prompts: List[str],
        fallback: Callable[[], List[Any]],
        output_format: str = "json",
    ) -> List[Any]:
        """
        批量处理 AI 请求（优化网络开销）

        Args:
            task: 任务名称
            prompts: 提示词列表
            fallback: 回退函数
            output_format: 输出格式

        Returns:
            结果列表
        """
        self.batch_count += 1
        self.request_count += len(prompts)

        if not self.enable_ai or self.responder is None:
            self.fallback_mode = True
            self._log_fallback(task, reason="AI disabled or No responder")
            return fallback()

        try:
            # 构建批量提示词
            batch_prompt = self._build_batch_prompt(prompts, output_format)

            # 调用 AI
            raw = self.responder(task, batch_prompt, output_format)
            if hasattr(raw, "__await__"):
                raw = await raw  # type: ignore[misc]

            if raw is None:
                raise ValueError("Empty AI response")

            # 解析批量结果
            if output_format == "json":
                results = self._parse_batch_json_response(raw)
                self.success_count += len(results)
                return results
            elif output_format == "text":
                # 文本模式下，按行分割返回
                text = str(raw).strip()
                results = [line.strip() for line in text.split("\n") if line.strip()]
                self.success_count += len(results)
                return results
            else:
                raise ValueError(f"Unsupported output_format: {output_format}")

        except Exception as e:
            self.fallback_mode = True
            self._log_fallback(task, reason=str(e))
            return fallback()

    def _build_batch_prompt(self, prompts: List[str], output_format: str) -> str:
        """构建批量提示词"""
        batch_prompt = "请批量处理以下请求，返回 JSON 数组：\n\n"
        for i, prompt in enumerate(prompts, 1):
            batch_prompt += f"\n## 请求 {i}\n{prompt}\n"

        if output_format == "json":
            batch_prompt += "\n## 输出格式\n"
            batch_prompt += "请返回 JSON 数组，每个元素对应一个请求的结果：\n"
            batch_prompt += "```json\n[结果1, 结果2, ...]\n```\n"

        return batch_prompt

    def _parse_batch_json_response(self, response: Any) -> List[Any]:
        """解析批量 JSON 响应"""
        response_text = str(response)

        # 尝试提取 JSON 数组
        try:
            # 1) 提取 fenced code block 中的 JSON
            if "```json" in response_text:
                start = response_text.find("```json") + 7
                end = response_text.find("```", start)
                if end != -1:
                    json_str = response_text[start:end].strip()
                    data = json.loads(json_str)
                    if isinstance(data, list):
                        return data
            elif "```" in response_text:
                # 尝试无语言标记的代码块
                start = response_text.find("```") + 3
                end = response_text.find("```", start)
                if end != -1:
                    json_str = response_text[start:end].strip()
                    data = json.loads(json_str)
                    if isinstance(data, list):
                        return data

            # 2) 直接解析整个响应
            data = json.loads(response_text)
            if isinstance(data, list):
                return data

        except (json.JSONDecodeError, ValueError):
            pass

        # 3) 尝试提取多个 JSON 对象
        results = []
        for match in response_text.split("{"):
            if not match.strip():
                continue
            try:
                obj = json.loads("{" + match.split("}")[0] + "}")
                results.append(obj)
            except (json.JSONDecodeError, ValueError, IndexError):
                continue

        return results if len(results) > 1 else []
