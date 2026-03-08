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
import time
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
ABBR_CANDIDATE_RE = re.compile(r"\b[A-Za-z][A-Za-z0-9-]{1,24}\b")

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


def _resolve_main_tex(project_root: Path, requested: str) -> Optional[Path]:
    requested_path = (project_root / requested).resolve()
    if requested_path.exists() and requested_path.is_file():
        return requested_path

    candidates = sorted(project_root.rglob("*.tex"))
    if not candidates:
        return None

    def _score(path: Path) -> int:
        score = 0
        rel_parts = path.relative_to(project_root).parts
        name = path.name.lower()
        try:
            text = _read_text(path)
        except Exception:
            text = ""
        if "\\documentclass" in text:
            score += 6
        if "\\begin{document}" in text:
            score += 4
        if path.parent == project_root:
            score += 2
        if name in {"main.tex", "proposal.tex", "application.tex"}:
            score += 2
        if any(part in {"extratex", "template", "figures", "qc"} for part in map(str.lower, rel_parts[:-1])):
            score -= 3
        if name.startswith("@"):
            score -= 2
        return score

    scored = sorted((( _score(path), path) for path in candidates), key=lambda item: (item[0], str(item[1])), reverse=True)
    best_score, best_path = scored[0]
    if best_score < 1:
        return None
    return best_path


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
    s = _mask_latex_for_abbrev_scan(line)
    s = re.sub(r"\s+", " ", s)
    return s.strip()


def _mask_latex_for_abbrev_scan(line: str) -> str:
    """
    Replace LaTeX-only regions with spaces while preserving the original string length.
    This lets us keep token column order roughly aligned with the source line.
    """

    def _mask(pattern: str, text: str) -> str:
        return re.sub(pattern, lambda m: " " * (m.end() - m.start()), text)

    s = line
    s = _mask(r"\$[^$]*\$", s)
    s = _mask(r"\\\([^)]*\\\)", s)
    s = _mask(r"\\\[[^\]]*\\\]", s)
    s = _mask(r"\\(?:label|ref|eqref|pageref)\s*(?:\[[^\]]*\]\s*)?\{[^}]*\}", s)
    s = _mask(r"\\cite[a-zA-Z*]*\s*(?:\[[^\]]*\]\s*)*\{[^}]*\}", s)
    s = _mask(r"\\(?:begin|end)\s*\{[^}]*\}\s*(?:\[[^\]]*\])?", s)
    s = _mask(r"\\[a-zA-Z@]+\*?", s)
    s = s.replace("{", " ").replace("}", " ")
    return s


@dataclass(frozen=True)
class _RenderEvent:
    seq: int
    path: str
    line: int
    column: int
    text: str
    source_stack: Tuple[str, ...]


@dataclass(frozen=True)
class _AbbrOccurrence:
    abbr: str
    seq: int
    path: str
    line: int
    column: int
    excerpt: str
    event_index: int


@dataclass(frozen=True)
class _AbbrDefinition:
    abbr: str
    seq: int
    path: str
    line: int
    column: int
    english_full: str
    chinese_full: str
    matched_text: str
    context: str


def _event_excerpt(text: str, *, limit: int = 140) -> str:
    excerpt = text.strip()
    if len(excerpt) > limit:
        return excerpt[: limit - 3] + "..."
    return excerpt


def _iter_render_events(main_tex: Path, *, project_root: Path) -> List[_RenderEvent]:
    events: List[_RenderEvent] = []
    seq = 1

    def _rel_path(p: Path) -> str:
        try:
            return str(p.relative_to(project_root))
        except Exception:
            return str(p)

    def _emit(text: str, *, path: Path, line: int, column: int, stack: Tuple[str, ...]) -> None:
        nonlocal seq
        if not text.strip():
            return
        events.append(
            _RenderEvent(
                seq=seq,
                path=_rel_path(path),
                line=line,
                column=max(1, column),
                text=text,
                source_stack=stack,
            )
        )
        seq += 1

    def _walk(path: Path, *, stack: Tuple[str, ...], active: Tuple[Path, ...]) -> None:
        rel = _rel_path(path)
        try:
            lines = _read_text(path).splitlines()
        except Exception:
            return

        current_stack = stack + (rel,)
        for line_no, raw_line in enumerate(lines, start=1):
            line = _strip_comments(raw_line)
            if not line.strip():
                continue

            cursor = 0
            for match in TEX_INPUT_RE.finditer(line):
                prefix = line[cursor: match.start()]
                if prefix.strip():
                    _emit(prefix, path=path, line=line_no, column=cursor + 1, stack=current_stack)

                inc = (match.group(2) or "").strip()
                inc_path = _resolve_tex_path(path.parent, inc) or _resolve_tex_path(main_tex.parent, inc)
                if inc_path and inc_path.resolve() not in active:
                    _walk(inc_path, stack=current_stack, active=active + (inc_path.resolve(),))
                cursor = match.end()

            suffix = line[cursor:]
            if suffix.strip():
                _emit(suffix, path=path, line=line_no, column=cursor + 1, stack=current_stack)

    _walk(main_tex, stack=(), active=(main_tex.resolve(),))
    return events


def _looks_like_abbreviation(token: str) -> bool:
    token = token.strip()
    if len(token) < 2 or len(token) > 24:
        return False
    if token.upper() in ABBR_STOPLIST:
        return False
    if re.fullmatch(r"[IVXivx]{2,}", token):
        return False
    if re.fullmatch(r"[A-Z]\d{1,4}", token):
        return False
    if re.fullmatch(r"[A-Z][a-z]+(?:-[A-Z][a-z]+)+", token):
        return False

    upper_count = sum(1 for ch in token if ch.isupper())
    lower_count = sum(1 for ch in token if ch.islower())
    digit_count = sum(1 for ch in token if ch.isdigit())
    if token.isupper() and upper_count >= 2:
        return True
    if upper_count >= 2 and (lower_count > 0 or digit_count > 0 or "-" in token):
        return True
    return False


def _extract_abbreviation_tokens(text: str) -> List[Tuple[str, int]]:
    tokens: List[Tuple[str, int]] = []
    seen: Set[Tuple[str, int]] = set()
    for match in ABBR_CANDIDATE_RE.finditer(text):
        token = match.group(0)
        if not _looks_like_abbreviation(token):
            continue
        item = (token, match.start())
        if item in seen:
            continue
        seen.add(item)
        tokens.append(item)
    return tokens


def _normalize_english_full(text: str) -> str:
    text = re.sub(r"[^A-Za-z0-9]+", " ", str(text or "").lower()).strip()
    return re.sub(r"\s+", " ", text)


def _normalize_chinese_full(text: str) -> str:
    return re.sub(r"[\s，,。；;：:“”‘’'\-()（）/]+", "", str(text or "").strip())


def _extract_definition_components(prefix: str, paren_content: str, abbr: str) -> Tuple[str, str]:
    english_full = ""
    chinese_full = ""

    inner = _simplify_latex_for_abbrev_scan(paren_content).strip()
    inner = re.sub(r"\b" + re.escape(abbr) + r"\b", " ", inner)
    inner = re.sub(r"[，,;；:：\s]+", " ", inner).strip()
    eng_match = re.search(r"([A-Za-z][A-Za-z0-9/+-]*(?:\s+[A-Za-z][A-Za-z0-9/+-]*){1,7})$", inner)
    if eng_match:
        english_full = eng_match.group(1).strip(" ,;:：，；")

    tail = _simplify_latex_for_abbrev_scan(prefix)[-120:].strip()
    tail = re.sub(r"[，,。；;：:、\s]+$", "", tail)
    if tail:
        parts = re.split(r"[，,。；;：:]", tail)
        tail = parts[-1].strip() if parts else tail
    tail = re.sub(r"^(?:为保持记号统一，?)", "", tail)
    tail = re.sub(r".*?(?:写作|称为|称作|定义为|记作|表示为|简称为|简称|即)", "", tail)
    zh_match = re.search(r"([\u4e00-\u9fff][\u4e00-\u9fff0-9·\-]{1,24})$", tail)
    if zh_match:
        chinese_full = zh_match.group(1).strip()

    return english_full, chinese_full


def _build_occurrence_context(events: List[_RenderEvent], event_index: int) -> Tuple[str, int]:
    start = max(0, event_index - 1)
    end = min(len(events), event_index + 2)
    parts: List[str] = []
    current_offset = 0
    for idx in range(start, end):
        if parts:
            parts.append("\n")
        if idx == event_index:
            current_offset = sum(len(part) for part in parts)
        parts.append(events[idx].text)
    context = "".join(parts).strip()
    if len(context) > 320:
        context = context[:317] + "..."
    return context, current_offset


def _extract_definition_for_occurrence(
    *,
    events: List[_RenderEvent],
    occurrence: _AbbrOccurrence,
) -> Optional[_AbbrDefinition]:
    context, current_offset = _build_occurrence_context(events, occurrence.event_index)
    if not context:
        return None

    occurrence_abs = current_offset + max(0, occurrence.column - 1)
    paren_re = re.compile(r"[(（][^()（）\n]{0,180}" + re.escape(occurrence.abbr) + r"[^()（）\n]{0,60}[)）]")

    best_match = None
    best_distance = None
    best_abbr_abs = None
    for match in paren_re.finditer(context):
        rel_pos = match.group(0).find(occurrence.abbr)
        if rel_pos < 0:
            continue
        abbr_abs = match.start() + rel_pos
        distance = abs(abbr_abs - occurrence_abs)
        if best_distance is None or distance < best_distance:
            best_match = match
            best_distance = distance
            best_abbr_abs = abbr_abs

    if best_match is None or best_distance is None or best_abbr_abs is None or best_distance > 6:
        return None

    prefix = context[max(0, best_match.start() - 160): best_match.start()]
    inner = best_match.group(0)[1:-1].strip()
    english_full, chinese_full = _extract_definition_components(prefix, inner, occurrence.abbr)
    return _AbbrDefinition(
        abbr=occurrence.abbr,
        seq=occurrence.seq,
        path=occurrence.path,
        line=occurrence.line,
        column=occurrence.column,
        english_full=english_full,
        chinese_full=chinese_full,
        matched_text=best_match.group(0),
        context=context,
    )


def _definition_to_dict(item: _AbbrDefinition) -> dict:
    return {
        "abbr": item.abbr,
        "seq": item.seq,
        "path": item.path,
        "line": item.line,
        "column": item.column,
        "english_full": item.english_full,
        "chinese_full": item.chinese_full,
        "english_full_normalized": _normalize_english_full(item.english_full),
        "chinese_full_normalized": _normalize_chinese_full(item.chinese_full),
        "matched_text": item.matched_text,
        "context": item.context,
    }


def _occurrence_to_dict(item: _AbbrOccurrence) -> dict:
    return {
        "abbr": item.abbr,
        "seq": item.seq,
        "path": item.path,
        "line": item.line,
        "column": item.column,
        "excerpt": item.excerpt,
    }


def _detect_abbreviation_conventions(*, main_tex: Path, project_root: Path) -> dict:
    """
    Build an abbreviation registry from the actual render order of the LaTeX project.

    Goals:
    - first occurrence follows main.tex render order instead of per-file scan order;
    - same-line tokens preserve source order instead of set/sorted order;
    - definition uniqueness is judged globally (English full name / Chinese explanation);
    - repeated same definition and late definition are separated from outright conflicts.
    """
    render_events = _iter_render_events(main_tex, project_root=project_root)

    occurrences: List[_AbbrOccurrence] = []
    by_abbr: Dict[str, List[_AbbrOccurrence]] = {}
    for event_index, event in enumerate(render_events):
        masked = _mask_latex_for_abbrev_scan(event.text)
        for token, offset in _extract_abbreviation_tokens(masked):
            occ = _AbbrOccurrence(
                abbr=token,
                seq=event.seq,
                path=event.path,
                line=event.line,
                column=event.column + offset,
                excerpt=_event_excerpt(event.text),
                event_index=event_index,
            )
            occurrences.append(occ)
            by_abbr.setdefault(token, []).append(occ)

    definition_map: Dict[str, List[_AbbrDefinition]] = {}
    for occ in occurrences:
        definition = _extract_definition_for_occurrence(events=render_events, occurrence=occ)
        if not definition:
            continue
        items = definition_map.setdefault(occ.abbr, [])
        dedupe_key = (
            definition.seq,
            definition.path,
            definition.line,
            definition.column,
            _normalize_english_full(definition.english_full),
            _normalize_chinese_full(definition.chinese_full),
        )
        if any(
            (
                item.seq,
                item.path,
                item.line,
                item.column,
                _normalize_english_full(item.english_full),
                _normalize_chinese_full(item.chinese_full),
            )
            == dedupe_key
            for item in items
        ):
            continue
        items.append(definition)

    issues: List[dict] = []
    registry: List[dict] = []

    def _add_issue(
        *,
        abbr: str,
        issue_kind: str,
        severity: str,
        occurrence: _AbbrOccurrence,
        recommendation: str,
        context: str,
        english_full: str = "",
        chinese_full: str = "",
        details: str = "",
    ) -> None:
        issues.append(
            {
                "abbr": abbr,
                "issue_kind": issue_kind,
                "severity": severity,
                "path": occurrence.path,
                "line": occurrence.line,
                "column": occurrence.column,
                "excerpt": occurrence.excerpt,
                "context": context,
                "english_full": english_full,
                "chinese_full": chinese_full,
                "details": details,
                "recommendation": recommendation,
            }
        )

    for abbr, occs in sorted(by_abbr.items(), key=lambda kv: min(item.seq for item in kv[1])):
        ordered_occs = sorted(occs, key=lambda item: (item.seq, item.column))
        ordered_defs = sorted(definition_map.get(abbr, []), key=lambda item: (item.seq, item.column))
        first_occ = ordered_occs[0]
        first_context, _ = _build_occurrence_context(render_events, first_occ.event_index)
        first_def = next((item for item in ordered_defs if item.seq == first_occ.seq), None)

        english_variants: Dict[str, _AbbrDefinition] = {}
        chinese_variants: Dict[str, _AbbrDefinition] = {}
        pair_occurrences: Dict[Tuple[str, str], List[_AbbrDefinition]] = {}
        for item in ordered_defs:
            eng_norm = _normalize_english_full(item.english_full)
            zh_norm = _normalize_chinese_full(item.chinese_full)
            if eng_norm:
                english_variants.setdefault(eng_norm, item)
            if zh_norm:
                chinese_variants.setdefault(zh_norm, item)
            pair_occurrences.setdefault((eng_norm, zh_norm), []).append(item)

        first_use_status = "defined"
        if first_def is None:
            if ordered_defs:
                first_use_status = "late_definition"
                later = ordered_defs[0]
                _add_issue(
                    abbr=abbr,
                    issue_kind="late_definition",
                    severity="P1",
                    occurrence=first_occ,
                    context=first_context or first_occ.excerpt,
                    english_full=later.english_full,
                    chinese_full=later.chinese_full,
                    details=f"首次定义滞后；首次检测到定义位于 {later.path}:{later.line}",
                    recommendation=(
                        f"{abbr} 首次出现早于定义。建议把首次定义提前到第一次出现处，写成“中文全称（English Full Name, {abbr}）”。"
                    ),
                )
            else:
                first_use_status = "bare_first_use"
                _add_issue(
                    abbr=abbr,
                    issue_kind="bare_first_use",
                    severity="P1",
                    occurrence=first_occ,
                    context=first_context or first_occ.excerpt,
                    recommendation=f"首次出现建议写成：中文全称（English Full Name, {abbr}）；后文再仅用 {abbr}。",
                )
        else:
            if not first_def.english_full:
                _add_issue(
                    abbr=abbr,
                    issue_kind="missing_english_full",
                    severity="P1",
                    occurrence=first_occ,
                    context=first_def.context or first_occ.excerpt,
                    chinese_full=first_def.chinese_full,
                    recommendation=f"首次定义建议补全英文全称：中文全称（English Full Name, {abbr}）；后文仅用 {abbr}。",
                )
            elif not first_def.chinese_full:
                _add_issue(
                    abbr=abbr,
                    issue_kind="missing_chinese_full",
                    severity="P2",
                    occurrence=first_occ,
                    context=first_def.context or first_occ.excerpt,
                    english_full=first_def.english_full,
                    recommendation=f"首次定义建议同时给出中文全称：中文全称（{first_def.english_full}, {abbr}）。",
                )

        if len(english_variants) > 1:
            conflict = list(english_variants.values())[1]
            variants_preview = " / ".join(sorted(item.english_full for item in english_variants.values() if item.english_full))
            target_occ = next((item for item in ordered_occs if item.seq == conflict.seq), first_occ)
            _add_issue(
                abbr=abbr,
                issue_kind="conflicting_english_full_name",
                severity="P1",
                occurrence=target_occ,
                context=conflict.context or target_occ.excerpt,
                english_full=conflict.english_full,
                details=f"全文出现多个英文全称：{variants_preview}",
                recommendation=f"同一缩写 {abbr} 在全文中应统一对应一个英文全称；建议保留首次定义并统一后文写法。",
            )

        if len(chinese_variants) > 1:
            conflict = list(chinese_variants.values())[1]
            variants_preview = " / ".join(sorted(item.chinese_full for item in chinese_variants.values() if item.chinese_full))
            target_occ = next((item for item in ordered_occs if item.seq == conflict.seq), first_occ)
            _add_issue(
                abbr=abbr,
                issue_kind="conflicting_chinese_full",
                severity="P1",
                occurrence=target_occ,
                context=conflict.context or target_occ.excerpt,
                chinese_full=conflict.chinese_full,
                details=f"全文出现多个中文解释：{variants_preview}",
                recommendation=f"同一缩写 {abbr} 在全文中应统一对应一个中文解释；建议以首次定义为准统一修订。",
            )

        repeated_defs = [items for pair, items in pair_occurrences.items() if (pair[0] or pair[1]) and len(items) >= 2]
        if repeated_defs:
            second_def = repeated_defs[0][1]
            target_occ = next((item for item in ordered_occs if item.seq == second_def.seq), first_occ)
            _add_issue(
                abbr=abbr,
                issue_kind="repeated_same_definition",
                severity="P2",
                occurrence=target_occ,
                context=second_def.context or target_occ.excerpt,
                english_full=second_def.english_full,
                chinese_full=second_def.chinese_full,
                details=f"同一定义重复出现 {len(repeated_defs[0])} 次",
                recommendation=f"{abbr} 已重复以相同定义展开。建议保留首次定义，后文尽量直接使用 {abbr}。",
            )

        english_status = "missing"
        if len(english_variants) == 1:
            english_status = "unique"
        elif len(english_variants) > 1:
            english_status = "conflicting"

        chinese_status = "missing"
        if len(chinese_variants) == 1 and all(item.chinese_full for item in ordered_defs):
            chinese_status = "unique"
        elif len(chinese_variants) > 1:
            chinese_status = "conflicting"
        elif len(chinese_variants) == 1:
            chinese_status = "partial_missing"

        registry.append(
            {
                "abbr": abbr,
                "first_occurrence": _occurrence_to_dict(first_occ),
                "occurrences": [_occurrence_to_dict(item) for item in ordered_occs],
                "definitions": [_definition_to_dict(item) for item in ordered_defs],
                "status": {
                    "first_use": first_use_status,
                    "english_full_name": english_status,
                    "chinese_full": chinese_status,
                    "redefinition": "repeated_same_definition" if repeated_defs else "none",
                },
            }
        )

    counts = {"P0": 0, "P1": 0, "P2": 0}
    issue_kinds: Dict[str, int] = {}
    for item in issues:
        sev = str(item.get("severity") or "")
        if sev in counts:
            counts[sev] += 1
        kind = str(item.get("issue_kind") or "")
        if kind:
            issue_kinds[kind] = issue_kinds.get(kind, 0) + 1

    render_stream_payload = [
        {
            "seq": item.seq,
            "path": item.path,
            "line": item.line,
            "column": item.column,
            "text": item.text,
            "source_stack": list(item.source_stack),
        }
        for item in render_events
    ]

    return {
        "summary": {
            "abbreviations_detected": len(by_abbr),
            "occurrences_detected": len(occurrences),
            "abbreviations_with_definitions": sum(1 for item in registry if item.get("definitions")),
            "issues": len(issues),
            "issues_by_severity": counts,
            "issues_by_kind": issue_kinds,
        },
        "issues_preview": issues[:200],
        "registry_preview": registry[:50],
        "registry": registry,
        "render_stream": render_stream_payload,
        "note": "Render-order heuristic: abbreviations are checked on the actual main.tex expansion order, then aggregated into a whole-document registry for late definition / conflict / repeated-definition checks.",
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


def _check_url_accessible(url: str, *, timeout_s: int, user_agent: str) -> dict:
    """
    Check if a URL is accessible (HTTP HEAD request).
    Returns: {"ok": bool, "status_code": int, "error": str}
    """
    if not url or not url.strip():
        return {"ok": False, "status_code": 0, "error": "empty_url"}

    url = url.strip()
    # Basic URL validation
    if not (url.startswith("http://") or url.startswith("https://")):
        return {"ok": False, "status_code": 0, "error": "invalid_scheme"}

    try:
        req = urllib.request.Request(url, headers={"User-Agent": user_agent}, method="HEAD")
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            return {"ok": True, "status_code": resp.status, "error": ""}
    except urllib.error.HTTPError as e:
        return {"ok": False, "status_code": e.code, "error": f"http_{e.code}"}
    except urllib.error.URLError as e:
        return {"ok": False, "status_code": 0, "error": f"url_error: {type(e.reason).__name__}"}
    except Exception as e:
        return {"ok": False, "status_code": 0, "error": f"exception: {type(e).__name__}"}


def _normalize_title_for_comparison(title: str) -> str:
    """
    Normalize title for fuzzy comparison: lowercase, remove punctuation, collapse whitespace.
    """
    if not title:
        return ""
    # Lowercase
    t = title.lower()
    # Remove common punctuation
    t = re.sub(r"[^\w\s]", " ", t)
    # Collapse whitespace
    t = re.sub(r"\s+", " ", t).strip()
    return t


def _compare_titles(bib_title: str, api_title: str) -> dict:
    """
    Compare bib title with API-resolved title.
    Returns: {"match": str, "similarity": float, "note": str}
    match: "exact" | "fuzzy" | "mismatch" | "missing"
    """
    if not bib_title and not api_title:
        return {"match": "missing", "similarity": 0.0, "note": "both titles missing"}
    if not bib_title:
        return {"match": "missing", "similarity": 0.0, "note": "bib title missing"}
    if not api_title:
        return {"match": "missing", "similarity": 0.0, "note": "api title missing"}

    # Exact match (case-insensitive)
    if bib_title.strip().lower() == api_title.strip().lower():
        return {"match": "exact", "similarity": 1.0, "note": ""}

    # Fuzzy match (normalized)
    norm_bib = _normalize_title_for_comparison(bib_title)
    norm_api = _normalize_title_for_comparison(api_title)

    if norm_bib == norm_api:
        return {"match": "fuzzy", "similarity": 0.95, "note": "normalized match"}

    # Simple word-based similarity (Jaccard)
    words_bib = set(norm_bib.split())
    words_api = set(norm_api.split())
    if not words_bib or not words_api:
        return {"match": "mismatch", "similarity": 0.0, "note": "empty after normalization"}

    intersection = len(words_bib & words_api)
    union = len(words_bib | words_api)
    similarity = intersection / union if union > 0 else 0.0

    if similarity >= 0.8:
        return {"match": "fuzzy", "similarity": similarity, "note": "high word overlap"}
    elif similarity >= 0.5:
        return {"match": "fuzzy", "similarity": similarity, "note": "moderate word overlap"}
    else:
        return {"match": "mismatch", "similarity": similarity, "note": "low word overlap"}


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
    max_concurrent: int,
) -> dict:
    """
    Deterministically gather reference-side evidence (title/abstract/pdf excerpt when possible),
    plus proposal-side citation contexts, to enable later AI semantic judgment.

    Now includes:
    - URL accessibility check for bib url field
    - Automatic metadata comparison (bib title vs API title)
    - Concurrency control (max_concurrent requests at a time)
    """
    user_agent = "nsfc-qc/1.0.0 (reference-evidence)"
    evidence_path = out_dir / "reference_evidence.jsonl"
    summary_path = out_dir / "reference_evidence_summary.json"

    total = 0
    resolved_title = 0
    resolved_abstract = 0
    pdf_downloaded = 0
    pdf_text = 0
    failures = 0
    url_checked = 0
    url_accessible = 0
    title_match_exact = 0
    title_match_fuzzy = 0
    title_mismatch = 0

    items: List[dict] = []

    # Process in batches to control concurrency
    batch_size = max(1, min(max_concurrent, 10))  # Clamp to [1, 10]

    for batch_start in range(0, len(cited_keys), batch_size):
        batch_keys = cited_keys[batch_start:batch_start + batch_size]

        for k in batch_keys:
            total += 1
            fields = bib_entries.get(k) or {}
            doi = _guess_doi(fields)
            arxiv_id = _guess_arxiv_id(fields)
            ctxs = citation_contexts.get(k) or []

            # Fetch metadata from APIs
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

            # Check bib URL accessibility
            bib_url = (fields.get("url") or "").strip()
            url_check_result = {"checked": False, "ok": False, "status_code": 0, "error": ""}
            if bib_url:
                url_checked += 1
                url_check_result = _check_url_accessible(bib_url, timeout_s=timeout_s, user_agent=user_agent)
                url_check_result["checked"] = True
                if url_check_result.get("ok"):
                    url_accessible += 1

            # Compare bib title with API title
            bib_title = (fields.get("title") or "").strip()
            title_comparison = _compare_titles(bib_title, title)
            match_type = title_comparison.get("match", "missing")
            if match_type == "exact":
                title_match_exact += 1
            elif match_type == "fuzzy":
                title_match_fuzzy += 1
            elif match_type == "mismatch":
                title_mismatch += 1

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
                "url_check": url_check_result,
                "title_comparison": title_comparison,
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

        # Sleep between batches to avoid rate limiting (except for the last batch)
        if batch_start + batch_size < len(cited_keys):
            time.sleep(0.5)

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
            "url_checked": url_checked,
            "url_accessible": url_accessible,
            "title_match_exact": title_match_exact,
            "title_match_fuzzy": title_match_fuzzy,
            "title_mismatch": title_mismatch,
        },
        "outputs": {
            "reference_evidence_jsonl": str(evidence_path.name),
            "reference_evidence_summary_json": str(summary_path.name),
        },
        "notes": [
            "This is best-effort evidence collection for later AI semantic checks.",
            "PDF fetching is optional and only attempts arXiv/Unpaywall OA links or bib url ending with .pdf.",
            "URL accessibility check uses HTTP HEAD request on bib url field.",
            "Title comparison: exact (case-insensitive match), fuzzy (normalized/word overlap), mismatch (low similarity).",
            f"Concurrency control: max {batch_size} concurrent requests per batch.",
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
    ap.add_argument("--max-concurrent", type=int, default=5, help="max concurrent network requests for reference resolution (default: 5, to avoid rate limiting)")
    ap.add_argument("--timeout-s", type=int, default=20, help="network timeout seconds for reference resolution")
    args = ap.parse_args()

    project_root = Path(args.project_root).expanduser().resolve()
    out_dir = Path(args.out).expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    main_tex = _resolve_main_tex(project_root, str(args.main_tex))
    if not main_tex:
        print(f"error: main tex not found (or auto-detect failed): {project_root / args.main_tex}", file=sys.stderr)
        return 2
    try:
        main_tex_rel = str(main_tex.relative_to(project_root))
    except Exception:
        main_tex_rel = str(main_tex)

    tex_files = _find_included_tex_files(main_tex)
    bib_files = _find_bib_files(tex_files, project_root)
    citations = _extract_citations(tex_files, project_root=project_root)
    bib_entries = _parse_bib_keys(bib_files)
    lengths = _rough_text_metrics(tex_files)
    typography = _detect_quote_issues(tex_files, project_root=project_root)
    abbreviation_conventions = _detect_abbreviation_conventions(main_tex=main_tex, project_root=project_root)
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
            max_concurrent=int(args.max_concurrent),
        )
        reference_evidence["enabled"] = True

    abbreviation_summary_public = abbreviation_conventions
    if isinstance(abbreviation_conventions, dict):
        abbreviation_summary_public = {
            "summary": abbreviation_conventions.get("summary") or {},
            "issues_preview": abbreviation_conventions.get("issues_preview") or [],
            "registry_preview": abbreviation_conventions.get("registry_preview") or [],
            "note": abbreviation_conventions.get("note") or "",
        }

    precheck = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "project_root": str(project_root),
        "main_tex": main_tex_rel,
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
        "abbreviation_conventions": abbreviation_summary_public,
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
        w.writerow(["severity", "issue_kind", "abbr", "path", "line", "column", "english_full", "chinese_full", "details", "recommendation", "excerpt", "context"])
        for it in abbr_items:
            w.writerow(
                [
                    it.get("severity", ""),
                    it.get("issue_kind", ""),
                    it.get("abbr", ""),
                    it.get("path", ""),
                    it.get("line", ""),
                    it.get("column", ""),
                    it.get("english_full", ""),
                    it.get("chinese_full", ""),
                    it.get("details", ""),
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
                "column": it.get("column", ""),
                "english_full": it.get("english_full", ""),
                "chinese_full": it.get("chinese_full", ""),
                "details": it.get("details", ""),
                "recommendation": it.get("recommendation", ""),
            }
        )
    issue_kinds_count = {}
    if isinstance(abbr_summary, dict):
        issue_kinds_count = abbr_summary.get("issues_by_kind") or {}
    (out_dir / "abbreviation_issues_summary.json").write_text(
        json.dumps(
            {
                "total_abbreviations_detected": total_abbr_detected,
                "issues_count": issues_count,
                "issues_by_kind": issue_kinds_count,
                "top_issues": top_issues,
                "note": "Heuristic only. AI threads should verify each item and filter false positives.",
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    abbr_registry = (abbreviation_conventions.get("registry") or []) if isinstance(abbreviation_conventions, dict) else []
    (out_dir / "abbreviation_registry.json").write_text(
        json.dumps(abbr_registry, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    render_stream = (abbreviation_conventions.get("render_stream") or []) if isinstance(abbreviation_conventions, dict) else []
    with (out_dir / "abbreviation_render_stream.jsonl").open("w", encoding="utf-8") as f:
        for item in render_stream:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")

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
