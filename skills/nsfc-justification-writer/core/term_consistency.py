#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import re
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


def _count_alias_hits(text: str, aliases: Sequence[str]) -> Dict[str, int]:
    hits: Dict[str, int] = {}
    for a in aliases:
        a = str(a)
        if not a:
            continue
        try:
            n = len(re.findall(re.escape(a), text))
        except Exception:
            n = 0
        if n > 0:
            hits[a] = n
    return hits


def _format_hits(hits: Dict[str, int]) -> str:
    if not hits:
        return "—"
    parts = [f"{k}({v})" for k, v in sorted(hits.items(), key=lambda kv: (-kv[1], kv[0]))]
    return ", ".join(parts)


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
        per_file_hits: Dict[str, Dict[str, int]] = {}
        for label in headers:
            text = contents.get(label, "")
            per_file_hits[label] = _count_alias_hits(text, list(aliases))

        any_hit = any(bool(h) for h in per_file_hits.values())
        if not any_hit:
            continue

        variants: List[str] = sorted({k for hits in per_file_hits.values() for k in hits.keys()})
        inconsistent_across_files = len(variants) > 1
        inconsistent_within_file = any(len(hits.keys()) > 1 for hits in per_file_hits.values())
        conclusion = "✅ 一致" if (not inconsistent_across_files and not inconsistent_within_file) else "⚠️ 不一致"
        if inconsistent_across_files:
            issues.append(f"术语“{canonical}”跨章节表述不一致：{', '.join(variants)}")
        if inconsistent_within_file:
            bad = [label for label, hits in per_file_hits.items() if len(hits.keys()) > 1]
            issues.append(f"术语“{canonical}”在同一章节内出现多种表述：{', '.join(bad)}")

        cells = []
        for label in headers:
            cells.append(_format_hits(per_file_hits.get(label, {})))
        rows.append((canonical, cells, conclusion))

    return TermMatrix(headers=headers, rows=rows, issues=issues)
