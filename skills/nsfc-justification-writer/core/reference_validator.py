#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set, Tuple


_BIBKEY_RE = re.compile(r"@[A-Za-z]+\s*\{\s*([^,\s]+)\s*,")
_CITE_RE = re.compile(r"\\cite[a-zA-Z\*]*\s*(?:\[[^\]]*\]\s*)*\{([^}]*)\}")
_DOI_FIELD_RE = re.compile(r"(?i)\\bdoi\\s*=\\s*(?:\\{([^}]*)\\}|\"([^\"]*)\")")


@dataclass(frozen=True)
class CitationCheckResult:
    cite_keys: List[str]
    bib_keys: List[str]
    missing_keys: List[str]
    missing_doi_keys: List[str]


def parse_bib_keys(bib_text: str) -> Set[str]:
    keys = set()
    for m in _BIBKEY_RE.finditer(bib_text):
        key = (m.group(1) or "").strip()
        if key:
            keys.add(key)
    return keys


def parse_cite_keys(tex_text: str) -> List[str]:
    keys: List[str] = []
    for m in _CITE_RE.finditer(tex_text):
        raw = (m.group(1) or "").strip()
        if not raw:
            continue
        for part in raw.split(","):
            key = part.strip()
            if key:
                keys.append(key)
    return keys


def load_project_bib_keys(project_root: Path, bib_globs: Iterable[str]) -> Set[str]:
    all_keys: Set[str] = set()
    for pattern in bib_globs:
        for bib_path in project_root.glob(pattern):
            if not bib_path.is_file():
                continue
            try:
                all_keys |= parse_bib_keys(bib_path.read_text(encoding="utf-8", errors="ignore"))
            except Exception:
                continue
    return all_keys


def _parse_bib_doi_map(bib_text: str) -> Dict[str, str]:
    entries: Dict[str, str] = {}
    matches = list(_BIBKEY_RE.finditer(bib_text))
    for i, m in enumerate(matches):
        key = (m.group(1) or "").strip()
        if not key:
            continue
        start = m.end()
        end = matches[i + 1].start() if (i + 1) < len(matches) else len(bib_text)
        chunk = bib_text[start:end]
        dm = _DOI_FIELD_RE.search(chunk)
        if not dm:
            continue
        doi = (dm.group(1) or dm.group(2) or "").strip().strip("{}").strip()
        if doi:
            entries[key] = doi
    return entries


def load_project_bib_doi_map(project_root: Path, bib_globs: Iterable[str]) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for pattern in bib_globs:
        for bib_path in project_root.glob(pattern):
            if not bib_path.is_file():
                continue
            try:
                out.update(_parse_bib_doi_map(bib_path.read_text(encoding="utf-8", errors="ignore")))
            except Exception:
                continue
    return out


def check_citations(
    *,
    tex_text: str,
    project_root: Path,
    bib_globs: Iterable[str],
) -> CitationCheckResult:
    cite_keys = parse_cite_keys(tex_text)
    bib_keys = sorted(load_project_bib_keys(project_root, bib_globs))
    missing = sorted({k for k in cite_keys if k not in set(bib_keys)})
    doi_map = load_project_bib_doi_map(project_root, bib_globs)
    missing_doi = sorted({k for k in cite_keys if (k in set(bib_keys)) and (not doi_map.get(k))})
    return CitationCheckResult(
        cite_keys=cite_keys,
        bib_keys=bib_keys,
        missing_keys=missing,
        missing_doi_keys=missing_doi,
    )
