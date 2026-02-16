from __future__ import annotations

"""
Shared deterministic color math (WCAG contrast).

This is used by both heuristic evaluators and measurement collectors to avoid drift.
"""

from typing import Tuple


def srgb_channel_to_linear(x: float) -> float:
    if x <= 0.04045:
        return x / 12.92
    return ((x + 0.055) / 1.055) ** 2.4


def relative_luminance(rgb: Tuple[int, int, int]) -> float:
    r, g, b = rgb
    rl = srgb_channel_to_linear(r / 255.0)
    gl = srgb_channel_to_linear(g / 255.0)
    bl = srgb_channel_to_linear(b / 255.0)
    return 0.2126 * rl + 0.7152 * gl + 0.0722 * bl


def contrast_ratio(rgb1: Tuple[int, int, int], rgb2: Tuple[int, int, int]) -> float:
    l1 = relative_luminance(rgb1)
    l2 = relative_luminance(rgb2)
    hi, lo = (l1, l2) if l1 >= l2 else (l2, l1)
    return (hi + 0.05) / (lo + 0.05)

