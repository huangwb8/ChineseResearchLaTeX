from __future__ import annotations

"""
Extract proposal structure into a JSON-friendly dict (no LLM, deterministic).

This is used by planning_mode=ai:
- script: extract titles/paragraphs/keywords
- host AI: decide phases/nodes/templates and generate roadmap-plan.md + spec_draft.yaml
"""

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from extract_from_tex import (
    extract_item_titles,
    extract_subsubsections,
    find_candidate_justification_tex,
    find_candidate_research_tex,
)
from utils import fatal, read_text


def _clean_latex(text: str) -> str:
    s = text
    # Remove common LaTeX commands while keeping Chinese/English content readable.
    s = re.sub(r"\\(subsection|subsubsection|section)\{[^}]*\}", "\n", s)
    s = re.sub(r"\\itemtitlefont\{([^}]*)\}", r"\1", s)
    s = s.replace("\\item", "\n- ")
    s = re.sub(r"\\[a-zA-Z]+\*?(?:\[[^\]]*\])?(?:\{[^}]*\})?", " ", s)
    s = s.replace("{", " ").replace("}", " ")
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _split_paragraphs(text: str, max_paragraphs: int = 12) -> List[str]:
    # Prefer blank-lines as paragraph separators; fallback to punctuation slicing.
    parts = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    if not parts:
        parts = [text.strip()] if text.strip() else []
    out: List[str] = []
    for p in parts:
        if not p:
            continue
        out.append(p)
        if len(out) >= max_paragraphs:
            break
    return out


def _extract_tex_headings(text: str, max_titles: int = 10) -> List[str]:
    """
    Lightweight heading extraction for .tex to help AI planning when \\itemtitlefont is absent.
    Order-preserving and de-duplicated.
    """
    titles: List[str] = []
    for pat in (r"\\subsubsection\{([^}]*)\}", r"\\subsubsubsection\{([^}]*)\}", r"\\section\{([^}]*)\}"):
        for m in re.finditer(pat, text):
            t = re.sub(r"\s+", " ", (m.group(1) or "").strip())
            t = t.strip(" ：:;，,")
            if not t:
                continue
            if t not in titles:
                titles.append(t)
            if len(titles) >= max_titles:
                return titles
    return titles


def _extract_keywords(titles: List[str], text: str, max_keywords: int = 12) -> List[str]:
    # Deterministic heuristic:
    # - keep ASCII tokens (PAD/CCS/AI/etc.)
    # - keep frequent short Chinese sequences from titles
    blob = "\n".join(titles) + "\n" + text

    ascii_tokens = re.findall(r"[A-Za-z][A-Za-z0-9\-_/]{1,15}", blob)
    ascii_norm: List[str] = []
    for t in ascii_tokens:
        tt = t.strip("-_/").strip()
        if not tt:
            continue
        if tt.lower() in {"and", "the", "with", "for", "from", "into"}:
            continue
        ascii_norm.append(tt)

    # Count Chinese 2-6 char sequences, prefer those in titles.
    cn = re.findall(r"[\u4e00-\u9fff]{2,6}", "\n".join(titles))
    freq: Dict[str, int] = {}
    for w in cn:
        freq[w] = freq.get(w, 0) + 1
    cn_sorted = sorted(freq.items(), key=lambda kv: (-kv[1], kv[0]))
    cn_pick = [w for w, _ in cn_sorted[: max(0, max_keywords - 4)]]

    # Merge, de-dup, keep order.
    out: List[str] = []
    for t in ascii_norm + cn_pick:
        if t not in out:
            out.append(t)
        if len(out) >= max_keywords:
            break
    return out


def _make_section_extract(source: Path, section_names: Optional[List[str]] = None) -> Dict[str, Any]:
    raw_full = read_text(source)
    raw = raw_full
    if source.suffix.lower() == ".tex" and section_names:
        raw = extract_subsubsections(raw_full, section_names)

    # Titles: prefer \\itemtitlefont items (NSFC-style); fallback to heading extraction.
    titles = extract_item_titles(source, max_items=8) if source.suffix.lower() == ".tex" else []
    if not titles and source.suffix.lower() == ".tex":
        titles = _extract_tex_headings(raw_full, max_titles=10)

    clean = _clean_latex(raw) if source.suffix.lower() == ".tex" else re.sub(r"\s+", " ", raw).strip()
    paragraphs = _split_paragraphs(clean, max_paragraphs=12)
    keywords = _extract_keywords(titles, clean, max_keywords=12)

    return {
        "source": str(source),
        "titles": titles,
        "paragraphs": [{"text": p, "excerpt": (p[:140] + "…") if len(p) > 140 else p} for p in paragraphs],
        "keywords": keywords,
        "text_excerpt": (clean[:1200] + "…") if len(clean) > 1200 else clean,
    }


def extract(
    proposal_path: Optional[Path] = None,
    proposal_file: Optional[Path] = None,
    proposal_text: Optional[str] = None,
) -> Dict[str, Any]:
    src: Optional[Path] = None
    raw: str = ""
    titles: List[str] = []

    if proposal_text and str(proposal_text).strip():
        raw = str(proposal_text).strip()
        src = None
    else:
        if proposal_file is not None:
            src = proposal_file
        elif proposal_path is not None:
            src = find_candidate_research_tex(proposal_path)
        if src is None:
            fatal("无法定位 proposal 输入文件（请提供 --proposal-file 或 --proposal-path）")
        if not src.exists() or not src.is_file():
            fatal(f"proposal 输入文件不存在或不是文件：{src}")

        raw = read_text(src)

        # Extract titles for .tex; for other types, try a lightweight heading pattern.
        if src.suffix.lower() == ".tex":
            titles = extract_item_titles(src, max_items=8)
            # Prefer research_content + 技术路线 blocks to reduce noise for planning.
            raw = extract_subsubsections(raw, ["研究内容", "技术路线"])
            if not titles:
                titles = _extract_tex_headings(raw, max_titles=10)
        else:
            # Markdown headings (## / ###) as "titles".
            for m in re.finditer(r"^\s{0,3}#{2,4}\s+(.+?)\s*$", raw, re.M):
                t = m.group(1).strip()
                if t and t not in titles:
                    titles.append(t)
                if len(titles) >= 8:
                    break

    clean = _clean_latex(raw) if src and src.suffix.lower() == ".tex" else re.sub(r"\s+", " ", raw).strip()
    paragraphs = _split_paragraphs(clean, max_paragraphs=12)
    keywords = _extract_keywords(titles, clean, max_keywords=12)

    out: Dict[str, Any] = {
        # Backward-compatible view: keep research_content as the default/top-level.
        "source": str(src) if src is not None else "inline_text",
        "titles": titles,
        "paragraphs": [{"text": p, "excerpt": (p[:140] + "…") if len(p) > 140 else p} for p in paragraphs],
        "keywords": keywords,
        "text_excerpt": (clean[:1200] + "…") if len(clean) > 1200 else clean,
    }

    # Extra planning context (when proposal_path is available).
    if proposal_path is not None and proposal_path.exists() and proposal_path.is_dir():
        j = find_candidate_justification_tex(proposal_path)
        r = find_candidate_research_tex(proposal_path)
        sections: Dict[str, Any] = {}
        sources: Dict[str, str] = {}

        if j is not None and j.exists() and j.is_file():
            sections["justification"] = _make_section_extract(j, section_names=None)
            sources["justification"] = str(j)
        if r is not None and r.exists() and r.is_file():
            sections["research_content"] = _make_section_extract(r, section_names=["研究内容", "技术路线"])
            sources["research_content"] = str(r)

        if sections:
            out["sections"] = sections
            out["sources"] = sources

    return out


def main() -> None:
    import argparse

    p = argparse.ArgumentParser(description="Extract proposal structure for AI planning.")
    p.add_argument("--proposal-path", type=Path, default=None)
    p.add_argument("--proposal-file", type=Path, default=None)
    p.add_argument("--proposal", type=str, default=None)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()

    data = extract(args.proposal_path, args.proposal_file, args.proposal)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
