#!/usr/bin/env python3
"""
global_rate_limiter.py - 全局速率限制（跨所有 API 的总请求量保护）

设计目标：
  - 防止并发/循环请求导致整体请求量失控，从而触发 API 防护或封禁
  - 提供“冷却期”机制：达到阈值后短暂暂停，再继续执行

说明：
  - 该 limiter 以“单次 HTTP 请求”为粒度更合理；但在本技能中也可用于更粗粒度的调用保护。
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Optional, Tuple


@dataclass
class GlobalLimitStatus:
    can_request: bool
    reason: Optional[str] = None
    cooldown_seconds: int = 0


class GlobalRateLimiter:
    """全局速率限制器（跨 provider 汇总统计）"""

    def __init__(self, *, max_per_minute: int = 120, cooldown_on_limit: int = 30):
        self.max_per_minute = int(max_per_minute)
        self.cooldown_on_limit = int(cooldown_on_limit)

        self._all_calls: list[float] = []
        self._in_cooldown = False
        self._cooldown_until = 0.0

    def can_request(self) -> GlobalLimitStatus:
        now = time.time()

        if self._in_cooldown:
            if now < self._cooldown_until:
                remaining = max(0, int(self._cooldown_until - now))
                return GlobalLimitStatus(
                    can_request=False,
                    reason=f"全局冷却中，剩余 {remaining} 秒",
                    cooldown_seconds=remaining,
                )
            self._in_cooldown = False

        recent_calls = [t for t in self._all_calls if now - t < 60]
        # 只保留最近一分钟窗口，避免列表无限增长
        self._all_calls = recent_calls

        if len(recent_calls) >= self.max_per_minute:
            self._in_cooldown = True
            self._cooldown_until = now + self.cooldown_on_limit
            return GlobalLimitStatus(
                can_request=False,
                reason=f"全局速率限制：{len(recent_calls)}/{self.max_per_minute} 次/分钟",
                cooldown_seconds=self.cooldown_on_limit,
            )

        return GlobalLimitStatus(can_request=True)

    def record_request(self) -> None:
        self._all_calls.append(time.time())

