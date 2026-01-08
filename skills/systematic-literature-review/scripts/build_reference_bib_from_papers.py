#!/usr/bin/env python3
"""
build_reference_bib_from_papers.py - 从 papers.jsonl 生成 reference.bib（最大参考库）

说明：
  - 该 reference.bib 的目的不是“排版完美”，而是作为“最大候选库”的可读/可用 BibTeX 载体。
  - 优先保证：覆盖率（尽可能多收录）+ 可追踪（尽量带 DOI/URL）+ 可重复（稳定 key）。
  - 不依赖联网：只使用 papers.jsonl 里已有的元数据。
"""

from __future__ import annotations

import argparse
import json
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, Optional
from urllib.parse import quote
import urllib.request


def _sanitize_unicode(text: str) -> str:
    """
    清洗 Unicode 控制字符和不可见字符

    移除的字符类型:
    - U+200E (LEFT-TO-RIGHT MARK)
    - U+200F (RIGHT-TO-LEFT MARK)
    - U+202A-U+202E (方向控制字符)
    - 其他 Unicode 控制字符 (Cc, Cf 类别)

    保留:
    - 正常字母、数字、标点、空格
    - 特殊学术字符（如带变音符号的字母）
    """
    if not text:
        return text

    result = []
    for char in text:
        category = unicodedata.category(char)
        # Cc = Control characters, Cf = Format characters (包括方向控制符)
        if category not in ('Cc', 'Cf'):
            result.append(char)

    return ''.join(result)


def _read_jsonl(path: Path) -> Iterable[Dict[str, Any]]:
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except Exception:
                continue
            if isinstance(obj, dict):
                yield obj


def _normalize_doi(raw: str) -> str:
    raw = (raw or "").strip()
    raw = re.sub(r"^https?://(dx\.)?doi\.org/", "", raw, flags=re.IGNORECASE)
    raw = re.sub(r"^doi:\s*", "", raw, flags=re.IGNORECASE).strip()
    return raw.lower()


def _slug(s: str) -> str:
    s = (s or "").strip().lower()
    s = re.sub(r"[^a-z0-9]+", "", s)
    return s


def _latex_escape(s: str) -> str:
    s = (s or "").replace("&amp;", "&")
    replacements = {
        "\\": "\\textbackslash{}",
        "&": "\\&",
        "%": "\\%",
        "$": "\\$",
        "#": "\\#",
        "_": "\\_",
        "{": "\\{",
        "}": "\\}",
    }
    return "".join(replacements.get(ch, ch) for ch in s)


def _make_key(*, doi: str, title: str, year: Optional[int]) -> str:
    if doi:
        suffix = doi.split("/", 1)[-1] if "/" in doi else doi
        suffix = _slug(suffix)[:24] or "ref"
        return f"doi{suffix}"
    base = _slug(title)[:24] or "ref"
    if year:
        return f"{base}{year}"
    return base


@dataclass(frozen=True)
class Ref:
    key: str
    title: str
    year: Optional[int]
    venue: str
    doi: str
    url: str
    authors: list[str]
    volume: str
    issue: str
    pages: str
    publisher: str
    entry_type: str
    enriched: bool = False


def _to_ref(obj: Dict[str, Any]) -> Optional[Ref]:
    doi = _normalize_doi(str(obj.get("doi") or ""))
    title = _sanitize_unicode(str(obj.get("title") or "").strip())
    if not title and not doi:
        return None
    venue = _sanitize_unicode(str(obj.get("venue") or obj.get("journal") or obj.get("source") or "").strip())
    url = str(obj.get("url") or "").strip()

    # authors: try authorships (OpenAlex), fallback to authors list, fallback to single author
    authors: list[str] = []
    auths = obj.get("authorships") or obj.get("authors") or []
    if isinstance(auths, list):
        for a in auths:
            if isinstance(a, dict):
                name = a.get("author", {}).get("display_name") or a.get("display_name") or a.get("name")
                if name:
                    authors.append(_sanitize_unicode(str(name).strip()))
            elif isinstance(a, str):
                authors.append(_sanitize_unicode(a.strip()))
    first_author = _sanitize_unicode(str(obj.get("author") or "").strip())
    if not authors and first_author:
        authors.append(first_author)

    year_raw = obj.get("year")
    year: Optional[int] = None
    try:
        if isinstance(year_raw, int):
            year = year_raw
        elif year_raw not in (None, "", 0):
            year = int(str(year_raw))
    except Exception:
        year = None

    volume = str(obj.get("volume") or "").strip()
    issue = str(obj.get("issue") or obj.get("number") or "").strip()
    pages = str(obj.get("pages") or obj.get("page") or "").strip()
    publisher = str(obj.get("publisher") or "").strip()
    entry_type = str(obj.get("type") or "").strip().lower()

    key = _make_key(doi=doi, title=title or doi, year=year)
    key = re.sub(r"[^A-Za-z0-9:_-]+", "", key)[:60] or "ref"
    return Ref(
        key=key,
        title=title or doi,
        year=year,
        venue=venue,
        doi=doi,
        url=url,
        authors=authors,
        volume=volume,
        issue=issue,
        pages=pages,
        publisher=publisher,
        entry_type=entry_type,
        enriched=False,
    )


def _render_bib_entry(ref: Ref) -> str:
    fields: list[str] = []
    fields.append(f"  title={{{_latex_escape(ref.title)}}}")
    if ref.authors:
        fields.append(f"  author={{{' and '.join(_latex_escape(a) for a in ref.authors)}}}")
    if ref.venue:
        fields.append(f"  journal={{{_latex_escape(ref.venue)}}}")
    if ref.year is not None:
        fields.append(f"  year={{{ref.year}}}")
    if ref.volume:
        fields.append(f"  volume={{{_latex_escape(ref.volume)}}}")
    if ref.issue:
        fields.append(f"  number={{{_latex_escape(ref.issue)}}}")
    if ref.pages:
        fields.append(f"  pages={{{_latex_escape(ref.pages)}}}")
    if ref.publisher:
        fields.append(f"  publisher={{{_latex_escape(ref.publisher)}}}")
    if ref.doi:
        fields.append(f"  doi={{{ref.doi}}}")
    if ref.url and (not ref.doi or "doi.org" not in ref.url.lower()):
        fields.append(f"  url={{{_latex_escape(ref.url)}}}")

    body = ",\n".join(fields)

    # choose entry type
    entry_type = "article"
    if not ref.venue:
        entry_type = "misc"
    elif "conference" in ref.entry_type or "proceed" in ref.entry_type:
        entry_type = "inproceedings"

    return f"@{entry_type}{{{ref.key},\n{body}\n}}\n"


def _fetch_openalex_work(doi: str, timeout: int = 8) -> Optional[Dict[str, Any]]:
    """Fetch enriched metadata from OpenAlex for a DOI."""
    if not doi:
        return None
    url = f"https://api.openalex.org/works/https://doi.org/{quote(doi)}"
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:  # nosec B310
            data = resp.read()
        return json.loads(data)
    except Exception:
        return None


def _enrich_ref_from_openalex(ref: Ref, *, timeout: int = 8) -> Ref:
    """Return a new Ref enriched from OpenAlex (best-effort)."""
    work = _fetch_openalex_work(ref.doi, timeout=timeout)
    if not work:
        return ref

    venue = ref.venue or str((work.get("host_venue") or {}).get("display_name") or "")
    volume = ref.volume or str((work.get("biblio") or {}).get("volume") or "")
    issue = ref.issue or str((work.get("biblio") or {}).get("issue") or "")
    pages = ref.pages or str((work.get("biblio") or {}).get("pages") or "")
    publisher = ref.publisher or str((work.get("host_venue") or {}).get("publisher") or "")
    entry_type = ref.entry_type or str(work.get("type") or "")

    authors: list[str] = list(ref.authors)
    if not authors:
        auths = work.get("authorships") or []
        for a in auths:
            if isinstance(a, dict):
                name = (
                    (a.get("author") or {}).get("display_name")
                    or a.get("display_name")
                    or a.get("raw_affiliation_string")
                )
                if name:
                    authors.append(str(name).strip())

    return Ref(
        key=ref.key,
        title=ref.title,
        year=ref.year,
        venue=venue.strip(),
        doi=ref.doi,
        url=ref.url or str(work.get("id") or ""),
        authors=authors,
        volume=volume.strip(),
        issue=issue.strip(),
        pages=pages.strip(),
        publisher=publisher.strip(),
        entry_type=entry_type,
        enriched=True,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Build reference.bib from papers.jsonl (maximal coverage, optional enrichment).")
    parser.add_argument("--input", required=True, type=Path, help="Input papers.jsonl (largest candidate pool)")
    parser.add_argument("--output", required=True, type=Path, help="Output reference.bib path")
    parser.add_argument("--max", type=int, default=0, help="Optional max entries (0 means no limit)")
    parser.add_argument("--enrich-openalex", action="store_true", help="Enrich metadata via OpenAlex (requires network, best-effort)")
    parser.add_argument("--enrich-timeout", type=int, default=8, help="OpenAlex timeout seconds (default: 8)")
    args = parser.parse_args()

    inp = args.input.resolve()
    out = args.output.resolve()
    if not inp.exists():
        raise SystemExit(f"input not found: {inp}")

    refs: list[Ref] = []
    for obj in _read_jsonl(inp):
        r = _to_ref(obj)
        if r is not None:
            refs.append(r)

    # ensure unique keys (never drop entries just because of key collision)
    used: set[str] = set()
    uniq: list[Ref] = []
    for r in refs:
        key = r.key
        if key in used:
            base = key
            i = 2
            while f"{base}_{i}" in used:
                i += 1
            key = f"{base}_{i}"
        used.add(key)
        uniq.append(
            Ref(
                key=key,
                title=r.title,
                year=r.year,
                venue=r.venue,
                doi=r.doi,
                url=r.url,
                authors=r.authors,
                volume=r.volume,
                issue=r.issue,
                pages=r.pages,
                publisher=r.publisher,
                entry_type=r.entry_type,
            )
        )
    refs = uniq

    # optional enrichment via OpenAlex (when DOI present)
    if args.enrich_openalex:
        enriched: list[Ref] = []
        for r in refs:
            if r.doi:
                enriched.append(_enrich_ref_from_openalex(r, timeout=int(args.enrich_timeout)))
            else:
                enriched.append(r)
        refs = enriched

    # stable order: Tier not known here; sort by year desc then title
    refs.sort(key=lambda r: (-(r.year or 0), r.title.casefold(), r.key))

    if args.max and args.max > 0:
        refs = refs[: int(args.max)]

    out.parent.mkdir(parents=True, exist_ok=True)
    header = [
        "% reference.bib - maximal reference library generated from papers.jsonl",
        f"% input: {inp}",
        f"% total: {len(refs)}",
        "",
    ]
    content = "\n".join(header) + "\n".join(_render_bib_entry(r).rstrip() for r in refs) + "\n"
    out.write_text(content, encoding="utf-8")
    print(f"✓ reference.bib written: {out} ({len(refs)})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
