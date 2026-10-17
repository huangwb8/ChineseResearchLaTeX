#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

from typing import Mapping, Tuple

from .config_access import get_int, get_mapping


def _limits_cfg(cfg: Mapping[str, Any]) -> Mapping[str, Any]:
    return get_mapping(cfg, "limits")


def word_target_range(cfg: Mapping[str, Any], *, default_min: int = 100, default_max: int = 20000) -> Tuple[int, int]:
    wt = get_mapping(_limits_cfg(cfg), "word_target")
    lo = get_int(wt, "min", default_min)
    hi = get_int(wt, "max", default_max)
    lo = max(0, lo)
    hi = max(lo, hi)
    return lo, hi
