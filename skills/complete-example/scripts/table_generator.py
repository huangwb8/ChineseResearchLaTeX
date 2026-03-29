"""
TableGenerator - generate safe LaTeX tables from a TABLE placeholder.

Design: prefer deterministic fallback output. If a real LLM is available and
`prompts.generate_table` exists, we can ask it for JSON and render via template.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional
import json
import re


def _slugify_label(text: str) -> str:
    # Keep it LaTeX-label friendly.
    cleaned = re.sub(r"[^a-zA-Z0-9:_-]+", "-", text.strip())
    cleaned = cleaned.strip("-").lower()
    return cleaned or "table"


@dataclass(frozen=True)
class TableSpec:
    caption: str
    column_spec: str
    header_row: str
    data_rows: list[str]
    label: str
    header_rows: Optional[str] = None  # complex table


class TableGenerator:
    def __init__(self, llm_client: Any, config: Dict[str, Any], templates: Dict[str, str]):
        self.llm = llm_client
        self.config = config
        self.templates = templates

    def generate(self, description: str, complexity: str, context: str = "") -> str:
        from .template_renderer import render_template
        spec = self._generate_spec(description, complexity, context)
        template_name = "complex_table" if (complexity == "complex" and spec.header_rows) else "simple_table"
        template = self.templates.get(template_name)
        if not template:
            # Very defensive fallback: avoid breaking compilation.
            return f"% (table template missing) {description}"

        if template_name == "complex_table":
            return render_template(template, {
                "caption": spec.caption,
                "column_spec": spec.column_spec,
                "header_rows": spec.header_rows or spec.header_row,
                "data_rows": "\n        ".join(spec.data_rows),
                "label": spec.label,
            })

        return render_template(template, {
            "caption": spec.caption,
            "column_spec": spec.column_spec,
            "header_row": spec.header_row,
            "data_rows": "\n        ".join(spec.data_rows),
            "label": spec.label,
        })

    def _generate_spec(self, description: str, complexity: str, context: str) -> TableSpec:
        # Prefer LLM JSON if available; otherwise deterministic fallback.
        prompt_tmpl = (self.config.get("prompts") or {}).get("generate_table")
        level_cfg = (((self.config.get("generation") or {}).get("table_generation") or {})
                     .get("complexity_levels") or {}).get(complexity, {})
        num_columns = int(level_cfg.get("max_columns", 5))
        num_rows = int(level_cfg.get("max_rows", 10))

        if prompt_tmpl and hasattr(self.llm, "complete"):
            try:
                prompt = prompt_tmpl.format(
                    table_theme=description,
                    complexity=complexity,
                    num_columns=num_columns,
                    num_rows=num_rows,
                    purpose="示例展示",
                    context=context[:1200],
                )
                raw = self.llm.complete(prompt, response_format="json", temperature=0.7)
                data = json.loads(raw)
                return TableSpec(
                    caption=str(data.get("caption") or description),
                    column_spec=str(data.get("column_spec") or ("l" + "c" * max(2, min(4, num_columns - 1)))),
                    header_row=str(data.get("header_row") or r"\textbf{指标} & \textbf{组A} & \textbf{组B} & \textbf{\textit{P} value} \\"),
                    data_rows=[str(x) for x in (data.get("data_rows") or [])] or [
                        r"准确率 & 0.91 & 0.88 & 0.032 \\",
                        r"召回率 & 0.87 & 0.84 & 0.041 \\",
                        r"F1 分数 & 0.89 & 0.86 & 0.028 \\",
                    ],
                    label=str(data.get("label") or f"tab:{_slugify_label(description)}"),
                    header_rows=data.get("header_rows"),
                )
            except Exception:
                pass

        # Deterministic fallback (always valid LaTeX, moderate size).
        label = f"tab:{_slugify_label(description)}"
        if complexity == "simple":
            return TableSpec(
                caption=description,
                column_spec="lcc",
                header_row=r"\textbf{参数} & \textbf{数值} & \textbf{单位} \\",
                data_rows=[
                    r"温度 & 25 & $^\circ$C \\",
                    r"压力 & 1.0 & atm \\",
                    r"时间 & 24 & h \\",
                ],
                label=label,
            )

        if complexity == "complex":
            # Multirow/multicolumn are optional; keep minimal to reduce package assumptions.
            return TableSpec(
                caption=description,
                column_spec="lllll",
                header_row=r"& \textbf{Characteristics} & \textbf{High (n=137)} & \textbf{Low (n=235)} & \textbf{\textit{P} value} \\",
                header_rows=r"& \textbf{Characteristics} & \textbf{High (n=137)} & \textbf{Low (n=235)} & \textbf{\textit{P} value} \\",
                data_rows=[
                    r"\textbf{Gender (\%)} & Male  & 85 (62.0) & 154 (65.5) & 0.572 \\",
                    r" & Female & 52 (38.0) & 81 (34.5) &  \\",
                    r"\textbf{Age (mean (SD))} &  & 65.50 (10.22) & 66.06 (10.95) & 0.628 \\",
                ],
                label=label,
            )

        # moderate
        return TableSpec(
            caption=description,
            column_spec="lcccc",
            header_row=r"\textbf{模型} & \textbf{Acc} & \textbf{Recall} & \textbf{F1} & \textbf{\textit{P} value} \\",
            data_rows=[
                r"Baseline & 0.86 & 0.83 & 0.84 & 0.041 \\",
                r"Proposed & 0.91 & 0.87 & 0.89 & 0.028 \\",
                r"Ablation & 0.88 & 0.84 & 0.86 & 0.036 \\",
            ],
            label=label,
        )
