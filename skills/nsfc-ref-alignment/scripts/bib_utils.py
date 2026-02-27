#!/usr/bin/env python3
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


_BIBTEXPARSER = None
_BIBTEXPARSER_ERR: Optional[str] = None
_WARNED_BIBTEXPARSER_MISSING = False

try:
    import bibtexparser  # type: ignore

    _BIBTEXPARSER = bibtexparser
except Exception as e:  # pragma: no cover
    _BIBTEXPARSER = None
    _BIBTEXPARSER_ERR = str(e)


@dataclass(frozen=True)
class BibEntry:
    key: str
    entry_type: str
    fields: Dict[str, str]  # lowercase keys
    source: str  # path string

    def get(self, name: str, default: str = "") -> str:
        return str(self.fields.get(name.lower(), default) or default)


def _normalize_field_value(v: Any) -> str:
    s = str(v or "").strip()
    # collapse whitespace
    return " ".join(s.split())


def parse_bib_file(bib_path: Path) -> Tuple[Dict[str, BibEntry], List[str]]:
    """
    Parse a bib file into dict[key -> BibEntry]. Best-effort.
    """
    warnings: List[str] = []
    text = bib_path.read_text(encoding="utf-8", errors="ignore")
    out: Dict[str, BibEntry] = {}

    # Prefer bibtexparser if available (more robust for nested braces).
    global _WARNED_BIBTEXPARSER_MISSING
    if _BIBTEXPARSER is not None:
        try:
            bib_db = _BIBTEXPARSER.loads(text)
            for e in (bib_db.entries or []):
                key = e.get("ID") or e.get("id")
                if not key:
                    continue
                entry_type = str(e.get("ENTRYTYPE") or e.get("entrytype") or "").strip().lower()
                fields = {str(k).lower(): _normalize_field_value(v) for k, v in e.items()}
                out[str(key)] = BibEntry(key=str(key), entry_type=entry_type, fields=fields, source=str(bib_path))
            if out:
                return out, warnings
        except Exception as e:
            warnings.append(f"bibtexparser failed to parse {bib_path.name}; fallback to manual parser ({e})")
    else:
        # Avoid spamming the same warning for every .bib file.
        if not _WARNED_BIBTEXPARSER_MISSING:
            warnings.append(f"bibtexparser unavailable ({_BIBTEXPARSER_ERR or 'unknown'}); using manual BibTeX parser (best-effort)")
            _WARNED_BIBTEXPARSER_MISSING = True

    # Fallback manual parsing (good enough for most clean BibTeX).
    # This will not correctly parse all nested braces, but still catches missing keys / basic fields.
    entry_re = re.compile(r"@(?P<typ>\w+)\s*\{\s*(?P<key>[^,]+)\s*,", re.MULTILINE)
    matches = list(entry_re.finditer(text))
    for i, m in enumerate(matches):
        entry_type = m.group("typ").strip().lower()
        key = m.group("key").strip()
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[start:end]

        fields: Dict[str, str] = {}
        # naive field pattern: name = {value} or "value"
        for fm in re.finditer(r"(?P<name>\w+)\s*=\s*(?P<val>\{[^{}]*\}|\"[^\"]*\")\s*,?", body, re.MULTILINE):
            name = fm.group("name").strip().lower()
            val = fm.group("val").strip().strip(",").strip()
            if val.startswith("{") and val.endswith("}"):
                val = val[1:-1]
            if val.startswith("\"") and val.endswith("\""):
                val = val[1:-1]
            fields[name] = _normalize_field_value(val)

        out[key] = BibEntry(key=key, entry_type=entry_type, fields=fields, source=str(bib_path))

    if not out:
        warnings.append(f"no bib entries parsed from {bib_path}")
    return out, warnings


def merge_bib_entries(bib_files: List[Path]) -> Tuple[Dict[str, BibEntry], Dict[str, List[str]], List[str]]:
    """
    Merge bib entries from multiple bib files.
    Returns (entries_by_key, duplicates, warnings).
    duplicates: key -> list of sources (including the chosen one)
    """
    warnings: List[str] = []
    entries: Dict[str, BibEntry] = {}
    sources: Dict[str, List[str]] = {}

    for bib in bib_files:
        if not bib.exists():
            warnings.append(f"bib file not found: {bib}")
            continue
        parsed, w = parse_bib_file(bib)
        warnings.extend(w)
        for k, e in parsed.items():
            sources.setdefault(k, []).append(str(bib))
            if k not in entries:
                entries[k] = e

    duplicates = {k: v for k, v in sources.items() if len(v) > 1}
    return entries, duplicates, warnings


def validate_doi(doi: str, doi_regex: str) -> bool:
    if not doi:
        return True
    try:
        d = doi.strip()
        # Common variants in BibTeX exports
        d = re.sub(r"^(?i)\s*doi\s*:\s*", "", d).strip()
        m_url = re.search(r"(?i)doi\.org/(?P<doi>10\.\d{4,9}/.+)$", d)
        if m_url:
            d = m_url.group("doi").strip()

        m = re.search(doi_regex, d)
        return bool(m and m.start() == 0 and m.end() == len(d))
    except Exception:
        # if regex itself is invalid, don't block
        return True


def required_field_issues(
    entry: BibEntry,
    required_common: List[str],
    year_like: List[str],
) -> List[str]:
    issues: List[str] = []
    for f in required_common:
        if not entry.get(f):
            issues.append(f"missing field: {f}")
    if year_like:
        if not any(entry.get(f) for f in year_like):
            issues.append(f"missing field: one of {year_like}")
    return issues
