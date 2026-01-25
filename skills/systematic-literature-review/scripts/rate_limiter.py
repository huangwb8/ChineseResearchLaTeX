#!/usr/bin/env python3
"""
rate_limiter.py - provider 配额管理 + 智能路由

本模块重点解决：
  - Semantic Scholar 零配置场景下的速率限制（默认 100/min）
  - 在多查询场景中自动把主力负载放到 OpenAlex（无官方限制）
  - 对包含 DOI 的查询优先走 Crossref 进行权威校验/补全
"""

from __future__ import annotations

import re
import time
from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, Optional, Tuple


_DOI_RE = re.compile(r"(10\\.[0-9]{4,9}/[-._;()/:A-Za-z0-9]+)", re.IGNORECASE)


def extract_doi(text: str) -> str:
    if not text:
        return ""
    # 兼容 doi.org/ 前缀
    t = re.sub(r"https?://(dx\\.)?doi\\.org/", "", text.strip(), flags=re.IGNORECASE)
    m = _DOI_RE.search(t)
    return (m.group(1) if m else "").lower()


def contains_doi(text: str) -> bool:
    return bool(extract_doi(text))


@dataclass
class ProviderLimitStatus:
    can_call: bool
    reason: Optional[str] = None


class RateLimiter:
    """API 速率限制管理器（目前主要管 Semantic Scholar）"""

    def __init__(self, cfg: Optional[dict] = None):
        cfg = cfg or {}
        self.enabled = bool(cfg.get("enabled", True))

        ss_cfg = cfg.get("semantic_scholar", {}) if isinstance(cfg.get("semantic_scholar", {}), dict) else {}
        oa_cfg = cfg.get("openalex", {}) if isinstance(cfg.get("openalex", {}), dict) else {}

        self.semantic_max_per_minute = int(ss_cfg.get("max_calls_per_minute", 80))
        self.semantic_max_per_session = int(ss_cfg.get("max_calls_per_session", 500))
        self.semantic_cooldown = int(ss_cfg.get("cooldown_on_limit", 60))
        self.semantic_fallback_to_openalex = bool(ss_cfg.get("fallback_to_openalex", True))

        self.openalex_polite_delay = float(oa_cfg.get("polite_delay", 0.25))

        self._calls = defaultdict(list)  # provider -> timestamps
        self._cooldown_until: Dict[str, float] = {}
        self._session_start = time.time()

    def can_call(self, provider: str) -> ProviderLimitStatus:
        if not self.enabled:
            return ProviderLimitStatus(True)

        provider = str(provider or "").strip()
        if provider != "semantic_scholar":
            return ProviderLimitStatus(True)

        now = time.time()
        until = self._cooldown_until.get(provider)
        if until is not None and now < until:
            remaining = max(0, int(until - now))
            return ProviderLimitStatus(False, f"速率限制冷却中，剩余 {remaining} 秒")

        recent_calls = [t for t in self._calls[provider] if now - t < 60]
        self._calls[provider] = recent_calls
        if len(recent_calls) >= self.semantic_max_per_minute:
            self._cooldown_until[provider] = now + self.semantic_cooldown
            return ProviderLimitStatus(False, f"速率限制：{len(recent_calls)}/{self.semantic_max_per_minute} 次/分钟")

        total_calls = len(self._calls[provider])
        if total_calls >= self.semantic_max_per_session:
            return ProviderLimitStatus(False, f"会话配额用尽：{total_calls}/{self.semantic_max_per_session}")

        return ProviderLimitStatus(True)

    def record_call(self, provider: str) -> None:
        if not self.enabled:
            return
        self._calls[str(provider)].append(time.time())

    def recommended_provider(self, providers: list[str], query: str = "") -> str:
        """
        根据查询类型 + 速率限制推荐 provider。

        规则（尽量符合计划中的“主力/补充”定位）：
          - DOI 查询：优先 Crossref（若在候选列表中）
          - 短查询（<=5词）：优先 OpenAlex
          - 长查询（>5词）：优先 Semantic Scholar（若配额允许）
          - 其他：按优先级回退到 OpenAlex
        """
        providers = [p for p in providers if p]
        if not providers:
            return "openalex"

        q = (query or "").strip()
        if q and contains_doi(q) and "crossref" in providers:
            return "crossref"

        # 主力默认走 OpenAlex（无官方速率限制）；Semantic Scholar 主要用于“补充/增强”
        if "openalex" in providers:
            return "openalex"

        words = [w for w in q.split() if w]
        if len(words) > 5 and "semantic_scholar" in providers:
            st = self.can_call("semantic_scholar")
            if st.can_call:
                return "semantic_scholar"

        return providers[0]

    def summary(self) -> Dict[str, Dict[str, float]]:
        now = time.time()
        out: Dict[str, Dict[str, float]] = {}
        for provider, timestamps in self._calls.items():
            recent_calls = len([t for t in timestamps if now - t < 60])
            out[provider] = {
                "calls_last_minute": float(recent_calls),
                "total_calls": float(len(timestamps)),
                "session_duration_seconds": float(now - self._session_start),
            }
        return out
