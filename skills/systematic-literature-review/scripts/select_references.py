#!/usr/bin/env python3
"""
select_references.py - 按高分优先比例选文并生成 BibTeX

输入：评分后的 papers jsonl（包含 score/subtopic/doi/title/year/venue 等）
输出：
  - selected jsonl
  - references.bib
  - selection rationale yaml
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

import yaml


def _read_jsonl(path: Path) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except Exception:
                continue
            if isinstance(obj, dict):
                items.append(obj)
    return items


def _normalize_key(paper: Dict[str, Any]) -> str:
    doi = str(paper.get("doi") or "").strip().lower()
    if doi:
        doi = doi.replace("https://doi.org/", "").replace("http://doi.org/", "")
    title = str(paper.get("title") or "").strip().lower()
    year = str(paper.get("year") or "").strip()
    return doi or f"{title}::{year}"


def _bib_key_from_title(title: str, year: str) -> str:
    tokens = re.findall(r"[A-Za-z0-9]+", title)
    base = "".join(tokens[:3]).lower() or "ref"
    yr = re.sub(r"[^0-9]", "", year) if year else ""
    return (base + yr)[:40] or "ref"


def _make_unique_key(base: str, used_lower: set[str]) -> str:
    candidate = base or "ref"
    if candidate.lower() not in used_lower:
        used_lower.add(candidate.lower())
        return candidate
    suffix = 1
    while f"{candidate}{suffix}".lower() in used_lower:
        suffix += 1
    final = f"{candidate}{suffix}"
    used_lower.add(final.lower())
    return final


def _escape_bib_value(value: str) -> tuple[str, bool]:
    """Escape ampersands; return escaped value and whether a replacement happened."""
    escaped, n = re.subn(r"(?<!\\)&", r"\\&", value)
    return escaped, n > 0


def _normalize_authors(authors: Any) -> str:
    if isinstance(authors, list):
        names: list[str] = []
        for a in authors:
            if isinstance(a, dict) and a.get("name"):
                names.append(str(a["name"]))
            elif isinstance(a, str):
                names.append(a)
        if names:
            return " and ".join(names)
    if isinstance(authors, str) and authors.strip():
        return authors.strip()
    return "Unknown"


def _render_bib_entry(key: str, paper: Dict[str, Any]) -> tuple[str, list[str]]:
    warnings: list[str] = []
    title_raw = paper.get("title") or "Untitled"
    venue_raw = paper.get("venue") or paper.get("journal") or ""
    year_raw = str(paper.get("year") or "").strip()
    url_raw = paper.get("url") or ""
    doi_raw = paper.get("doi") or ""
    authors_raw = paper.get("authors") or paper.get("author") or ""

    title, title_fixed = _escape_bib_value(str(title_raw))
    venue, venue_fixed = _escape_bib_value(str(venue_raw))
    author_str, author_fixed = _escape_bib_value(_normalize_authors(authors_raw))
    doi = str(doi_raw).replace("https://doi.org/", "").replace("http://doi.org/", "").strip()
    year = year_raw if year_raw else "n.d."

    missing_fields = []
    if author_str.lower() == "unknown":
        missing_fields.append("author")
    if venue.strip() == "":
        missing_fields.append("journal")
    if doi == "":
        missing_fields.append("doi")
    if missing_fields:
        warnings.append(f"{key} 缺失字段: {', '.join(missing_fields)}（已填默认值，建议补全）")

    for fixed, label in [(title_fixed, "title"), (venue_fixed, "journal"), (author_fixed, "author")]:
        if fixed:
            warnings.append(f"{key} 自动转义 {label} 中的 & 为 \\&")

    fields = [
        f"title = {{{title}}}",
        f"author = {{{author_str or 'Unknown'}}}",
        f"year = {{{year}}}",
        f"journal = {{{venue or 'Unknown'}}}",
    ]
    if doi:
        fields.append(f"doi = {{{doi}}}")
    if url_raw:
        url, _ = _escape_bib_value(str(url_raw))
        fields.append(f"url = {{{url}}}")
    return "@article{{{key},\n  {fields}\n}}\n".format(key=key, fields=",\n  ".join(fields)), warnings


def _select_papers(
    papers: List[Dict[str, Any]],
    min_refs: int,
    max_refs: int,
    high_score_min: float,
    high_score_max: float,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    unique: Dict[str, Dict[str, Any]] = {}
    for p in papers:
        k = _normalize_key(p)
        if not k:
            continue
        unique[k] = p
    items = list(unique.values())
    items.sort(key=lambda x: (float(x.get("score") or 0), x.get("subtopic", "")), reverse=True)

    total = len(items)
    if total == 0:
        return [], {"total_candidates": 0}

    frac = (high_score_min + high_score_max) / 2.0
    high_count = max(0, min(total, math.ceil(total * frac)))
    selected = items[:high_count]

    # 若未满足最小参考数，继续从剩余中补齐
    idx = high_count
    while len(selected) < min_refs and idx < total:
        selected.append(items[idx])
        idx += 1

    # 控制最大数量
    if len(selected) > max_refs:
        selected = selected[:max_refs]

    # 统计选中文献的实际分数分布
    selected_scores = [float(p.get("score") or 0) for p in selected]
    score_distribution = {
        "high_score_count": sum(1 for s in selected_scores if s >= 7),
        "mid_score_count": sum(1 for s in selected_scores if 4 <= s < 7),
        "low_score_count": sum(1 for s in selected_scores if s < 4),
        "max_score": max(selected_scores) if selected_scores else 0,
        "min_score": min(selected_scores) if selected_scores else 0,
        "avg_score": round(sum(selected_scores) / len(selected_scores), 2) if selected_scores else 0,
    }

    rationale = {
        "total_candidates": total,
        "selected": len(selected),
        "high_score_fraction_used": frac,
        "high_score_bucket": high_count,  # 保留向后兼容
        "min_refs": min_refs,
        "max_refs": max_refs,
        "score_distribution": score_distribution,
    }
    return selected, rationale


def main() -> int:
    parser = argparse.ArgumentParser(description="Select references by score and generate bib.")
    parser.add_argument("--input", required=True, type=Path, help="Scored papers jsonl")
    parser.add_argument("--output", required=True, type=Path, help="Selected papers jsonl output")
    parser.add_argument("--bib", required=True, type=Path, help="BibTeX output path")
    parser.add_argument("--selection", required=True, type=Path, help="Selection rationale yaml")
    parser.add_argument("--min-refs", type=int, required=True, help="Minimum references to keep")
    parser.add_argument("--max-refs", type=int, required=True, help="Maximum references to keep")
    parser.add_argument("--high-score-min", type=float, default=0.6, help="Lower bound of high-score fraction")
    parser.add_argument("--high-score-max", type=float, default=0.8, help="Upper bound of high-score fraction")
    args = parser.parse_args()

    papers = _read_jsonl(args.input)
    selected, rationale = _select_papers(
        papers,
        min_refs=args.min_refs,
        max_refs=args.max_refs,
        high_score_min=args.high_score_min,
        high_score_max=args.high_score_max,
    )

    if not selected:
        print("✗ 无可选文献", file=sys.stderr)
        return 1

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as fo:
        for p in selected:
            fo.write(json.dumps(p, ensure_ascii=False) + "\n")

    # 生成简易 BibTeX
    args.bib.parent.mkdir(parents=True, exist_ok=True)
    bib_entries = []
    used_keys_lower: set[str] = set()
    warnings: list[str] = []
    for p in selected:
        title = str(p.get("title") or "")
        year = str(p.get("year") or "")
        key = _make_unique_key(_bib_key_from_title(title, year), used_keys_lower)
        entry, entry_warnings = _render_bib_entry(key, p)
        bib_entries.append(entry)
        warnings.extend(entry_warnings)
    args.bib.write_text("\n".join(bib_entries), encoding="utf-8")
    if warnings:
        print("⚠️ BibTeX 清洗提示:", file=sys.stderr)
        for w in warnings[:20]:
            print(f"  - {w}", file=sys.stderr)

    args.selection.parent.mkdir(parents=True, exist_ok=True)
    yaml.safe_dump(rationale, args.selection.open("w", encoding="utf-8"), allow_unicode=True, sort_keys=False)

    print(json.dumps({"selected": len(selected), "bib": str(args.bib), "selection": str(args.selection)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
