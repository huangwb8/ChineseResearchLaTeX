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


def build_term_matrices(
    *,
    files: Mapping[str, Path],
    dimensions: Mapping[str, Mapping[str, Sequence[str]]],
) -> Dict[str, TermMatrix]:
    out: Dict[str, TermMatrix] = {}
    for dim_name, alias_groups in dimensions.items():
        if not alias_groups:
            continue
        out[str(dim_name)] = build_term_matrix(files=files, alias_groups=alias_groups)
    return out


def format_term_matrices_markdown(mats: Mapping[str, TermMatrix]) -> str:
    if not mats:
        return "（未配置术语一致性规则：terminology.dimensions 或 terminology.alias_groups 为空）\n"
    parts: List[str] = []
    for name, mat in mats.items():
        parts.append(f"## {name}\n")
        parts.append(mat.to_markdown().rstrip() + "\n")
    return "\n".join(parts).strip() + "\n"


class CrossChapterValidator:
    def __init__(self, *, files: Mapping[str, Path], terminology_config: Mapping[str, object]) -> None:
        self.files = dict(files)
        self.terminology_config = dict(terminology_config)

    def build(self) -> Dict[str, TermMatrix]:
        dims = self.terminology_config.get("dimensions")
        if isinstance(dims, dict) and dims:
            # dimensions: {dim_name: {canonical: [aliases...]}}
            safe_dims: Dict[str, Dict[str, Sequence[str]]] = {}
            for dn, groups in dims.items():
                if not isinstance(dn, str) or not isinstance(groups, dict):
                    continue
                safe_groups: Dict[str, Sequence[str]] = {}
                for k, v in groups.items():
                    if isinstance(k, str) and isinstance(v, list):
                        safe_groups[k] = [str(x) for x in v if str(x).strip()]
                if safe_groups:
                    safe_dims[dn] = safe_groups
            return build_term_matrices(files=self.files, dimensions=safe_dims)

        alias_groups = self.terminology_config.get("alias_groups")
        if isinstance(alias_groups, dict) and alias_groups:
            safe_groups: Dict[str, Sequence[str]] = {}
            for k, v in alias_groups.items():
                if isinstance(k, str) and isinstance(v, list):
                    safe_groups[k] = [str(x) for x in v if str(x).strip()]
            return build_term_matrices(files=self.files, dimensions={"术语": safe_groups})

        return {}

    def to_markdown(self) -> str:
        mats = self.build()
        return format_term_matrices_markdown(mats)
