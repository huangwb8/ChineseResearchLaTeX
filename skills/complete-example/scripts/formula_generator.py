"""
FormulaGenerator - render LaTeX math blocks from formula placeholders.

We intentionally keep this deterministic: the placeholder already contains the
formula (or formulas). The generator only wraps it with the configured LaTeX
templates and performs basic label sanitization.
"""

from __future__ import annotations

from typing import Dict, Any
import re


def _sanitize_label(label: str) -> str:
    label = (label or "").strip()
    if not label:
        return "eq:formula"
    # Keep common LaTeX label characters.
    label = re.sub(r"[^a-zA-Z0-9:_-]+", "-", label)
    return label[:64]


class FormulaGenerator:
    def __init__(self, templates: Dict[str, str]):
        self.templates = templates

    def inline(self, formula: str) -> str:
        from .template_renderer import render_template
        tmpl = self.templates.get("inline_math", "${{formula}}$")
        return render_template(tmpl, {"formula": formula.strip()})

    def display(self, formula: str) -> str:
        from .template_renderer import render_template
        tmpl = self.templates.get("display_math")
        if not tmpl:
            return f"\\[\n{formula.strip()}\n\\]"
        return render_template(tmpl, {"formula": formula.strip()})

    def equation(self, formula: str, label: str) -> str:
        from .template_renderer import render_template
        tmpl = self.templates.get("equation")
        safe_label = _sanitize_label(label)
        if not tmpl:
            return f"\\begin{{equation}}\n  {formula.strip()}\n  \\label{{{safe_label}}}\n\\end{{equation}}"
        return render_template(tmpl, {"formula": formula.strip(), "label": safe_label})

    def align(self, formulas_raw: str) -> str:
        from .template_renderer import render_template
        tmpl = self.templates.get("align")
        # Placeholder suggests using literal '\\\\' to separate lines.
        parts = [p.strip() for p in re.split(r"\\\\+", formulas_raw) if p.strip()]
        joined = " \\\\\n        ".join(parts) if parts else formulas_raw.strip()
        if not tmpl:
            return f"\\begin{{align}}\n  {joined}\n\\end{{align}}"
        return render_template(tmpl, {"formulas": joined})
