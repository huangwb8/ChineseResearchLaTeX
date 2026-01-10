#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set, Tuple
from urllib.parse import quote
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .latex_parser import strip_comments


_BIBKEY_RE = re.compile(r"@[A-Za-z]+\s*\{\s*([^,\s]+)\s*,")
_CITE_RE = re.compile(r"\\cite[a-zA-Z\*]*\s*(?:\[[^\]]*\]\s*)*\{([^}]*)\}")
_DOI_FIELD_RE = re.compile(r'(?i)\bdoi\s*=\s*(?:\{([^}]*)\}|"([^"]*)")')
_DOI_PREFIX_RE = re.compile(r"(?i)^(?:doi\s*:)?\s*https?://(?:dx\.)?doi\.org/")
_DOI_FORMAT_RE = re.compile(r"(?i)^10\.\d{4,9}/\S+$")


@dataclass(frozen=True)
class CitationCheckResult:
    cite_keys: List[str]
    bib_keys: List[str]
    missing_keys: List[str]
    missing_doi_keys: List[str]
    invalid_doi_keys: List[str]


def _strip_ignored_environments(tex_text: str, *, envs: Set[str]) -> str:
    """
    为引用扫描剔除“类代码/原样输出”环境内容（避免把示例代码里的 \\cite{...} 当成真实引用）。
    仅做近似：按行状态机识别 \\begin{env} ... \\end{env}。
    """
    source = tex_text or ""
    in_env: Optional[str] = None
    out_lines: List[str] = []
    for line in source.splitlines():
        probe = line
        if in_env is None:
            for e in envs:
                if f"\\begin{{{e}}}" in probe:
                    in_env = e
                    break
            out_lines.append(line)
            continue

        # in ignored env
        if f"\\end{{{in_env}}}" in probe:
            in_env = None
            out_lines.append(line)
        else:
            out_lines.append("")
    return "\n".join(out_lines)


def normalize_doi(raw: str) -> str:
    d = (raw or "").strip().strip("{}").strip()
    if not d:
        return ""
    d = _DOI_PREFIX_RE.sub("", d).strip()
    return d


def parse_bib_keys(bib_text: str) -> Set[str]:
    keys = set()
    for m in _BIBKEY_RE.finditer(bib_text):
        key = (m.group(1) or "").strip()
        if key:
            keys.add(key)
    return keys


def parse_cite_keys(tex_text: str) -> List[str]:
    scan = strip_comments(tex_text or "")
    scan = _strip_ignored_environments(scan, envs={"verbatim", "lstlisting", "minted"})
    keys: List[str] = []
    for m in _CITE_RE.finditer(scan):
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
            except (OSError, UnicodeError):
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
        doi = normalize_doi(dm.group(1) or dm.group(2) or "")
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
            except (OSError, UnicodeError, ValueError):
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
    invalid_doi = sorted(
        {k for k in cite_keys if (k in set(bib_keys)) and doi_map.get(k) and (not _DOI_FORMAT_RE.match(doi_map.get(k, "")))}
    )
    return CitationCheckResult(
        cite_keys=cite_keys,
        bib_keys=bib_keys,
        missing_keys=missing,
        missing_doi_keys=missing_doi,
        invalid_doi_keys=invalid_doi,
    )


def verify_doi_via_crossref(*, doi: str, timeout_s: float = 5.0) -> bool:
    """
    可选联网校验：通过 Crossref API 检查 DOI 是否存在对应 works。
    失败/超时返回 False（调用方应把 False 视为“需人工核验”，而非断言不存在）。
    """
    d = normalize_doi(doi)
    if not d or (not _DOI_FORMAT_RE.match(d)):
        return False
    url = f"https://api.crossref.org/works/{quote(d)}"
    try:
        req = Request(url, headers={"User-Agent": "ChineseResearchLaTeX/nsfc-justification-writer"})
        with urlopen(req, timeout=float(timeout_s)) as resp:
            if int(getattr(resp, "status", 200)) != 200:
                return False
            body = resp.read().decode("utf-8", errors="ignore")
            return "\"message\"" in body and "\"DOI\"" in body
    except (HTTPError, URLError, TimeoutError, OSError, ValueError):
        return False
