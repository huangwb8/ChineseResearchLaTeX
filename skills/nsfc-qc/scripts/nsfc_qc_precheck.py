#!/usr/bin/env python3
"""
Deterministic, read-only precheck for NSFC LaTeX proposals.

- Extracts citations and checks bibkey existence.
- Produces rough length metrics (per tex file and overall).

All outputs must be written under a user-provided --out directory (recommended inside .nsfc-qc/).
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
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

# Abbreviation convention checks (best-effort heuristics):
# - Detect likely English abbreviations (e.g., "GNN", "LLM", "COVID-19") in LaTeX sources.
# - For the first occurrence of each abbreviation, check whether it is introduced with a definition-like
#   pattern such as "中文全称（English Full Name, ABBR）" or "English Full Name (ABBR)".
# - Later, recommend using ABBR only (avoid repeating "Full Name (ABBR)" multiple times).
ABBR_TOKEN_RE = re.compile(r"\b[A-Z][A-Z0-9]{1,11}\b")
ABBR_HYPHEN_RE = re.compile(r"\b[A-Z]{2,}(?:-[A-Z0-9]{1,})+\b")

# Keep the stoplist conservative to avoid overwhelming false positives.
ABBR_STOPLIST = {
    # Base infra tokens (rarely need "full name + abbreviation" introductions).
    "NSFC",
    "PDF",
    "TEX",
    "LATEX",
    "DOI",
    "URL",
    "HTTP",
    "HTTPS",
    # LaTeX typesetting conventional tokens (avoid noisy "Fig/Tab/Sec" false positives).
    "FIG",
    "TAB",
    "EQ",
    "SEC",
    "REF",
    "APP",
    "APPENDIX",
    # Common academic writing shorthand.
    "ET",
    "AL",
    "IE",
    "EG",
    "VS",
    "CF",
}


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


def _simplify_latex_for_abbrev_scan(line: str) -> str:
    """
    Best-effort conversion from a LaTeX source line to a plain-ish string for abbreviation scanning.
    We intentionally keep this lightweight and dependency-free (false positives are acceptable).
    """
    s = line
    # Remove common math segments to avoid capturing variable names as abbreviations.
    s = re.sub(r"\$[^$]*\$", " ", s)
    s = re.sub(r"\\\([^)]*\\\)", " ", s)
    s = re.sub(r"\\\[[^\]]*\\\]", " ", s)
    # Remove label/ref/cite arguments (bibkey/label often contain ALLCAPS tokens; not abbreviations).
    s = re.sub(
        r"\\(?:label|ref|eqref|pageref)\s*(?:\[[^\]]*\]\s*)?\{[^}]*\}",
        " ",
        s,
    )
    s = re.sub(
        r"\\cite[a-zA-Z*]*\s*(?:\[[^\]]*\]\s*)*\{[^}]*\}",
        " ",
        s,
    )
    # Remove environment names (\begin{...}/\end{...}) to avoid capturing env IDs as abbreviations.
    s = re.sub(r"\\(?:begin|end)\s*\{[^}]*\}\s*(?:\[[^\]]*\])?", " ", s)
    # Remove TeX commands (keep arguments content untouched).
    s = re.sub(r"\\[a-zA-Z@]+\*?", " ", s)
    # Normalize separators
    s = s.replace("{", " ").replace("}", " ")
    s = re.sub(r"\s+", " ", s)
    return s.strip()


def _detect_abbreviation_conventions(tex_files: List[Path], *, project_root: Path) -> dict:
    """
    Detect a common writing convention in NSFC proposals:
    - First occurrence of an important concept: Chinese full name + English full name + English abbreviation.
    - Later occurrences: use the abbreviation only.

    This is heuristic and line-level; it provides "actionable hints" rather than strict enforcement.
    """
    @dataclass(frozen=True)
    class _Occ:
        abbr: str
        seq: int
        path: str
        line: int
        excerpt: str

    occurrences: List[_Occ] = []
    seq = 0
    for p in tex_files:
        try:
            raw = _strip_comments(_read_text(p))
        except Exception:
            continue
        lines = raw.splitlines()
        for i, line in enumerate(lines, start=1):
            scan = _simplify_latex_for_abbrev_scan(line)
            if not scan:
                continue
            tokens = set()
            for m in ABBR_TOKEN_RE.finditer(scan):
                tokens.add(m.group(0))
            for m in ABBR_HYPHEN_RE.finditer(scan):
                tokens.add(m.group(0))
            if not tokens:
                continue

            excerpt = line.strip()
            if len(excerpt) > 140:
                excerpt = excerpt[:137] + "..."
            try:
                rel = str(p.relative_to(project_root))
            except Exception:
                rel = str(p)

            for t in sorted(tokens):
                t2 = t.strip()
                if not t2:
                    continue
                if len(t2) < 2 or len(t2) > 20:
                    continue
                if t2.upper() in ABBR_STOPLIST:
                    continue
                # Filter obvious false positives: pure digits / single-letter / roman numerals-ish.
                if re.fullmatch(r"[IVX]{2,}", t2):
                    continue
                # Filter simple version tokens like "V2" (but keep mixed tokens like "COVID19").
                if re.fullmatch(r"[A-Z]\d{1,4}", t2):
                    continue
                occurrences.append(_Occ(abbr=t2, seq=seq, path=rel, line=i, excerpt=excerpt))
                seq += 1

    # Group by abbreviation.
    by_abbr: Dict[str, List[_Occ]] = {}
    for oc in occurrences:
        by_abbr.setdefault(oc.abbr, []).append(oc)

    # Analyze each abbreviation and create issue items.
    issues: List[dict] = []
    total_abbr = len(by_abbr)

    def _load_context(path_rel: str, line_no: int) -> str:
        # Load 3-line context from the file for better pattern detection.
        try:
            fp = (project_root / path_rel).resolve()
            if not fp.exists():
                return ""
            raw2 = _strip_comments(_read_text(fp))
            ls = raw2.splitlines()
            idx = max(1, min(line_no, len(ls))) - 1
            prev_ln = ls[idx - 1].strip() if idx - 1 >= 0 else ""
            cur_ln = ls[idx].strip() if 0 <= idx < len(ls) else ""
            next_ln = ls[idx + 1].strip() if idx + 1 < len(ls) else ""
            snip = " ".join([x for x in (prev_ln, cur_ln, next_ln) if x]).strip()
            if len(snip) > 260:
                snip = snip[:257] + "..."
            return snip
        except Exception:
            return ""

    for abbr, occs in sorted(by_abbr.items(), key=lambda kv: kv[0]):
        # First occurrence (deterministic by LaTeX include order + file scan order).
        first = min(occs, key=lambda o: o.seq)
        ctx = _load_context(first.path, first.line) or first.excerpt

        paren_re = re.compile(r"[(（]\s*" + re.escape(abbr) + r"\s*[)）]")
        m_paren = paren_re.search(ctx)

        # Count repeated "definition-like" uses across all occurrences (line-level).
        def_total = 0
        for oc in occs:
            sn = _load_context(oc.path, oc.line) or oc.excerpt
            if paren_re.search(sn):
                def_total += 1

        if not m_paren:
            issues.append(
                {
                    "abbr": abbr,
                    "issue_kind": "bare_first_use",
                    "severity": "P1",
                    "path": first.path,
                    "line": first.line,
                    "excerpt": first.excerpt,
                    "context": ctx,
                    "recommendation": f"首次出现建议写成：中文全称（English Full Name, {abbr}）；后文仅用 {abbr}。",
                }
            )
        else:
            before = ctx[: m_paren.start()]
            # Heuristic: English full name exists if we see >=2 English-like words before (ABBR).
            eng_words = re.findall(r"[A-Za-z]{2,}(?:[-/][A-Za-z]{2,})?", before)
            has_english_full = len(eng_words) >= 2
            has_chinese_full = bool(re.search(r"[\u4e00-\u9fff]", before))

            if not has_english_full:
                issues.append(
                    {
                        "abbr": abbr,
                        "issue_kind": "missing_english_full",
                        "severity": "P1",
                        "path": first.path,
                        "line": first.line,
                        "excerpt": first.excerpt,
                        "context": ctx,
                        "recommendation": f"首次出现建议补全英文全称：中文全称（English Full Name, {abbr}）；后文仅用 {abbr}。",
                    }
                )
            elif not has_chinese_full:
                issues.append(
                    {
                        "abbr": abbr,
                        "issue_kind": "missing_chinese_full",
                        "severity": "P2",
                        "path": first.path,
                        "line": first.line,
                        "excerpt": first.excerpt,
                        "context": ctx,
                        "recommendation": f"首次出现建议同时给出中文全称：中文全称（English Full Name, {abbr}）；后文仅用 {abbr}。",
                    }
                )

        # Repeated definition-like patterns are often unnecessary after the first definition.
        if def_total >= 2:
            issues.append(
                {
                    "abbr": abbr,
                    "issue_kind": "repeated_expansion",
                    "severity": "P2",
                    "path": first.path,
                    "line": first.line,
                    "excerpt": first.excerpt,
                    "context": ctx,
                    "recommendation": f"已检测到多次出现类似“...({abbr})”的定义式写法（>=2 次）。建议首次定义后，后文尽量只用 {abbr}，避免重复展开。",
                }
            )

    # Keep preview bounded.
    preview = issues[:200]
    counts = {"P0": 0, "P1": 0, "P2": 0}
    for it in issues:
        sev = str(it.get("severity") or "")
        if sev in counts:
            counts[sev] += 1

    return {
        "summary": {
            "abbreviations_detected": total_abbr,
            "issues": len(issues),
            "issues_by_severity": counts,
        },
        "issues_preview": preview,
        "note": "Heuristic check: detect likely English abbreviations and whether the first occurrence is introduced as '中文全称（English Full Name, ABBR）' or 'English Full Name (ABBR)'. False positives/negatives are possible; treat as writing guidance.",
    }


def _detect_terminology_consistency(tex_files: List[Path], *, project_root: Path) -> dict:
    """
    Detect potential English terminology inconsistencies (heuristic, read-only):
    1. Capitalization variants: "deep learning" vs "Deep Learning"
    2. Hyphenation variants: "deep-learning" vs "deep learning"

    Normalizes each term to lowercase+no-hyphens, then flags keys with multiple surface forms.
    False positives are possible; treat results as writing guidance only.
    """
    HYPHEN_TERM_RE = re.compile(r"\b([A-Za-z]{2,}(?:-[A-Za-z]{2,}){1,3})\b")
    TITLE_PHRASE_RE = re.compile(r"\b([A-Z][a-z]{2,}(?:\s+[A-Z][a-z]{2,}){1,3})\b")

    # normalized_key -> {surface_form -> [(path, line)]}
    term_map: Dict[str, Dict[str, List[Tuple[str, int]]]] = {}

    for p in tex_files:
        try:
            raw = _strip_comments(_read_text(p))
        except Exception:
            continue
        lines = raw.splitlines()
        for i, line in enumerate(lines, start=1):
            scan = _simplify_latex_for_abbrev_scan(line)
            if not scan:
                continue
            try:
                rel = str(p.relative_to(project_root))
            except Exception:
                rel = str(p)

            for m in HYPHEN_TERM_RE.finditer(scan):
                term = m.group(1)
                if term.upper() == term:  # skip all-caps abbreviations
                    continue
                key = term.lower().replace("-", " ")
                if len(key.split()) < 2:
                    continue
                term_map.setdefault(key, {}).setdefault(term, []).append((rel, i))

            for m in TITLE_PHRASE_RE.finditer(scan):
                term = m.group(1)
                key = term.lower()
                term_map.setdefault(key, {}).setdefault(term, []).append((rel, i))

    issues: List[dict] = []
    for key, surface_map in sorted(term_map.items()):
        if len(surface_map) <= 1:
            continue
        variants = [
            {
                "surface": surface,
                "count": len(locs),
                "first_occurrence": {"path": locs[0][0], "line": locs[0][1]},
            }
            for surface, locs in sorted(surface_map.items(), key=lambda kv: -len(kv[1]))
        ]
        canonical = variants[0]["surface"]
        issues.append(
            {
                "normalized_key": key,
                "severity": "P2",
                "issue_kind": "term_variant",
                "variants": variants,
                "recommendation": f"建议统一使用最常见形式：\"{canonical}\"，检查其他变体是否为笔误或不一致。",
            }
        )

    counts = {"P0": 0, "P1": 0, "P2": len(issues)}
    return {
        "summary": {
            "unique_normalized_terms": len(term_map),
            "inconsistent_terms": len(issues),
            "issues_by_severity": counts,
        },
        "issues_preview": issues[:100],
        "note": (
            "Heuristic check for English term capitalization/hyphenation inconsistencies. "
            "False positives possible; treat as writing guidance."
        ),
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
    user_agent = "nsfc-qc/0.1.5 (reference-evidence)"
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


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--project-root", required=True)
    ap.add_argument("--main-tex", default="main.tex", help="relative to project-root")
    ap.add_argument("--out", required=True, help="output directory (recommended: .nsfc-qc/.../artifacts)")
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
    abbreviation_conventions = _detect_abbreviation_conventions(tex_files, project_root=project_root)
    terminology_consistency = _detect_terminology_consistency(tex_files, project_root=project_root)
    citation_contexts = _extract_citation_contexts(tex_files, project_root=project_root)

    cited_keys = sorted(citations.keys())
    missing = [k for k in cited_keys if k not in bib_entries]

    # Detect obviously incomplete bib entries (best-effort).
    incomplete: List[str] = []
    for k, f in bib_entries.items():
        # Minimal fields in BibTeX vary by entry type, but these are common.
        if not f.get("title") or not (f.get("author") or f.get("editor")) or not f.get("year"):
            incomplete.append(k)

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
        "abbreviation_conventions": abbreviation_conventions,
        "terminology_consistency": terminology_consistency,
        "reference_evidence": reference_evidence,
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

    # abbreviation conventions CSV (best-effort)
    abbr_items = (abbreviation_conventions.get("issues_preview") or []) if isinstance(abbreviation_conventions, dict) else []
    with (out_dir / "abbreviation_issues.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["severity", "issue_kind", "abbr", "path", "line", "recommendation", "excerpt", "context"])
        for it in abbr_items:
            w.writerow(
                [
                    it.get("severity", ""),
                    it.get("issue_kind", ""),
                    it.get("abbr", ""),
                    it.get("path", ""),
                    it.get("line", ""),
                    it.get("recommendation", ""),
                    it.get("excerpt", ""),
                    it.get("context", ""),
                ]
            )

    # abbreviation conventions JSON summary (for AI-friendly consumption)
    abbr_summary = {}
    if isinstance(abbreviation_conventions, dict):
        abbr_summary = abbreviation_conventions.get("summary") or {}
    issues_by_sev = {}
    if isinstance(abbr_summary, dict):
        issues_by_sev = abbr_summary.get("issues_by_severity") or {}
    total_abbr_detected = int((abbr_summary.get("abbreviations_detected") or 0) if isinstance(abbr_summary, dict) else 0)
    issues_count = {
        "P0": int((issues_by_sev.get("P0") or 0) if isinstance(issues_by_sev, dict) else 0),
        "P1": int((issues_by_sev.get("P1") or 0) if isinstance(issues_by_sev, dict) else 0),
        "P2": int((issues_by_sev.get("P2") or 0) if isinstance(issues_by_sev, dict) else 0),
    }
    top_issues = []
    for it in abbr_items[:20]:
        top_issues.append(
            {
                "abbr": it.get("abbr", ""),
                "issue_kind": it.get("issue_kind", ""),
                "severity": it.get("severity", ""),
                "path": it.get("path", ""),
                "line": it.get("line", ""),
                "recommendation": it.get("recommendation", ""),
            }
        )
    (out_dir / "abbreviation_issues_summary.json").write_text(
        json.dumps(
            {
                "total_abbreviations_detected": total_abbr_detected,
                "issues_count": issues_count,
                "top_issues": top_issues,
                "note": "Heuristic only. AI threads should verify each item and filter false positives.",
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    # terminology consistency CSV
    term_issues = (terminology_consistency.get("issues_preview") or []) if isinstance(terminology_consistency, dict) else []
    with (out_dir / "terminology_issues.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["severity", "issue_kind", "normalized_key", "variants_count", "canonical", "path", "line"])
        for it in term_issues:
            variants = it.get("variants") or []
            canonical = variants[0].get("surface", "") if variants else ""
            first = variants[0].get("first_occurrence", {}) if variants else {}
            w.writerow(
                [
                    it.get("severity", ""),
                    it.get("issue_kind", ""),
                    it.get("normalized_key", ""),
                    len(variants),
                    canonical,
                    first.get("path", ""),
                    first.get("line", ""),
                ]
            )

    # terminology consistency JSON summary
    term_summary = (terminology_consistency.get("summary") or {}) if isinstance(terminology_consistency, dict) else {}
    term_issues_count = (term_summary.get("issues_by_severity") or {}) if isinstance(term_summary, dict) else {}
    top_term_issues = []
    for it in term_issues[:20]:
        variants = it.get("variants") or []
        top_term_issues.append(
            {
                "normalized_key": it.get("normalized_key", ""),
                "severity": it.get("severity", ""),
                "variants": [v.get("surface", "") for v in variants],
                "recommendation": it.get("recommendation", ""),
            }
        )
    (out_dir / "terminology_issues_summary.json").write_text(
        json.dumps(
            {
                "total_normalized_terms": int((term_summary.get("unique_normalized_terms") or 0) if isinstance(term_summary, dict) else 0),
                "inconsistent_terms": int((term_summary.get("inconsistent_terms") or 0) if isinstance(term_summary, dict) else 0),
                "issues_count": {
                    "P0": int((term_issues_count.get("P0") or 0) if isinstance(term_issues_count, dict) else 0),
                    "P1": int((term_issues_count.get("P1") or 0) if isinstance(term_issues_count, dict) else 0),
                    "P2": int((term_issues_count.get("P2") or 0) if isinstance(term_issues_count, dict) else 0),
                },
                "top_issues": top_term_issues,
                "note": "Heuristic only. AI threads should verify each item and filter false positives.",
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    print(str(out_dir))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
