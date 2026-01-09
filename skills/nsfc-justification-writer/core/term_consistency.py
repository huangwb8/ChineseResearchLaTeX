#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

from .latex_parser import strip_comments


@dataclass(frozen=True)
class TermMatrix:
    headers: List[str]
    rows: List[Tuple[str, List[str], str]]
    issues: List[str]

    def to_markdown(self) -> str:
        header = "| 术语 | " + " | ".join(self.headers) + " | 结论 |"
        sep = "|---" * (len(self.headers) + 2) + "|"
        lines = [header, sep]
        for term, cells, conclusion in self.rows:
            lines.append("| " + " | ".join([term] + cells + [conclusion]) + " |")
        if self.issues:
            lines.append("")
            lines.append("问题摘要：")
            for it in self.issues:
                lines.append(f"- {it}")
        return "\n".join(lines).strip() + "\n"


def _contains_any(text: str, candidates: Sequence[str]) -> Optional[str]:
    for c in candidates:
        if c and (c in text):
            return c
    return None


def build_term_matrix(
    *,
    files: Mapping[str, Path],
    alias_groups: Mapping[str, Sequence[str]],
) -> TermMatrix:
    headers = list(files.keys())
    contents: Dict[str, str] = {}
    for label, path in files.items():
        try:
            contents[label] = strip_comments(path.read_text(encoding="utf-8", errors="ignore"))
        except Exception:
            contents[label] = ""

    rows: List[Tuple[str, List[str], str]] = []
    issues: List[str] = []

    for canonical, aliases in alias_groups.items():
        found: Dict[str, str] = {}
        for label in headers:
            hit = _contains_any(contents.get(label, ""), list(aliases))
            if hit:
                found[label] = hit

        if not found:
            continue

        variants = sorted(set(found.values()))
        conclusion = "✅ 一致" if len(variants) <= 1 else "⚠️ 不一致"
        if len(variants) > 1:
            issues.append(f"术语“{canonical}”在不同章节出现多种表述：{', '.join(variants)}")

        cells = []
        for label in headers:
            cells.append(found.get(label, "—"))
        rows.append((canonical, cells, conclusion))

    return TermMatrix(headers=headers, rows=rows, issues=issues)

