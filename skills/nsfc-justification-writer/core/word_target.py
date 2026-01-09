#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple


@dataclass(frozen=True)
class WordTargetSpec:
    target: int
    tolerance: int
    source: str
    evidence: str = ""


_RANGE_RE = re.compile(r"(?P<a>\d{3,5})\s*[-~—–]\s*(?P<b>\d{3,5})\s*(?:字|字符)")
_SINGLE_RE = re.compile(r"(?P<n>\d{3,5})\s*(?:字|字符)")
_PLUS_MINUS_RE = re.compile(r"(?P<n>\d{3,5})\s*(?:字|字符)?\s*(?:±|\+/-)\s*(?P<tol>\d{1,4})")


def _clamp_int(n: int, *, lo: int, hi: int) -> int:
    return max(lo, min(hi, int(n)))


def parse_word_target_from_text(text: str) -> Optional[Tuple[int, int, str]]:
    """
    从自然语言中解析“目标字数/字符数”和容差。

    支持：
    - 区间：2500-3000 字
    - ±：3000±200 字 / 3000 +/- 200
    - 单值：约 3000 字 / 3000 字左右（默认容差 200）
    """
    t = (text or "").strip()
    if not t:
        return None

    m = _PLUS_MINUS_RE.search(t)
    if m:
        target = int(m.group("n"))
        tol = int(m.group("tol"))
        target = _clamp_int(target, lo=100, hi=20000)
        tol = _clamp_int(tol, lo=0, hi=5000)
        return target, tol, m.group(0)

    m = _RANGE_RE.search(t)
    if m:
        a = int(m.group("a"))
        b = int(m.group("b"))
        lo, hi = (a, b) if a <= b else (b, a)
        target = int(round((lo + hi) / 2))
        tol = int(max(50, round(abs(hi - lo) / 2)))
        target = _clamp_int(target, lo=100, hi=20000)
        tol = _clamp_int(tol, lo=0, hi=5000)
        return target, tol, m.group(0)

    m = _SINGLE_RE.search(t)
    if m:
        target = _clamp_int(int(m.group("n")), lo=100, hi=20000)
        tol = 200
        return target, tol, m.group(0)

    return None


def resolve_word_target(
    *,
    config: Dict[str, Any],
    user_intent_text: str = "",
    info_form_text: str = "",
) -> WordTargetSpec:
    """
    解析优先级（用户意图优先）：
    - P0：user_intent_text（通常是用户指令/Prompt）
    - P1：info_form_text（信息表中的“字数限制”）
    - P2：config.active_preset（若存在，视作“学科预设”来源之一）
    - P3：config.word_count.*（兜底）
    """
    parsed = parse_word_target_from_text(user_intent_text)
    if parsed:
        target, tol, ev = parsed
        return WordTargetSpec(target=target, tolerance=tol, source="user_intent", evidence=ev)

    parsed = parse_word_target_from_text(info_form_text)
    if parsed:
        target, tol, ev = parsed
        return WordTargetSpec(target=target, tolerance=tol, source="info_form", evidence=ev)

    wc_cfg = config.get("word_count", {}) or {}
    target = int(wc_cfg.get("target", 4000))
    tol = int(wc_cfg.get("tolerance", 200))

    preset = str(config.get("active_preset", "") or "").strip()
    if preset:
        return WordTargetSpec(target=target, tolerance=tol, source=f"preset:{preset}", evidence="")

    return WordTargetSpec(target=target, tolerance=tol, source="config_default", evidence="")

