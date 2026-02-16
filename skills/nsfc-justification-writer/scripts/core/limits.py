#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

from typing import Any, Mapping, Tuple

from .config_access import get_int, get_mapping


def _limits_cfg(cfg: Mapping[str, Any]) -> Mapping[str, Any]:
    return get_mapping(cfg, "limits")


def max_file_size_mb(cfg: Mapping[str, Any], *, default: int = 5) -> int:
    n = get_int(_limits_cfg(cfg), "max_file_size_mb", default)
    return max(1, n)


def max_file_bytes(cfg: Mapping[str, Any], *, default_mb: int = 5) -> int:
    return max_file_size_mb(cfg, default=default_mb) * 1024 * 1024


def ai_max_input_chars(cfg: Mapping[str, Any], *, default: int = 20000) -> int:
    limits_cfg = _limits_cfg(cfg)
    if "ai_max_input_chars" in limits_cfg:
        n = get_int(limits_cfg, "ai_max_input_chars", default)
        return max(1000, n)

    terminology_ai = get_mapping(get_mapping(cfg, "terminology"), "ai")
    if "max_chars" in terminology_ai:
        n = get_int(terminology_ai, "max_chars", default)
        return max(1000, n)

    return max(1000, int(default))


def writing_coach_preview_chars(cfg: Mapping[str, Any], *, default: int = 3000) -> int:
    n = get_int(_limits_cfg(cfg), "writing_coach_preview_chars", default)
    return max(300, n)


def word_target_range(cfg: Mapping[str, Any], *, default_min: int = 100, default_max: int = 20000) -> Tuple[int, int]:
    wt = get_mapping(_limits_cfg(cfg), "word_target")
    lo = get_int(wt, "min", default_min)
    hi = get_int(wt, "max", default_max)
    lo = max(0, lo)
    hi = max(lo, hi)
    return lo, hi

