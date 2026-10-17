#!/usr/bin/env python3
"""读取配置中的字数目标，供诊断和字数统计共用。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict

from .config_access import get_int, get_mapping
from .limits import word_target_range


@dataclass(frozen=True)
class WordTargetSpec:
    target: int
    tolerance: int
    source: str = "config"
    evidence: str = ""


def _clamp(value: int, low: int, high: int) -> int:
    return max(low, min(high, int(value)))


def resolve_word_target(*, config: Dict[str, Any]) -> WordTargetSpec:
    """返回配置中的字数目标；用户补充的篇幅要求由宿主 AI 处理。"""
    word_count = get_mapping(config, "word_count")
    low, high = word_target_range(config)
    target = _clamp(get_int(word_count, "target", 4000), low, high)
    tolerance = max(0, get_int(word_count, "tolerance", 200))
    return WordTargetSpec(target=target, tolerance=tolerance)
