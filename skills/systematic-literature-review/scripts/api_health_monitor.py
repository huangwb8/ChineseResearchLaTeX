#!/usr/bin/env python3
"""
api_health_monitor.py - API 健康监控与黑名单

用途：
  - 记录某个 provider 的近期失败情况
  - 失败达到阈值后将 provider 临时加入黑名单，避免反复浪费请求与重试
  - 黑名单到期后允许恢复尝试
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Dict, Optional


@dataclass
class HealthConfig:
    enabled: bool = True
    failure_threshold: int = 5
    failure_window: int = 60
    recovery_check_interval: int = 300


class APIHealthMonitor:
    def __init__(self, cfg: Optional[dict] = None):
        cfg = cfg or {}
        self.config = HealthConfig(
            enabled=bool(cfg.get("enabled", True)),
            failure_threshold=int(cfg.get("failure_threshold", 5)),
            failure_window=int(cfg.get("failure_window", 60)),
            recovery_check_interval=int(cfg.get("recovery_check_interval", 300)),
        )

        self._failures: Dict[str, list[float]] = {}
        self._blacklist_until: Dict[str, float] = {}

    def record_failure(self, provider: str) -> None:
        if not self.config.enabled:
            return
        now = time.time()
        bucket = self._failures.setdefault(provider, [])
        bucket.append(now)
        # 清理窗口外失败
        self._failures[provider] = [t for t in bucket if now - t <= self.config.failure_window]

        if len(self._failures[provider]) >= self.config.failure_threshold:
            self._blacklist_until[provider] = now + self.config.recovery_check_interval

    def record_success(self, provider: str) -> None:
        if not self.config.enabled:
            return
        self._failures.pop(provider, None)
        # 成功不强制解禁：由 is_available 的到期判断控制

    def is_available(self, provider: str) -> bool:
        if not self.config.enabled:
            return True
        until = self._blacklist_until.get(provider)
        if until is None:
            return True
        if time.time() >= until:
            # 到期后允许恢复尝试
            self._blacklist_until.pop(provider, None)
            self._failures.pop(provider, None)
            return True
        return False

    def blacklist_remaining(self, provider: str) -> int:
        until = self._blacklist_until.get(provider)
        if until is None:
            return 0
        return max(0, int(until - time.time()))

