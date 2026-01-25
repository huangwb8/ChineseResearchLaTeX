#!/usr/bin/env python3
"""
exponential_backoff_retry.py - 指数退避重试

用途：
  - 避免“立即重试风暴”放大故障与限流
  - 为短暂网络抖动/偶发 5xx 提供更稳健的恢复能力
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Callable, Optional, TypeVar

T = TypeVar("T")


@dataclass
class RetryConfig:
    enabled: bool = True
    max_retries: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    backoff_factor: float = 2.0


class ExponentialBackoffRetry:
    def __init__(self, cfg: Optional[dict] = None):
        cfg = cfg or {}
        self.config = RetryConfig(
            enabled=bool(cfg.get("enabled", True)),
            max_retries=int(cfg.get("max_retries", 3)),
            base_delay=float(cfg.get("base_delay", 1.0)),
            max_delay=float(cfg.get("max_delay", 60.0)),
            backoff_factor=float(cfg.get("backoff_factor", 2.0)),
        )

    def call(self, func: Callable[..., T], *args: Any, **kwargs: Any) -> T:
        if not self.config.enabled:
            return func(*args, **kwargs)

        last_exc: Optional[BaseException] = None
        for attempt in range(self.config.max_retries + 1):
            try:
                return func(*args, **kwargs)
            except BaseException as e:
                last_exc = e
                if attempt >= self.config.max_retries:
                    raise
                delay = min(
                    self.config.base_delay * (self.config.backoff_factor ** attempt),
                    self.config.max_delay,
                )
                time.sleep(delay)

        # 理论上不会到达这里
        assert last_exc is not None
        raise last_exc

