from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List, Optional

from utils import read_text


def extract_research_content_section(tex_path: Path) -> str:
    text = read_text(tex_path)
    # Prefer the "研究内容" section if present (subsection/subsubsection both appear in real proposals).
    m = re.search(
        r"\\subsubsection\{研究内容\}(.*?)(?:\\subsubsection\{|\\subsection\{|\\section\{|\\Z)",
        text,
        re.S,
    )
    if m:
        return m.group(1).strip()
    m1 = re.search(
        r"\\subsection\{研究内容\}(.*?)(?:\\subsection\{|\\section\{|\\Z)",
        text,
        re.S,
    )
    if m1:
        return m1.group(1).strip()
    # fallback：尝试立项依据/研究方案相关段落
    m2 = re.search(r"\\section\{.*?(立项依据|研究方案).*?\}(.*?)(?:\\section\{|\\Z)", text, re.S)
    if m2:
        return m2.group(2).strip()
    return text


def _extract_balanced_braces(text: str, start: int) -> tuple[str, int]:
    if start >= len(text) or text[start] != "{":
        raise ValueError("start must point to '{'")
    depth = 0
    i = start
    out: List[str] = []
    while i < len(text):
        ch = text[i]
        if ch == "{":
            depth += 1
            if depth > 1:
                out.append(ch)
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return ("".join(out), i + 1)
            out.append(ch)
        else:
            out.append(ch)
        i += 1
    raise ValueError("unbalanced braces")


def extract_research_terms(tex_path: Path, max_terms: int = 8) -> List[str]:
    section = extract_research_content_section(tex_path)
    terms: List[str] = []

    # 1) itemtitlefont
    i = 0
    needle = r"\itemtitlefont"
    while i < len(section) and len(terms) < max_terms:
        j = section.find(needle, i)
        if j == -1:
            break
        brace = section.find("{", j)
        if brace == -1:
            break
        try:
            content, end = _extract_balanced_braces(section, brace)
        except Exception:
            i = brace + 1
            continue
        t = re.sub(r"\s+", " ", content).strip(" ：:;，,")
        if t:
            terms.append(t)
        i = end

    # 2) subsection/subsubsection titles
    if len(terms) < max_terms:
        for m in re.finditer(r"\\(?:sub)*section\{([^{}]{2,80})\}", section):
            t = m.group(1).strip(" ：:;，,")
            if t and t not in terms:
                terms.append(t)
            if len(terms) >= max_terms:
                break

    # 3) sentence-level keyword chunk fallback
    if len(terms) < max_terms:
        chunks = re.split(r"[。；;\n]+", section)
        for c in chunks:
            c = re.sub(r"\\[a-zA-Z]+", " ", c)
            c = re.sub(r"\$[^$]*\$", " ", c)
            c = re.sub(r"\s+", " ", c).strip(" ：:;，,")
            if 6 <= len(c) <= 28 and c not in terms:
                terms.append(c)
            if len(terms) >= max_terms:
                break

    # 4) method/approach phrases (lightweight heuristic)
    # Aim: surface "采用/基于/提出/构建/使用 ..." phrases that help planning a schematic.
    if len(terms) < max_terms:
        patterns = [
            r"(?:采用|基于|使用|提出|构建|设计)([^。；;\n]{4,32})",
            r"\\textbf\{([^{}]{2,40})\}",
            r"\\emph\{([^{}]{2,40})\}",
        ]
        for pat in patterns:
            for m in re.finditer(pat, section):
                s = m.group(1) if m.lastindex else ""
                s = re.sub(r"\\[a-zA-Z]+", " ", s)
                s = re.sub(r"\$[^$]*\$", " ", s)
                s = s.replace("{", " ").replace("}", " ").replace("~", " ")
                s = re.sub(r"\s+", " ", s).strip(" ：:;，,")
                if 4 <= len(s) <= 36 and s not in terms:
                    terms.append(s)
                if len(terms) >= max_terms:
                    break
            if len(terms) >= max_terms:
                break

    return terms[:max_terms]


def find_candidate_tex(proposal_path: Path) -> Optional[Path]:
    if proposal_path.is_file():
        return proposal_path

    candidates = [
        proposal_path / "extraTex" / "1.1.立项依据.tex",
        proposal_path / "extraTex" / "2.1.研究内容.tex",
        proposal_path / "extraTex" / "2.研究内容.tex",
        proposal_path / "extraTex" / "研究内容.tex",
        proposal_path / "main.tex",
    ]
    for c in candidates:
        if c.exists() and c.is_file():
            return c

    tex_files = sorted([p for p in proposal_path.rglob("*.tex") if p.is_file()])
    return tex_files[0] if tex_files else None


def apply_tex_hints(spec: Dict[str, object], terms: List[str]) -> Dict[str, object]:
    if not terms:
        return spec
    root = spec.get("schematic") if isinstance(spec.get("schematic"), dict) else spec
    groups = root.get("groups") if isinstance(root, dict) else None
    if not isinstance(groups, list):
        return spec

    t_idx = 0
    for g in groups:
        if not isinstance(g, dict):
            continue
        children = g.get("children")
        if not isinstance(children, list):
            continue
        for c in children:
            if not isinstance(c, dict):
                continue
            if t_idx >= len(terms):
                return spec
            label = c.get("label")
            if isinstance(label, str) and len(label.strip()) >= 3:
                continue
            c["label"] = terms[t_idx]
            t_idx += 1
    return spec
