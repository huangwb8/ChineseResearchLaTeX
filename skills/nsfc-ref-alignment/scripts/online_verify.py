#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple


def _http_get_json(url: str, timeout_s: int = 20) -> Tuple[Optional[dict], Optional[str]]:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "nsfc-ref-alignment/0.1 (mailto: none)",
            "Accept": "application/json",
        },
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            payload = resp.read().decode("utf-8", errors="ignore")
            return json.loads(payload), None
    except Exception as e:
        return None, str(e)


def normalize_title(title: str) -> str:
    t = str(title or "").strip().lower()
    # remove common LaTeX braces/commands crudely
    t = re.sub(r"\\[a-zA-Z]+\*?(?:\[[^\]]*\])?(?:\{[^}]*\})?", " ", t)
    t = t.replace("{", " ").replace("}", " ")
    t = re.sub(r"[^a-z0-9]+", " ", t)
    return " ".join(t.split())


def title_similarity(a: str, b: str) -> float:
    na = normalize_title(a)
    nb = normalize_title(b)
    if not na or not nb:
        return 0.0
    sa = set(na.split())
    sb = set(nb.split())
    if not sa or not sb:
        return 0.0
    inter = len(sa & sb)
    union = len(sa | sb)
    return inter / max(1, union)


@dataclass
class OnlineCheckResult:
    ok: bool
    doi: str
    crossref_ok: bool
    openalex_ok: bool
    crossref_title: str
    openalex_title: str
    error: str
    title_similarity_crossref: float
    title_similarity_openalex: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ok": self.ok,
            "doi": self.doi,
            "crossref_ok": self.crossref_ok,
            "openalex_ok": self.openalex_ok,
            "crossref_title": self.crossref_title,
            "openalex_title": self.openalex_title,
            "error": self.error,
            "title_similarity_crossref": self.title_similarity_crossref,
            "title_similarity_openalex": self.title_similarity_openalex,
        }


def check_doi_online(doi: str, bib_title: str, sleep_s: float = 0.0) -> OnlineCheckResult:
    doi_norm = (doi or "").strip()
    # Accept common variants
    doi_norm = re.sub(r"^(?i)\s*doi\s*:\s*", "", doi_norm).strip()
    m_url = re.search(r"(?i)doi\.org/(?P<doi>10\.\d{4,9}/.+)$", doi_norm)
    if m_url:
        doi_norm = m_url.group("doi").strip()
    if not doi_norm:
        return OnlineCheckResult(
            ok=False,
            doi="",
            crossref_ok=False,
            openalex_ok=False,
            crossref_title="",
            openalex_title="",
            error="empty doi",
            title_similarity_crossref=0.0,
            title_similarity_openalex=0.0,
        )

    if sleep_s > 0:
        time.sleep(sleep_s)

    crossref_title = ""
    openalex_title = ""
    crossref_ok = False
    openalex_ok = False
    err_parts = []

    doi_encoded_crossref = urllib.parse.quote(doi_norm, safe="")
    # OpenAlex accepts DOI in the path form; keep '/' unescaped for readability (server should decode either way).
    doi_encoded_openalex = urllib.parse.quote(doi_norm, safe="/")

    # Crossref (existence + title)
    crossref_url = f"https://api.crossref.org/works/{doi_encoded_crossref}"
    crossref_json, crossref_err = _http_get_json(crossref_url)
    if crossref_json and isinstance(crossref_json, dict):
        msg = (crossref_json.get("message") or {}) if isinstance(crossref_json.get("message"), dict) else {}
        titles = msg.get("title") or []
        if isinstance(titles, list) and titles:
            crossref_title = str(titles[0] or "")
        crossref_ok = True
    else:
        err_parts.append(f"crossref: {crossref_err or 'unknown error'}")

    # OpenAlex (existence + title)
    openalex_url = f"https://api.openalex.org/works/https://doi.org/{doi_encoded_openalex}"
    openalex_json, openalex_err = _http_get_json(openalex_url)
    if openalex_json and isinstance(openalex_json, dict):
        openalex_title = str(openalex_json.get("title") or "")
        openalex_ok = True
    else:
        err_parts.append(f"openalex: {openalex_err or 'unknown error'}")

    sim_crossref = title_similarity(bib_title, crossref_title) if crossref_title else 0.0
    sim_openalex = title_similarity(bib_title, openalex_title) if openalex_title else 0.0

    ok = crossref_ok or openalex_ok
    return OnlineCheckResult(
        ok=ok,
        doi=doi_norm,
        crossref_ok=crossref_ok,
        openalex_ok=openalex_ok,
        crossref_title=crossref_title,
        openalex_title=openalex_title,
        error="; ".join(err_parts),
        title_similarity_crossref=sim_crossref,
        title_similarity_openalex=sim_openalex,
    )
