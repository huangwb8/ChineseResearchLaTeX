"""
Safe LaTeX template renderer.

We intentionally do NOT use Python's `str.format()` because LaTeX contains many
literal `{...}` which would be interpreted as format placeholders and crash.

Supported placeholders:
- `{{key}}`   -> value
- `{{{key}}}` -> `{value}` (wrap with one pair of braces)
"""

from __future__ import annotations

from typing import Any, Dict
import re


_TRIPLE_RE = re.compile(r"\{\{\{([a-zA-Z0-9_]+)\}\}\}")
_DOUBLE_RE = re.compile(r"\{\{([a-zA-Z0-9_]+)\}\}")


def render_template(template: str, values: Dict[str, Any]) -> str:
    def triple_sub(m: re.Match) -> str:
        key = m.group(1)
        if key not in values:
            raise KeyError(key)
        return "{" + str(values[key]) + "}"

    def double_sub(m: re.Match) -> str:
        key = m.group(1)
        if key not in values:
            raise KeyError(key)
        return str(values[key])

    out = _TRIPLE_RE.sub(triple_sub, template)
    out = _DOUBLE_RE.sub(double_sub, out)
    return out

