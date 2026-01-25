#!/usr/bin/env python3
"""
build_evidence_cards.py - 从 selected_papers.jsonl 生成“证据卡”（evidence cards）

目的：
- 压缩写作阶段的证据包上下文：只保留必要字段，并对摘要做截断
- bibkey 计算与 select_references.py 保持一致，便于写作时 \cite{bibkey}
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Dict, List


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


def _norm_ws(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").strip()


def _truncate(s: str, max_chars: int) -> str:
    s = _norm_ws(s)
    if max_chars <= 0:
        return s
    if len(s) <= max_chars:
        return s
    if max_chars <= 3:
        return s[:max_chars]
    return s[: max_chars - 3].rstrip() + "..."


def main() -> int:
    parser = argparse.ArgumentParser(description="Build evidence cards from selected_papers.jsonl")
    parser.add_argument("--input", required=True, type=Path, help="selected_papers.jsonl (or enriched variant)")
    parser.add_argument("--output", required=True, type=Path, help="evidence_cards.jsonl")
    parser.add_argument("--abstract-max-chars", type=int, default=800, help="Max chars for abstract (default: 800)")
    args = parser.parse_args()

    papers = _read_jsonl(args.input)
    if not papers:
        raise SystemExit(f"no papers loaded: {args.input}")

    used_lower: set[str] = set()
    cards: list[dict[str, Any]] = []
    for p in papers:
        title = str(p.get("title") or "")
        year = str(p.get("year") or "")
        bibkey = _make_unique_key(_bib_key_from_title(title, year), used_lower)

        abstract = p.get("abstract") or ""
        abstract_short = _truncate(str(abstract), int(args.abstract_max_chars))

        cards.append(
            {
                "bibkey": bibkey,
                "title": _norm_ws(title),
                "year": _norm_ws(year),
                "venue": _norm_ws(str(p.get("venue") or p.get("journal") or "")),
                "doi": _norm_ws(str(p.get("doi") or "")),
                "score": p.get("score"),
                "subtopic": p.get("subtopic"),
                "do_not_cite": bool(p.get("do_not_cite", False)),
                "quality_warnings": p.get("quality_warnings") or [],
                "abstract": abstract_short,
            }
        )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as f:
        for c in cards:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")

    print(json.dumps({"cards": len(cards), "output": str(args.output)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
