from __future__ import annotations

import re
from pathlib import Path
from typing import List, Optional

from utils import read_text


def extract_research_content_section(tex_path: Path) -> str:
    text = read_text(tex_path)
    # Grab from \subsubsection{研究内容} to next \subsubsection{...}
    m = re.search(r"\\subsubsection\{研究内容\}(.*?)(?:\\subsubsection\{|\\Z)", text, re.S)
    if not m:
        return text
    return m.group(1).strip()


def _extract_balanced_braces(text: str, start: int) -> tuple[str, int]:
    """
    Extract {...} content starting at `start` which must point to '{'.
    Returns (content_without_outer_braces, index_after_closing_brace).
    """
    if start >= len(text) or text[start] != "{":
        raise ValueError("start must point to '{'")
    depth = 0
    i = start
    out_chars: List[str] = []
    while i < len(text):
        ch = text[i]
        if ch == "{":
            depth += 1
            if depth > 1:
                out_chars.append(ch)
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return ("".join(out_chars), i + 1)
            out_chars.append(ch)
        else:
            out_chars.append(ch)
        i += 1
    raise ValueError("Unbalanced braces")


def extract_item_titles(tex_path: Path, max_items: int = 6) -> List[str]:
    section = extract_research_content_section(tex_path)
    titles: List[str] = []
    # Common patterns:
    # - \item \itemtitlefont{...}：
    # - \itemtitlefont{...}：  (rare in some templates)
    needle = r"\item"
    i = 0
    while i < len(section) and len(titles) < max_items:
        j = section.find(needle, i)
        if j == -1:
            break
        k = section.find(r"\itemtitlefont", j)
        if k == -1:
            i = j + len(needle)
            continue
        brace = section.find("{", k)
        if brace == -1:
            i = k + len(r"\itemtitlefont")
            continue
        try:
            content, end = _extract_balanced_braces(section, brace)
        except Exception:
            i = brace + 1
            continue
        t = re.sub(r"\s+", " ", content).strip(" ：:;，,")
        if t:
            titles.append(t)
        i = end
    return titles


def find_candidate_tex(proposal_path: Path) -> Optional[Path]:
    if proposal_path.is_file():
        return proposal_path
    candidates = [
        proposal_path / "extraTex" / "2.1.研究内容.tex",
        proposal_path / "main.tex",
    ]
    for c in candidates:
        if c.exists():
            return c
    # fallback: first .tex
    tex_files = sorted([p for p in proposal_path.rglob("*.tex") if p.is_file()])
    return tex_files[0] if tex_files else None
