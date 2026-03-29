"""
Placeholder parsing utilities for complete_example.

We keep this logic hard-coded and deterministic: AI outputs placeholders, and
the code replaces them with safe LaTeX blocks.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional
import re


@dataclass(frozen=True)
class Placeholder:
    """A parsed placeholder with its span in the original text."""

    kind: str  # "resource" | "table" | "inline_math" | "display_math" | "equation" | "align"
    start: int
    end: int
    raw: str

    # Resource
    resource_id: Optional[str] = None

    # Table
    description: Optional[str] = None
    complexity: Optional[str] = None  # simple|moderate|complex

    # Formula
    formula: Optional[str] = None
    label: Optional[str] = None


_RESOURCE_RE = re.compile(r"\{\{PLACEHOLDER:(.+?)\}\}")
_TABLE_RE = re.compile(r"\{\{TABLE:(.+?)\|(simple|moderate|complex)\}\}")
_INLINE_MATH_RE = re.compile(r"\{\{INLINE_MATH:(.+?)\}\}")
_DISPLAY_MATH_RE = re.compile(r"\{\{DISPLAY_MATH:(.+?)\}\}")
_EQUATION_RE = re.compile(r"\{\{EQUATION:(.+?)\|(.+?)\}\}")
_ALIGN_RE = re.compile(r"\{\{ALIGN:(.+?)\}\}")


def iter_placeholders(text: str) -> Iterable[Placeholder]:
    """Yield placeholders in appearance order (non-overlapping, based on regex finds)."""
    patterns = [
        ("resource", _RESOURCE_RE),
        ("table", _TABLE_RE),
        ("inline_math", _INLINE_MATH_RE),
        ("display_math", _DISPLAY_MATH_RE),
        ("equation", _EQUATION_RE),
        ("align", _ALIGN_RE),
    ]

    matches = []
    for kind, rx in patterns:
        for m in rx.finditer(text):
            matches.append((m.start(), m.end(), kind, m))

    matches.sort(key=lambda x: x[0])

    for start, end, kind, m in matches:
        raw = m.group(0)
        if kind == "resource":
            yield Placeholder(kind=kind, start=start, end=end, raw=raw, resource_id=m.group(1).strip())
        elif kind == "table":
            yield Placeholder(
                kind=kind,
                start=start,
                end=end,
                raw=raw,
                description=m.group(1).strip(),
                complexity=m.group(2).strip(),
            )
        elif kind == "inline_math":
            yield Placeholder(kind=kind, start=start, end=end, raw=raw, formula=m.group(1).strip())
        elif kind == "display_math":
            yield Placeholder(kind=kind, start=start, end=end, raw=raw, formula=m.group(1).strip())
        elif kind == "equation":
            yield Placeholder(
                kind=kind,
                start=start,
                end=end,
                raw=raw,
                formula=m.group(1).strip(),
                label=m.group(2).strip(),
            )
        elif kind == "align":
            yield Placeholder(kind=kind, start=start, end=end, raw=raw, formula=m.group(1).strip())


def replace_spans(text: str, replacements: list[tuple[int, int, str]]) -> str:
    """Replace multiple spans in a single pass, from back to front."""
    out = text
    for start, end, rep in sorted(replacements, key=lambda x: x[0], reverse=True):
        out = out[:start] + rep + out[end:]
    return out

