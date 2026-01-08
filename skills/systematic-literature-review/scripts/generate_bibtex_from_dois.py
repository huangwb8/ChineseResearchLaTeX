#!/usr/bin/env python3
"""
generate_bibtex_from_dois.py - Generate BibTeX entries from a DOI list.

Design goals:
  - Deterministic, minimal-dependency (requests only).
  - Prefer Crossref's BibTeX transformer for correctness.
  - Produce unique keys and a report for any failures.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


def _normalize_doi(raw: str) -> str:
    raw = (raw or "").strip()
    raw = re.sub(r"^https?://(dx\.)?doi\.org/", "", raw, flags=re.IGNORECASE)
    raw = re.sub(r"^doi:\s*", "", raw, flags=re.IGNORECASE).strip()
    return raw.lower()


def _slug(s: str) -> str:
    s = (s or "").strip().lower()
    s = re.sub(r"[^a-z0-9]+", "", s)
    return s


def _make_key(bibtex: str, doi: str) -> str:
    """
    Produce a stable key:
      - Try to parse existing key from Crossref output.
      - Otherwise derive from DOI suffix.
    """
    m = re.search(r"@\w+\{([^,]+),", bibtex)
    if m:
        key = m.group(1).strip()
        if key:
            return key
    # Fallback: doi-based key
    suffix = doi.split("/", 1)[-1] if "/" in doi else doi
    suffix = _slug(suffix)[:24] or "ref"
    return f"doi{suffix}"


@dataclass(frozen=True)
class BibResult:
    doi: str
    ok: bool
    key: str | None
    error: str | None


def _fetch_crossref_bibtex(doi: str, *, mailto: Optional[str], timeout_s: int) -> str:
    try:
        import requests  # type: ignore
    except ModuleNotFoundError as e:
        raise RuntimeError("Missing dependency: requests. Install it via `pip install requests`.") from e

    url = f"https://api.crossref.org/works/{doi}/transform/application/x-bibtex"
    headers = {
        "User-Agent": "pipelines/skills systematic-literature-review bibtex-from-dois",
        "Accept": "application/x-bibtex",
    }
    if mailto:
        headers["User-Agent"] += f" (mailto:{mailto})"

    resp = requests.get(url, headers=headers, timeout=timeout_s)
    resp.raise_for_status()
    return resp.text.strip()


def _rewrite_key(bibtex: str, new_key: str) -> str:
    # Keep regex group backrefs real (avoid writing literal "\1" into the output).
    return re.sub(
        r"^(@\w+\{)([^,]+)(,)",
        r"\1" + new_key + r"\3",
        bibtex,
        count=1,
        flags=re.MULTILINE,
    )


def _sanitize_bibtex_for_latex(bibtex: str) -> str:
    """
    Crossref BibTeX sometimes contains HTML entities or raw '&' which breaks LaTeX.
    Apply a conservative, compilation-oriented sanitization.
    """
    # Greek letters (common in biomedical titles)
    greek_map = {
        "alpha": r"{$\\alpha$}",
        "beta": r"{$\\beta$}",
        "gamma": r"{$\\gamma$}",
        "delta": r"{$\\delta$}",
    }
    for name, latex in greek_map.items():
        bibtex = re.sub(rf"&amp;{name};", latex, bibtex, flags=re.IGNORECASE)
        bibtex = re.sub(rf"&{name};", latex, bibtex, flags=re.IGNORECASE)

    # Remaining HTML ampersand entity -> LaTeX escaped ampersand
    bibtex = bibtex.replace("&amp;", r"\&")

    # Raw '&' (not already escaped) -> '\&'
    bibtex = re.sub(r"(?<!\\)&", r"\\&", bibtex)

    return bibtex


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate BibTeX from DOI list via Crossref transformer.")
    parser.add_argument("--input", required=True, type=Path, help="Input DOI list file (one DOI per line)")
    parser.add_argument("--output", required=True, type=Path, help="Output .bib file path")
    parser.add_argument("--report", required=True, type=Path, help="Output JSON report path")
    parser.add_argument("--mailto", default=None, help="Optional email for polite Crossref usage")
    parser.add_argument("--timeout", type=int, default=20, help="HTTP timeout seconds (default: 20)")
    parser.add_argument("--sleep", type=float, default=0.25, help="Polite delay between queries (default: 0.25s)")
    args = parser.parse_args()

    if not args.input.exists():
        print(f"Input not found: {args.input}", file=sys.stderr)
        return 2

    dois = [_normalize_doi(line) for line in args.input.read_text(encoding="utf-8").splitlines()]
    dois = [d for d in dois if d]
    if not dois:
        print("No DOIs provided.", file=sys.stderr)
        return 2

    # Dedupe DOIs while preserving order
    seen: set[str] = set()
    ordered: list[str] = []
    for d in dois:
        if d in seen:
            continue
        seen.add(d)
        ordered.append(d)

    out_entries: list[str] = []
    results: list[BibResult] = []
    used_keys: set[str] = set()

    for doi in ordered:
        try:
            bib = _fetch_crossref_bibtex(doi, mailto=args.mailto, timeout_s=args.timeout)
            key = _make_key(bib, doi)
            key = re.sub(r"[^A-Za-z0-9:_-]+", "", key)[:60] or "ref"
            # Ensure uniqueness
            base = key
            i = 2
            while key in used_keys:
                key = f"{base}_{i}"
                i += 1
            used_keys.add(key)

            bib = _rewrite_key(bib, key)
            bib = _sanitize_bibtex_for_latex(bib)
            out_entries.append(bib)
            results.append(BibResult(doi=doi, ok=True, key=key, error=None))
        except Exception as e:  # pragma: no cover (best-effort network)
            results.append(BibResult(doi=doi, ok=False, key=None, error=str(e)))
        time.sleep(max(0.0, args.sleep))

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.report.parent.mkdir(parents=True, exist_ok=True)

    args.output.write_text("\n\n".join(out_entries).strip() + "\n", encoding="utf-8")
    args.report.write_text(
        json.dumps(
            {
                "input": str(args.input),
                "output": str(args.output),
                "ok": sum(1 for r in results if r.ok),
                "total": len(results),
                "results": [r.__dict__ for r in results],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    failed = [r for r in results if not r.ok]
    if failed:
        print(f"⚠️  BibTeX failures: {len(failed)}/{len(results)}. See report: {args.report}")
        return 1

    print(f"✓ BibTeX written: {args.output} ({len(out_entries)})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
