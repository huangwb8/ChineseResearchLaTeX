#!/usr/bin/env python3
"""
Deterministic, read-only precheck for NSFC LaTeX proposals.

- Extracts citations and checks bibkey existence.
- Produces rough length metrics (per tex file and overall).
- Optionally compiles in an isolated copy to get PDF page count.

All outputs must be written under a user-provided --out directory (recommended inside .nsfc-qc/).
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import shutil
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set, Tuple


TEX_INPUT_RE = re.compile(r"\\(input|include)\s*\{([^}]+)\}")
TEX_BIB_RE = re.compile(r"\\bibliography\s*\{([^}]+)\}")
TEX_ADDBIB_RE = re.compile(r"\\addbibresource\s*(?:\[[^\]]*\]\s*)?\{([^}]+)\}")
TEX_CITE_RE = re.compile(
    r"\\cite[a-zA-Z*]*\s*(?:\[[^\]]*\]\s*)*\{([^}]+)\}"
)
TEX_COMMENT_RE = re.compile(r"(^|[^\\])%.*?$", flags=re.M)

LATEX_CMD_RE = re.compile(r"\\[a-zA-Z@]+(\*?)\s*(\[[^\]]*\])?\s*(\{[^}]*\})?")

BIB_ENTRY_KEY_RE = re.compile(r"@\w+\s*\{\s*([^,\s]+)\s*,")

# Straight quotes are often mistyped in Chinese-heavy proposals. Prefer TeX quotes: ``...''.
# We only flag cases where the quoted span contains CJK to reduce false positives (e.g., URLs).
STRAIGHT_DQUOTE_CJK_RE = re.compile(r'"([^"\n]*[\u4e00-\u9fff][^"\n]*)"')

DOI_IN_TEXT_RE = re.compile(r"\b10\.\d{4,9}/[^\s\"<>{}]+", flags=re.I)


def _is_within(base: Path, target: Path) -> bool:
    try:
        target.resolve().relative_to(base.resolve())
        return True
    except Exception:
        return False


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def _strip_comments(s: str) -> str:
    # Keep escaped percent (\\%) intact.
    return TEX_COMMENT_RE.sub(r"\1", s)


def _norm_tex_path(raw: str) -> str:
    raw = raw.strip()
    # Allow \input{a/b} without .tex suffix
    return raw if raw.lower().endswith(".tex") else raw + ".tex"


def _resolve_tex_path(base_dir: Path, raw: str) -> Optional[Path]:
    rel = Path(_norm_tex_path(raw))
    # LaTeX allows paths without extension and without leading ./.
    candidates = [
        base_dir / rel,
        base_dir / raw,  # if raw already contains extension
    ]
    for c in candidates:
        if c.exists() and c.is_file():
            return c
    return None


def _find_included_tex_files(main_tex: Path) -> List[Path]:
    seen: Set[Path] = set()
    order: List[Path] = []

    def walk(p: Path) -> None:
        rp = p.resolve()
        if rp in seen:
            return
        seen.add(rp)
        order.append(p)
        try:
            s = _strip_comments(_read_text(p))
        except Exception:
            return
        for m in TEX_INPUT_RE.finditer(s):
            inc = m.group(2).strip()
            # Prefer resolving relative to the including file directory.
            inc_path = _resolve_tex_path(p.parent, inc) or _resolve_tex_path(main_tex.parent, inc)
            if inc_path:
                walk(inc_path)

    walk(main_tex)
    return order


def _find_bib_files(tex_files: Iterable[Path], project_root: Path) -> List[Path]:
    # Prefer explicit \bibliography{...} declarations.
    bib_names: List[str] = []
    for p in tex_files:
        try:
            s = _strip_comments(_read_text(p))
        except Exception:
            continue
        for m in TEX_BIB_RE.finditer(s):
            bib_names.extend([x.strip() for x in m.group(1).split(",") if x.strip()])
        for m in TEX_ADDBIB_RE.finditer(s):
            name = (m.group(1) or "").strip()
            if name:
                bib_names.append(name)

    bib_paths: List[Path] = []
    if bib_names:
        for name in bib_names:
            name = name.strip()
            if not name:
                continue
            # BibTeX allows \bibliography{references/foo,bar}
            rel = Path(name)
            if rel.suffix.lower() != ".bib":
                rel = rel.with_suffix(".bib")
            # Search common locations.
            candidates = [
                project_root / rel,
                project_root / "references" / rel.name,
                project_root / rel.name,
            ]
            for c in candidates:
                if c.exists() and c.is_file():
                    bib_paths.append(c)
                    break

    # Fallback: any .bib under project_root/references
    if not bib_paths:
        refs = project_root / "references"
        if refs.exists():
            bib_paths.extend(sorted(refs.glob("*.bib")))
    return bib_paths


def _extract_citations(tex_files: Iterable[Path], *, project_root: Path) -> Dict[str, List[str]]:
    # bibkey -> list of "path:line" occurrences (first N kept per file scan)
    occ: Dict[str, List[str]] = {}
    for p in tex_files:
        try:
            raw = _strip_comments(_read_text(p))
        except Exception:
            continue
        lines = raw.splitlines()
        for i, line in enumerate(lines, start=1):
            for m in TEX_CITE_RE.finditer(line):
                keys = [k.strip() for k in m.group(1).split(",") if k.strip()]
                for k in keys:
                    occ.setdefault(k, [])
                    if len(occ[k]) < 50:
                        try:
                            rel = p.relative_to(project_root)
                            occ[k].append(f"{rel}:{i}")
                        except Exception:
                            occ[k].append(f"{p}:{i}")
    return occ


def _parse_bib_keys(bib_files: Iterable[Path]) -> Dict[str, Dict[str, str]]:
    # key -> simple field map (best-effort). No external dependencies.
    out: Dict[str, Dict[str, str]] = {}
    # Best-effort single-line field parse; multi-line is handled by a tiny state machine below.
    field_re = re.compile(r"^\s*([a-zA-Z][a-zA-Z0-9_-]*)\s*=\s*[\{\"](.+?)[\}\"]\s*,?\s*$")
    for bf in bib_files:
        try:
            s = _read_text(bf)
        except Exception:
            continue
        current_key: Optional[str] = None
        current_fields: Dict[str, str] = {}
        pending_field: Optional[str] = None
        pending_quote: str = ""
        pending_buf: List[str] = []
        for line in s.splitlines():
            m_key = BIB_ENTRY_KEY_RE.search(line)
            if m_key:
                # flush previous
                if current_key:
                    out[current_key] = current_fields
                current_key = m_key.group(1).strip()
                current_fields = {"__file__": str(bf)}
                pending_field = None
                pending_quote = ""
                pending_buf = []
                continue
            if current_key:
                if pending_field:
                    pending_buf.append(line)
                    joined = "\n".join(pending_buf)
                    # Close when we see a matching quote/bracket at line end (very naive but works for common .bib).
                    if pending_quote == "}" and "}" in line:
                        val = joined.split("}", 1)[0]
                        current_fields.setdefault(pending_field, val.strip())
                        pending_field = None
                        pending_quote = ""
                        pending_buf = []
                    elif pending_quote == '"' and '"' in line:
                        val = joined.split('"', 1)[0]
                        current_fields.setdefault(pending_field, val.strip())
                        pending_field = None
                        pending_quote = ""
                        pending_buf = []
                    continue

                m_f = field_re.match(line)
                if m_f:
                    k = m_f.group(1).lower()
                    v = m_f.group(2).strip()
                    if k not in current_fields:
                        current_fields[k] = v
                    continue

                # Multi-line field start (best-effort).
                m_start = re.match(r"^\s*([a-zA-Z][a-zA-Z0-9_-]*)\s*=\s*([\{\"])\s*(.*)$", line)
                if m_start:
                    k = m_start.group(1).lower()
                    q = m_start.group(2)
                    rest = m_start.group(3)
                    if k in current_fields:
                        continue
                    pending_field = k
                    pending_quote = "}" if q == "{" else '"'
                    pending_buf = [rest]
            if current_key and line.strip().endswith("}"):
                # naive entry end
                pass
        if current_key:
            if pending_field and pending_buf:
                # Flush unfinished value as-is.
                current_fields.setdefault(pending_field, "\n".join(pending_buf).strip())
            out[current_key] = current_fields
    return out


def _rough_text_metrics(tex_files: Iterable[Path]) -> Dict[str, Dict[str, int]]:
    metrics: Dict[str, Dict[str, int]] = {}
    for p in tex_files:
        try:
            s = _strip_comments(_read_text(p))
        except Exception:
            continue
        # Remove common LaTeX commands to approximate natural language length.
        s2 = LATEX_CMD_RE.sub(" ", s)
        # Drop braces and TeX special chars
        s2 = re.sub(r"[{}\\\\$&#_^~]", " ", s2)
        # Count CJK characters and ASCII words separately.
        cjk = len(re.findall(r"[\u4e00-\u9fff]", s2))
        words = len(re.findall(r"[A-Za-z0-9]+", s2))
        chars = len(re.sub(r"\s+", "", s2))
        metrics[str(p)] = {"cjk_chars": cjk, "ascii_words": words, "non_space_chars": chars}
    return metrics


def _detect_quote_issues(tex_files: Iterable[Path], *, project_root: Path) -> dict:
    """
    Detect typography issues related to straight double quotes in Chinese-heavy content.

    We treat `"免疫景观"` as suspicious and recommend TeX quotes: ``免疫景观''.
    This is a best-effort, line-level scan (comment-stripped).
    """
    occurrences: List[dict] = []
    total = 0
    for p in tex_files:
        try:
            raw = _strip_comments(_read_text(p))
        except Exception:
            continue
        for i, line in enumerate(raw.splitlines(), start=1):
            for m in STRAIGHT_DQUOTE_CJK_RE.finditer(line):
                total += 1
                if len(occurrences) >= 200:
                    continue
                inner = m.group(1).strip()
                excerpt = line.strip()
                if len(excerpt) > 120:
                    excerpt = excerpt[:117] + "..."
                try:
                    rel = str(p.relative_to(project_root))
                except Exception:
                    rel = str(p)
                occurrences.append(
                    {
                        "path": rel,
                        "line": i,
                        "excerpt": excerpt,
                        "found": f"\"{inner}\"",
                        "recommendation": f"Use TeX quotes: ``{inner}''",
                    }
                )
    return {
        "straight_double_quotes_with_cjk": {
            "count": total,
            "occurrences_preview": occurrences,
            "note": "In Chinese-heavy proposals, avoid straight quotes like \"...\"; prefer TeX quotes ``...''.",
        }
    }


def _extract_citation_contexts(tex_files: Iterable[Path], *, project_root: Path) -> Dict[str, List[dict]]:
    """
    Extract per-bibkey occurrences with a short context snippet from the proposal.
    This is used as the "proposal side" evidence for later AI semantic checks.
    """
    ctx: Dict[str, List[dict]] = {}
    for p in tex_files:
        try:
            raw = _strip_comments(_read_text(p))
        except Exception:
            continue
        lines = raw.splitlines()
        for i, line in enumerate(lines, start=1):
            for m in TEX_CITE_RE.finditer(line):
                keys = [k.strip() for k in m.group(1).split(",") if k.strip()]
                if not keys:
                    continue
                prev_line = lines[i - 2].strip() if i >= 2 else ""
                next_line = lines[i].strip() if i < len(lines) else ""
                snippet = " ".join([x for x in (prev_line, line.strip(), next_line) if x]).strip()
                if len(snippet) > 220:
                    snippet = snippet[:217] + "..."
                try:
                    rel = str(p.relative_to(project_root))
                except Exception:
                    rel = str(p)
                for k in keys:
                    ctx.setdefault(k, [])
                    if len(ctx[k]) >= 50:
                        continue
                    ctx[k].append({"path": rel, "line": i, "snippet": snippet})
    return ctx


def _strip_jats(s: str) -> str:
    # Crossref abstracts are sometimes in JATS/XML-ish tags.
    return re.sub(r"<[^>]+>", " ", s or "").replace("\n", " ").strip()


def _http_get_json(url: str, *, timeout_s: int, user_agent: str) -> Optional[dict]:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": user_agent, "Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            data = resp.read().decode("utf-8", errors="ignore")
        return json.loads(data)
    except Exception:
        return None


def _http_get_text(url: str, *, timeout_s: int, user_agent: str) -> Optional[str]:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": user_agent, "Accept": "*/*"})
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            return resp.read().decode("utf-8", errors="ignore")
    except Exception:
        return None


def _normalize_doi(raw: str) -> str:
    d = (raw or "").strip()
    d = d.replace("https://doi.org/", "").replace("http://doi.org/", "")
    d = d.replace("https://dx.doi.org/", "").replace("http://dx.doi.org/", "")
    d = d.strip().rstrip(".").rstrip(",").rstrip(";")
    return d


def _guess_doi(fields: Dict[str, str]) -> str:
    for k in ("doi",):
        if fields.get(k):
            return _normalize_doi(fields.get(k, ""))
    for k in ("url", "note", "howpublished", "misc", "annote"):
        if fields.get(k):
            m = DOI_IN_TEXT_RE.search(fields.get(k, ""))
            if m:
                return _normalize_doi(m.group(0))
    return ""


def _guess_arxiv_id(fields: Dict[str, str]) -> str:
    eprint = (fields.get("eprint") or "").strip()
    ap = (fields.get("archiveprefix") or fields.get("archivePrefix") or "").lower()
    if eprint and "arxiv" in ap:
        return eprint
    url = (fields.get("url") or "").strip()
    m = re.search(r"arxiv\.org/(abs|pdf)/([0-9]+\.[0-9]+)(?:v\d+)?", url)
    if m:
        return m.group(2)
    # Older arXiv IDs (very rough)
    m2 = re.search(r"arxiv:([a-z\-]+/\d{7}|\d{7})", (fields.get("note") or ""), flags=re.I)
    if m2:
        return m2.group(1)
    return ""


def _fetch_crossref(doi: str, *, timeout_s: int, user_agent: str) -> dict:
    if not doi:
        return {"ok": False, "error": "no_doi"}
    url = "https://api.crossref.org/works/" + urllib.parse.quote(doi)
    data = _http_get_json(url, timeout_s=timeout_s, user_agent=user_agent)
    if not data or "message" not in data:
        return {"ok": False, "error": "crossref_fetch_failed", "url": url}
    msg = data.get("message") or {}
    title = ""
    if isinstance(msg.get("title"), list) and msg.get("title"):
        title = str(msg.get("title")[0])
    abstract = _strip_jats(str(msg.get("abstract") or "")).strip()
    return {
        "ok": True,
        "source": "crossref",
        "url": url,
        "title": title,
        "abstract": abstract,
        "publisher": msg.get("publisher"),
        "container_title": (msg.get("container-title") or [""])[0] if isinstance(msg.get("container-title"), list) else msg.get("container-title"),
        "published": msg.get("published-print") or msg.get("published-online") or msg.get("created") or {},
    }


def _fetch_arxiv(arxiv_id: str, *, timeout_s: int, user_agent: str) -> dict:
    if not arxiv_id:
        return {"ok": False, "error": "no_arxiv_id"}
    url = "http://export.arxiv.org/api/query?id_list=" + urllib.parse.quote(arxiv_id)
    txt = _http_get_text(url, timeout_s=timeout_s, user_agent=user_agent)
    if not txt:
        return {"ok": False, "error": "arxiv_fetch_failed", "url": url}
    try:
        root = ET.fromstring(txt)
        ns = {"a": "http://www.w3.org/2005/Atom"}
        entry = root.find("a:entry", ns)
        if entry is None:
            return {"ok": False, "error": "arxiv_no_entry", "url": url}
        title = (entry.findtext("a:title", default="", namespaces=ns) or "").strip()
        summary = (entry.findtext("a:summary", default="", namespaces=ns) or "").strip()
        # Find PDF link
        pdf_url = ""
        for link in entry.findall("a:link", ns):
            if link.attrib.get("title") == "pdf" or link.attrib.get("type") == "application/pdf":
                pdf_url = link.attrib.get("href", "")
        if not pdf_url:
            pdf_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"
        return {"ok": True, "source": "arxiv", "url": url, "title": title, "abstract": summary, "pdf_url": pdf_url}
    except Exception:
        return {"ok": False, "error": "arxiv_parse_failed", "url": url}


def _fetch_unpaywall_pdf(doi: str, *, email: str, timeout_s: int, user_agent: str) -> dict:
    if not doi:
        return {"ok": False, "error": "no_doi"}
    if not email:
        return {"ok": False, "error": "missing_email"}
    url = f"https://api.unpaywall.org/v2/{urllib.parse.quote(doi)}?email={urllib.parse.quote(email)}"
    data = _http_get_json(url, timeout_s=timeout_s, user_agent=user_agent)
    if not data:
        return {"ok": False, "error": "unpaywall_fetch_failed", "url": url}
    best = data.get("best_oa_location") or {}
    return {
        "ok": True,
        "source": "unpaywall",
        "url": url,
        "is_oa": bool(data.get("is_oa")),
        "pdf_url": best.get("url_for_pdf") or "",
        "landing_url": best.get("url") or "",
    }


def _download_file(url: str, *, dst: Path, timeout_s: int, user_agent: str, max_bytes: int) -> dict:
    if not url:
        return {"ok": False, "error": "no_url"}
    dst.parent.mkdir(parents=True, exist_ok=True)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": user_agent})
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            total = 0
            with dst.open("wb") as f:
                while True:
                    chunk = resp.read(1024 * 64)
                    if not chunk:
                        break
                    total += len(chunk)
                    if total > max_bytes:
                        return {"ok": False, "error": "download_too_large", "bytes": total}
                    f.write(chunk)
        return {"ok": True, "bytes": total}
    except Exception as e:
        return {"ok": False, "error": f"download_failed: {type(e).__name__}"}


def _extract_pdf_text_excerpt(pdf_path: Path, *, max_chars: int) -> dict:
    """
    Best-effort PDF text extraction. We intentionally avoid hard deps.
    - Try pypdf (if installed).
    - Fallback: empty excerpt.
    """
    try:
        from pypdf import PdfReader  # type: ignore

        reader = PdfReader(str(pdf_path))
        buf: List[str] = []
        for page in reader.pages[:5]:
            try:
                buf.append(page.extract_text() or "")
            except Exception:
                continue
        text = "\n".join(buf).strip()
        if len(text) > max_chars:
            text = text[: max_chars - 3] + "..."
        return {"ok": True, "tool": "pypdf", "excerpt": text}
    except Exception:
        return {"ok": False, "tool": "", "excerpt": ""}


def _resolve_reference_evidence(
    *,
    cited_keys: List[str],
    bib_entries: Dict[str, Dict[str, str]],
    citation_contexts: Dict[str, List[dict]],
    out_dir: Path,
    timeout_s: int,
    unpaywall_email: str,
    fetch_pdf: bool,
    max_pdf_mb: int,
) -> dict:
    """
    Deterministically gather reference-side evidence (title/abstract/pdf excerpt when possible),
    plus proposal-side citation contexts, to enable later AI semantic judgment.
    """
    user_agent = "nsfc-qc/0.1.3 (reference-evidence)"
    evidence_path = out_dir / "reference_evidence.jsonl"
    summary_path = out_dir / "reference_evidence_summary.json"

    total = 0
    resolved_title = 0
    resolved_abstract = 0
    pdf_downloaded = 0
    pdf_text = 0
    failures = 0

    items: List[dict] = []
    for k in cited_keys:
        total += 1
        fields = bib_entries.get(k) or {}
        doi = _guess_doi(fields)
        arxiv_id = _guess_arxiv_id(fields)
        ctxs = citation_contexts.get(k) or []

        cross = _fetch_crossref(doi, timeout_s=timeout_s, user_agent=user_agent) if doi else {"ok": False, "error": "no_doi"}
        ax = _fetch_arxiv(arxiv_id, timeout_s=timeout_s, user_agent=user_agent) if arxiv_id else {"ok": False, "error": "no_arxiv_id"}

        title = (cross.get("title") or "") if cross.get("ok") else ""
        abstract = (cross.get("abstract") or "") if cross.get("ok") else ""
        if not title and ax.get("ok"):
            title = str(ax.get("title") or "").strip()
        if not abstract and ax.get("ok"):
            abstract = str(ax.get("abstract") or "").strip()

        if title:
            resolved_title += 1
        if abstract:
            resolved_abstract += 1

        unpay = _fetch_unpaywall_pdf(doi, email=unpaywall_email, timeout_s=timeout_s, user_agent=user_agent) if doi else {"ok": False, "error": "no_doi"}
        pdf_url = ""
        if ax.get("ok"):
            pdf_url = str(ax.get("pdf_url") or "")
        if not pdf_url and unpay.get("ok"):
            pdf_url = str(unpay.get("pdf_url") or "")
        if not pdf_url:
            # As a last resort, trust bib url if it looks like a PDF.
            u = (fields.get("url") or "").strip()
            if u.lower().endswith(".pdf"):
                pdf_url = u

        pdf_info = {"enabled": bool(fetch_pdf), "ok": False}
        pdf_text_info = {"ok": False, "excerpt": "", "tool": ""}
        if fetch_pdf and pdf_url:
            pdf_dir = out_dir / "refs_pdf"
            pdf_path = pdf_dir / f"{k}.pdf"
            dl = _download_file(
                pdf_url,
                dst=pdf_path,
                timeout_s=timeout_s,
                user_agent=user_agent,
                max_bytes=int(max_pdf_mb) * 1024 * 1024,
            )
            pdf_info = {"enabled": True, "url": pdf_url, "download": dl, "path": str(pdf_path) if dl.get("ok") else ""}
            if dl.get("ok"):
                pdf_downloaded += 1
                pdf_text_info = _extract_pdf_text_excerpt(pdf_path, max_chars=2000)
                if pdf_text_info.get("ok") and pdf_text_info.get("excerpt"):
                    pdf_text += 1

        item = {
            "bibkey": k,
            "proposal_contexts": ctxs[:50],
            "bib_entry": {kk: vv for kk, vv in fields.items() if kk != "__file__"},
            "identifiers": {"doi": doi, "arxiv_id": arxiv_id},
            "resolved": {
                "title": title,
                "abstract": abstract,
                "sources": {
                    "crossref": cross,
                    "arxiv": ax,
                    "unpaywall": unpay,
                },
            },
            "pdf": {
                "url": pdf_url,
                "downloaded": bool(pdf_info.get("download", {}).get("ok")) if isinstance(pdf_info, dict) else False,
                "download_info": pdf_info,
                "text_excerpt": pdf_text_info,
            },
        }

        # Track failures loosely: neither title nor abstract resolved.
        if not title and not abstract:
            failures += 1
        items.append(item)

    evidence_path.write_text(
        "\n".join(json.dumps(it, ensure_ascii=False) for it in items) + ("\n" if items else ""),
        encoding="utf-8",
    )
    summary = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "counts": {
            "cited_keys": total,
            "resolved_title": resolved_title,
            "resolved_abstract": resolved_abstract,
            "pdf_downloaded": pdf_downloaded,
            "pdf_text_excerpt_available": pdf_text,
            "no_title_or_abstract": failures,
        },
        "outputs": {
            "reference_evidence_jsonl": str(evidence_path.name),
            "reference_evidence_summary_json": str(summary_path.name),
        },
        "notes": [
            "This is best-effort evidence collection for later AI semantic checks.",
            "PDF fetching is optional and only attempts arXiv/Unpaywall OA links or bib url ending with .pdf.",
        ],
    }
    _write_json = lambda p, o: p.write_text(json.dumps(o, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    _write_json(summary_path, summary)
    return summary


def _run(cmd: List[str], cwd: Path, log_path: Path) -> int:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as f:
        f.write("\n$ " + " ".join(cmd) + "\n")
        try:
            p = subprocess.run(cmd, cwd=str(cwd), stdout=f, stderr=subprocess.STDOUT)
            return int(p.returncode)
        except FileNotFoundError:
            # Keep precheck robust across environments (TeX toolchain may not exist).
            f.write(f"[nsfc-qc] command not found: {cmd[0]}\n")
            return 127


def _get_pdf_pages(pdf_path: Path) -> Optional[int]:
    # Try pdfinfo (poppler) first, then qpdf.
    for tool in (["pdfinfo"], ["qpdf", "--show-npages"]):
        try:
            if tool[0] == "pdfinfo":
                p = subprocess.run(
                    tool + [str(pdf_path)],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    check=False,
                )
                if p.returncode == 0:
                    for line in p.stdout.splitlines():
                        if line.lower().startswith("pages:"):
                            return int(line.split(":", 1)[1].strip())
            else:
                p = subprocess.run(
                    tool + [str(pdf_path)],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    check=False,
                )
                if p.returncode == 0:
                    return int(p.stdout.strip())
        except Exception:
            continue
    return None


def _compile_isolated(project_root: Path, main_tex_rel: str, out_dir: Path) -> dict:
    compile_dir = out_dir / "compile"
    src = compile_dir / "src"
    build = compile_dir / "build"
    if compile_dir.exists():
        shutil.rmtree(compile_dir)
    compile_dir.mkdir(parents=True, exist_ok=True)

    def ignore(_dir: str, names: List[str]) -> Set[str]:
        # Keep this conservative; only avoid obvious junk.
        bad = {
            ".git",
            ".nsfc-qc",
            ".parallel_vibe",
            "__pycache__",
            ".DS_Store",
            "node_modules",
            ".venv",
            "venv",
            "build",
            "dist",
            "target",
        }
        return {n for n in names if n in bad}

    shutil.copytree(project_root, src, ignore=ignore, dirs_exist_ok=False)
    build.mkdir(parents=True, exist_ok=True)

    main_tex = src / main_tex_rel
    if not main_tex.exists():
        return {"enabled": True, "ok": False, "error": f"main_tex not found in isolated src: {main_tex_rel}"}

    base = main_tex.stem
    log = out_dir / "compile.log"

    missing_tools = [t for t in ("xelatex", "bibtex") if shutil.which(t) is None]
    if missing_tools:
        # Do not crash; record downgrade information.
        try:
            log.write_text(
                "[nsfc-qc] TeX toolchain not available; skip compile step.\n"
                f"missing_tools={missing_tools}\n",
                encoding="utf-8",
            )
        except Exception:
            pass
        return {
            "enabled": True,
            "ok": False,
            "missing_tools": missing_tools,
            "error": "TeX toolchain not available; skip compile step",
            "log": str(log),
        }

    r1 = _run(["xelatex", "-interaction=nonstopmode", "-halt-on-error", f"-output-directory={build}", str(main_tex)], cwd=src, log_path=log)
    # bibtex must run in build dir on the generated .aux
    r2 = _run(["bibtex", base], cwd=build, log_path=log) if r1 == 0 else 1
    r3 = _run(["xelatex", "-interaction=nonstopmode", "-halt-on-error", f"-output-directory={build}", str(main_tex)], cwd=src, log_path=log) if r2 == 0 else 1
    r4 = _run(["xelatex", "-interaction=nonstopmode", "-halt-on-error", f"-output-directory={build}", str(main_tex)], cwd=src, log_path=log) if r3 == 0 else 1

    pdf_path = build / f"{base}.pdf"
    pages = _get_pdf_pages(pdf_path) if pdf_path.exists() else None
    return {
        "enabled": True,
        "ok": (r4 == 0 and pdf_path.exists()),
        "pdf": str(pdf_path) if pdf_path.exists() else "",
        "pages": pages if pages is not None else None,
        "steps_rc": {"xelatex1": r1, "bibtex": r2, "xelatex2": r3, "xelatex3": r4},
        "log": str(log),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--project-root", required=True)
    ap.add_argument("--main-tex", default="main.tex", help="relative to project-root")
    ap.add_argument("--out", required=True, help="output directory (recommended: .nsfc-qc/.../artifacts)")
    ap.add_argument("--compile", action="store_true", help="compile in an isolated copy to estimate PDF page count")
    ap.add_argument("--resolve-refs", action="store_true", help="fetch reference evidence (title/abstract/optional pdf) for AI semantic checks")
    ap.add_argument("--unpaywall-email", default=os.environ.get("UNPAYWALL_EMAIL", ""), help="required by Unpaywall API (or set env UNPAYWALL_EMAIL)")
    ap.add_argument("--fetch-pdf", action="store_true", help="attempt to download OA PDFs (arXiv/Unpaywall/bib url) and extract a short text excerpt")
    ap.add_argument("--max-pdf-mb", type=int, default=5, help="max PDF size to download per reference when --fetch-pdf is enabled")
    ap.add_argument("--timeout-s", type=int, default=20, help="network timeout seconds for reference resolution")
    args = ap.parse_args()

    project_root = Path(args.project_root).expanduser().resolve()
    out_dir = Path(args.out).expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    main_tex = (project_root / args.main_tex).resolve()
    if not main_tex.exists():
        print(f"error: main tex not found: {project_root / args.main_tex}", file=sys.stderr)
        return 2

    tex_files = _find_included_tex_files(main_tex)
    bib_files = _find_bib_files(tex_files, project_root)
    citations = _extract_citations(tex_files, project_root=project_root)
    bib_entries = _parse_bib_keys(bib_files)
    lengths = _rough_text_metrics(tex_files)
    typography = _detect_quote_issues(tex_files, project_root=project_root)
    citation_contexts = _extract_citation_contexts(tex_files, project_root=project_root)

    cited_keys = sorted(citations.keys())
    missing = [k for k in cited_keys if k not in bib_entries]

    # Detect obviously incomplete bib entries (best-effort).
    incomplete: List[str] = []
    for k, f in bib_entries.items():
        # Minimal fields in BibTeX vary by entry type, but these are common.
        if not f.get("title") or not (f.get("author") or f.get("editor")) or not f.get("year"):
            incomplete.append(k)

    compile_info = {"enabled": False}
    if bool(args.compile):
        compile_info = _compile_isolated(project_root, args.main_tex, out_dir)

    reference_evidence = {"enabled": False}
    if bool(args.resolve_refs):
        reference_evidence = _resolve_reference_evidence(
            cited_keys=cited_keys,
            bib_entries=bib_entries,
            citation_contexts=citation_contexts,
            out_dir=out_dir,
            timeout_s=int(args.timeout_s),
            unpaywall_email=str(args.unpaywall_email or "").strip(),
            fetch_pdf=bool(args.fetch_pdf),
            max_pdf_mb=int(args.max_pdf_mb),
        )
        reference_evidence["enabled"] = True

    precheck = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "project_root": str(project_root),
        "main_tex": str(Path(args.main_tex)),
        "tex_files": [
            str(p.relative_to(project_root)) if _is_within(project_root, p) else str(p)
            for p in tex_files
        ],
        "bib_files": [
            str(p.relative_to(project_root)) if _is_within(project_root, p) else str(p)
            for p in bib_files
        ],
        "citation_stats": {
            "unique_citations": len(cited_keys),
            "missing_bibkeys": len(missing),
            "missing_bibkeys_list": missing[:200],
            "incomplete_bib_entries": len(incomplete),
            "incomplete_bibkeys_list": incomplete[:200],
        },
        "lengths": {
            "per_tex_file": {
                str(Path(k).relative_to(project_root)) if str(k).startswith(str(project_root)) else str(k): v
                for k, v in lengths.items()
            }
        },
        "typography": typography,
        "reference_evidence": reference_evidence,
        "compile": compile_info,
    }

    (out_dir / "precheck.json").write_text(json.dumps(precheck, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    # citations index CSV
    with (out_dir / "citations_index.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["bibkey", "status", "occurrences_n", "occurrences_preview"])
        for k in cited_keys:
            occ_list = citations.get(k, [])
            status = "ok" if k in bib_entries else "missing"
            w.writerow([k, status, len(occ_list), " | ".join(occ_list[:5])])

    # section/file lengths CSV (file-level)
    with (out_dir / "tex_lengths.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["path", "cjk_chars", "ascii_words", "non_space_chars"])
        for p in sorted(lengths.keys()):
            rel = str(Path(p).relative_to(project_root)) if str(p).startswith(str(project_root)) else str(p)
            m = lengths[p]
            w.writerow([rel, m["cjk_chars"], m["ascii_words"], m["non_space_chars"]])

    # quote issues CSV (best-effort)
    quote_items = (typography.get("straight_double_quotes_with_cjk") or {}).get("occurrences_preview") or []
    with (out_dir / "quote_issues.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["path", "line", "found", "recommendation", "excerpt"])
        for it in quote_items:
            w.writerow([it.get("path", ""), it.get("line", ""), it.get("found", ""), it.get("recommendation", ""), it.get("excerpt", "")])

    print(str(out_dir))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
