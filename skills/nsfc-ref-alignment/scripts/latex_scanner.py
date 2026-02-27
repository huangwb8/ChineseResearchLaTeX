#!/usr/bin/env python3
from __future__ import annotations

import bisect
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple

from runtime_utils import relpath_safe, sanitize_lines_for_parsing


_INPUT_RE = re.compile(r"\\(input|include)\s*\{(?P<path>[^}]+)\}")
_SECTION_RE = re.compile(r"\\(section|subsection|subsubsection|chapter|part)\*?\s*\{(?P<title>[^}]*)\}")


@dataclass(frozen=True)
class CitationHit:
    bibkey: str
    cite_command: str
    file: str  # relative to project_root when possible
    line: int  # 1-based
    heading: str
    sentence: str


def _normalize_tex_path(raw: str, current_dir: Path) -> Optional[Path]:
    raw = raw.strip()
    if not raw:
        return None
    # handle common \input{foo} where extension omitted
    p = Path(raw)
    if p.suffix.lower() != ".tex":
        p = p.with_suffix(".tex")
    if not p.is_absolute():
        p = (current_dir / p)
    return p


def discover_tex_dependency_tree(project_root: Path, main_tex: Path, max_files: int = 2000) -> Tuple[List[Path], List[str]]:
    """
    Best-effort parse \input/\include dependency tree rooted at main_tex.
    Returns (tex_files, warnings). Paths are absolute.
    """
    warnings: List[str] = []
    visited: Set[Path] = set()
    ordered: List[Path] = []
    stack: List[Path] = [main_tex]

    while stack:
        tex = stack.pop()
        try:
            tex = tex.resolve()
        except Exception:
            tex = tex
        if tex in visited:
            continue
        visited.add(tex)
        ordered.append(tex)
        if len(visited) > max_files:
            warnings.append(f"too many tex files discovered (> {max_files}); stop expanding dependency tree")
            break
        if not tex.exists():
            warnings.append(f"missing tex file referenced: {tex}")
            continue

        try:
            raw_lines = tex.read_text(encoding="utf-8", errors="ignore").splitlines()
        except Exception as e:
            warnings.append(f"failed to read tex file: {tex} ({e})")
            continue

        lines = sanitize_lines_for_parsing(raw_lines)
        cur_dir = tex.parent
        for line in lines:
            for m in _INPUT_RE.finditer(line):
                child = _normalize_tex_path(m.group("path"), cur_dir)
                if child is None:
                    continue
                # keep expansion within project_root as a safety heuristic
                try:
                    child.resolve().relative_to(project_root.resolve())
                except Exception:
                    # Safer default: do not read outside project_root (avoid surprises / leakage).
                    warnings.append(f"skip tex dependency outside project_root: {child}")
                    continue
                stack.append(child)

    # Ensure deterministic order: keep DFS discovery order but stable.
    return ordered, warnings


def discover_bib_files(
    project_root: Path,
    tex_files: Sequence[Path],
    bibliography_commands: Sequence[str],
) -> Tuple[List[Path], List[str]]:
    warnings: List[str] = []
    bibs: List[Path] = []

    cmd_alt = "|".join(re.escape(c) for c in bibliography_commands)
    # Allow optional arguments (mainly for biblatex's \addbibresource[...]{...})
    bib_re = re.compile(
        rf"\\(?:{cmd_alt})\s*(?:\[[^\]]*\]\s*)*\{{(?P<paths>[^}}]+)\}}",
        flags=re.MULTILINE | re.DOTALL,
    )

    for tex in tex_files:
        if not tex.exists():
            continue
        raw_lines = tex.read_text(encoding="utf-8", errors="ignore").splitlines()
        lines = sanitize_lines_for_parsing(raw_lines)
        sanitized_text = "\n".join(lines)
        for m in bib_re.finditer(sanitized_text):
            payload = (m.group("paths") or "").strip()
            if not payload:
                continue
            # \bibliography{a,b,c} allows comma-separated list.
            for part in [p.strip() for p in re.split(r"[,\n]", payload) if p.strip()]:
                p = Path(part.strip().strip("{}").strip())
                if p.suffix.lower() != ".bib":
                    p = p.with_suffix(".bib")
                if not p.is_absolute():
                    # In practice, BibTeX resolves paths relative to the main build cwd (usually project_root),
                    # not the directory of the file that contains \bibliography{}.
                    p = (project_root / p)
                bibs.append(p)

    # de-dup while preserving order
    uniq: List[Path] = []
    seen: Set[str] = set()
    for b in bibs:
        key = str(b)
        if key in seen:
            continue
        seen.add(key)
        uniq.append(b)

    # Fallback: search project_root for *.bib
    if not uniq:
        candidates = [
            p
            for p in sorted(project_root.rglob("*.bib"))
            if ".nsfc-ref-alignment" not in str(p) and ".latex-cache" not in str(p)
        ]
        if candidates:
            warnings.append("no bib file discovered from \\bibliography/\\addbibresource; fallback to scanning project_root/**/*.bib")
            uniq = candidates
        else:
            warnings.append("no .bib file found (neither via commands nor filesystem)")

    return uniq, warnings


def _build_line_starts(text: str) -> List[int]:
    starts = [0]
    for i, ch in enumerate(text):
        if ch == "\n":
            starts.append(i + 1)
    return starts


def _idx_to_line(line_starts: List[int], idx: int) -> int:
    # 1-based
    pos = bisect.bisect_right(line_starts, idx) - 1
    return pos + 1


def _extract_sentence(text: str, start: int, end: int, max_chars: int) -> str:
    """
    Heuristic: find nearest sentence boundary around [start,end).
    """
    # Treat line breaks as whitespace, not sentence boundaries.
    boundaries = set(".!?。！？")
    lo = start
    while lo > 0 and text[lo - 1] not in boundaries:
        lo -= 1
        if start - lo > max_chars:
            break
    hi = end
    while hi < len(text) and text[hi] not in boundaries:
        hi += 1
        if hi - end > max_chars:
            break
    snippet = text[lo:hi].replace("\n", " ").strip()
    # collapse whitespace
    snippet = " ".join(snippet.split())
    if len(snippet) > max_chars:
        snippet = snippet[:max_chars].rstrip() + " …"
    return snippet


def _heading_by_line(lines: List[str]) -> List[str]:
    """
    For each 0-based line index, record last seen heading title.
    """
    cur = ""
    out: List[str] = []
    for line in lines:
        m = _SECTION_RE.search(line)
        if m:
            cur = " ".join(m.group("title").split())
        out.append(cur)
    return out


def extract_citations(
    project_root: Path,
    tex_files: Sequence[Path],
    citation_commands: Sequence[str],
    max_sentence_chars: int,
) -> Tuple[List[CitationHit], List[str]]:
    warnings: List[str] = []
    hits: List[CitationHit] = []

    if not citation_commands:
        warnings.append("citation_commands is empty; no citations extracted")
        return [], warnings

    cmd_alt = "|".join(re.escape(c) for c in citation_commands)
    cite_re = re.compile(
        rf"\\(?P<cmd>{cmd_alt})\s*(?:\[[^\]]*\]\s*)*\{{(?P<keys>[^}}]+)\}}",
        flags=re.MULTILINE | re.DOTALL,
    )

    for tex in tex_files:
        if not tex.exists() or tex.suffix.lower() != ".tex":
            continue
        raw_lines = tex.read_text(encoding="utf-8", errors="ignore").splitlines()
        lines = sanitize_lines_for_parsing(raw_lines)
        sanitized_text = "\n".join(lines)
        line_starts = _build_line_starts(sanitized_text)
        headings = _heading_by_line(lines)

        for m in cite_re.finditer(sanitized_text):
            cmd = m.group("cmd")
            keys_raw = m.group("keys")
            if not keys_raw:
                continue
            keys = [k.strip() for k in re.split(r"[,\n]", keys_raw) if k.strip()]
            if not keys:
                continue
            line_no = _idx_to_line(line_starts, m.start())
            heading = headings[line_no - 1] if 0 < line_no <= len(headings) else ""
            sentence = _extract_sentence(sanitized_text, m.start(), m.end(), max_chars=max_sentence_chars)
            cite_cmd = "\\" + cmd + "{" + keys_raw.strip().replace("\n", " ") + "}"

            for k in keys:
                hits.append(
                    CitationHit(
                        bibkey=k,
                        cite_command=cite_cmd,
                        file=relpath_safe(tex, project_root),
                        line=line_no,
                        heading=heading,
                        sentence=sentence,
                    )
                )

    # common pitfall: \nocite{*}
    if any(h.bibkey == "*" for h in hits):
        warnings.append("found \\nocite{*}; unused-bibkey check will be less meaningful")

    return hits, warnings
