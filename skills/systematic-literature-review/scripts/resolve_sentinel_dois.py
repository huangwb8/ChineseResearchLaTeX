#!/usr/bin/env python3
"""
resolve_sentinel_dois.py - Resolve sentinel paper titles to DOIs via Crossref.

Purpose:
  - Turn human-readable sentinel paper strings into a DOI list for citation chasing.
  - Designed for "real run" testing where we want stage-3 citation chasing to execute.

Input:
  - A text file with one sentinel paper string per line (title, or "Author et al. Year", etc.)

Output:
  - A text file with one normalized DOI per line (lowercase, without https://doi.org/)
  - A JSON report with resolution details and failures
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional


def _normalize_doi(raw: str) -> str:
    raw = (raw or "").strip()
    raw = re.sub(r"^https?://(dx\.)?doi\.org/", "", raw, flags=re.IGNORECASE)
    raw = re.sub(r"^doi:\s*", "", raw, flags=re.IGNORECASE).strip()
    return raw.lower()


def _looks_like_doi(text: str) -> bool:
    text = (text or "").strip()
    return bool(re.search(r"\b10\.\d{4,9}/\S+\b", text))


def _extract_doi(text: str) -> Optional[str]:
    if not text:
        return None
    m = re.search(r"\b10\.\d{4,9}/\S+\b", text)
    if not m:
        return None
    return _normalize_doi(m.group(0))


@dataclass(frozen=True)
class Resolution:
    query: str
    doi: str | None
    score: float | None
    title: str | None
    year: int | None
    url: str | None
    source: str
    error: str | None = None


def _crossref_best_match(query: str, *, mailto: Optional[str], timeout_s: int) -> Resolution:
    try:
        import requests  # type: ignore
    except ModuleNotFoundError as e:
        raise RuntimeError("Missing dependency: requests. Install it via `pip install requests`.") from e

    url = "https://api.crossref.org/works"
    params: dict[str, Any] = {
        "query.bibliographic": query,
        "rows": 5,
    }
    if mailto:
        params["mailto"] = mailto

    try:
        resp = requests.get(url, params=params, timeout=timeout_s)
        resp.raise_for_status()
        data = resp.json()
        items = (((data or {}).get("message") or {}).get("items") or [])
        if not items:
            return Resolution(query=query, doi=None, score=None, title=None, year=None, url=None, source="crossref", error="no_items")

        def norm_text(s: str) -> list[str]:
            s = (s or "").lower()
            s = re.sub(r"[^a-z0-9]+", " ", s)
            return [t for t in s.split() if t and t not in {"et", "al"}]

        # Try to extract the "title-like" segment from the query to avoid author/year noise.
        title_like = query
        m = re.search(r"\b(19|20)\d{2}\b", query)
        if m:
            tail = query[m.end():].strip(" -:;,.")
            if len(tail) >= 8:
                title_like = tail

        target_tokens = set(norm_text(title_like))

        def candidate_score(it: dict) -> tuple[float, float]:
            title = ((it.get("title") or [None]) or [None])[0] or ""
            title_tokens = set(norm_text(title))
            overlap = len(target_tokens & title_tokens)
            union = len(target_tokens | title_tokens) or 1
            jaccard = overlap / union

            # Penalize obvious non-primary items (e.g., Faculty Opinions recommendations).
            container = (it.get("container-title") or [None])
            container0 = (container[0] if isinstance(container, list) and container else "") or ""
            penalty = 0.0
            if "faculty opinions" in title.lower() or "recommendation" in title.lower():
                penalty -= 0.25
            if "faculty opinions" in container0.lower():
                penalty -= 0.25

            base = float(it.get("score") or 0.0)
            return (jaccard + penalty, base)

        best = None
        best_pair = (-1e9, -1e9)
        for it in items:
            if not isinstance(it, dict):
                continue
            doi = _normalize_doi(it.get("DOI") or "")
            if not doi:
                continue
            pair = candidate_score(it)
            if pair > best_pair:
                best_pair = pair
                best = it

        if best is None:
            it0 = items[0] or {}
            return Resolution(query=query, doi=None, score=float(it0.get("score") or 0.0), title=((it0.get("title") or [None])[0]), year=None, url=it0.get("URL"), source="crossref", error="no_doi_candidates")

        doi = _normalize_doi(best.get("DOI") or "")
        title = (best.get("title") or [None])[0]
        year = None
        issued = ((best.get("issued") or {}).get("date-parts") or [])
        if issued and issued[0] and isinstance(issued[0][0], int):
            year = issued[0][0]
        score = best.get("score")
        return Resolution(
            query=query,
            doi=doi or None,
            score=float(score) if isinstance(score, (int, float)) else None,
            title=title,
            year=year,
            url=best.get("URL"),
            source="crossref",
        )
    except Exception as e:  # pragma: no cover (best-effort network)
        return Resolution(query=query, doi=None, score=None, title=None, year=None, url=None, source="crossref", error=str(e))


def main() -> int:
    parser = argparse.ArgumentParser(description="Resolve sentinel paper strings to DOIs (Crossref).")
    parser.add_argument("--input", required=True, type=Path, help="Input text file (one sentinel string per line)")
    parser.add_argument("--output", required=True, type=Path, help="Output DOI list file (one DOI per line)")
    parser.add_argument("--report", required=True, type=Path, help="Output JSON report path")
    parser.add_argument("--mailto", default=None, help="Optional email for polite Crossref usage")
    parser.add_argument("--timeout", type=int, default=20, help="HTTP timeout seconds (default: 20)")
    parser.add_argument("--sleep", type=float, default=0.25, help="Polite delay between queries (default: 0.25s)")
    args = parser.parse_args()

    if not args.input.exists():
        print(f"Input not found: {args.input}", file=sys.stderr)
        return 2

    raw_lines = [line.strip() for line in args.input.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not raw_lines:
        print("No sentinel queries provided.", file=sys.stderr)
        return 2

    resolutions: list[Resolution] = []
    dois: list[str] = []

    for q in raw_lines:
        # Fast path: already contains a DOI
        if _looks_like_doi(q):
            doi = _extract_doi(q)
            resolutions.append(Resolution(query=q, doi=doi, score=None, title=None, year=None, url=None, source="inline"))
            if doi:
                dois.append(doi)
            continue

        res = _crossref_best_match(q, mailto=args.mailto, timeout_s=args.timeout)
        resolutions.append(res)
        if res.doi:
            dois.append(res.doi)
        time.sleep(max(0.0, args.sleep))

    # Dedupe while preserving order
    seen: set[str] = set()
    deduped: list[str] = []
    for d in dois:
        if d in seen:
            continue
        seen.add(d)
        deduped.append(d)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.report.parent.mkdir(parents=True, exist_ok=True)

    args.output.write_text("\n".join(deduped) + ("\n" if deduped else ""), encoding="utf-8")
    args.report.write_text(
        json.dumps(
            {
                "input": str(args.input),
                "output": str(args.output),
                "count": len(deduped),
                "resolved": [r.__dict__ for r in resolutions],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    unresolved = [r for r in resolutions if not r.doi]
    if unresolved:
        print(f"⚠️  Unresolved: {len(unresolved)}/{len(resolutions)}. See report: {args.report}")

    print(f"✓ DOIs written: {args.output} ({len(deduped)})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
