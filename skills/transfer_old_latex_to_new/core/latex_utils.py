#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable, List, Set, Tuple


INPUT_RE = re.compile(r"\\(input|include)\{([^}]+)\}")


def strip_comments(tex: str) -> str:
    lines = []
    for line in tex.splitlines():
        # 保留转义百分号 \% 的内容
        parts = re.split(r"(?<!\\)%", line, maxsplit=1)
        lines.append(parts[0])
    return "\n".join(lines)


def normalize_ws(s: str) -> str:
    return re.sub(r"[ \t]+", " ", s).strip()


def extract_inputs(tex: str) -> List[str]:
    tex = strip_comments(tex)
    return [m.group(2).strip() for m in INPUT_RE.finditer(tex)]


def ensure_tex_suffix(path_fragment: str) -> str:
    p = path_fragment.strip()
    if not p.lower().endswith(".tex"):
        return p + ".tex"
    return p


def safe_read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


HEADING_RE = re.compile(r"\\(section|subsection|subsubsection)\*?\{([^}]*)\}")
LABEL_RE = re.compile(r"\\label\{([^}]+)\}")
REF_RE = re.compile(r"\\ref\{([^}]+)\}")
CITE_RE = re.compile(r"\\cite\{([^}]+)\}")


def extract_headings(tex: str) -> List[Tuple[str, str]]:
    tex = strip_comments(tex)
    return [(m.group(1), normalize_ws(m.group(2))) for m in HEADING_RE.finditer(tex)]


def extract_labels(tex: str) -> Set[str]:
    return set(LABEL_RE.findall(strip_comments(tex)))


def extract_refs(tex: str) -> Set[str]:
    return set(REF_RE.findall(strip_comments(tex)))


def extract_cites(tex: str) -> Set[str]:
    keys: Set[str] = set()
    for block in CITE_RE.findall(strip_comments(tex)):
        for k in block.split(","):
            k = k.strip()
            if k:
                keys.add(k)
    return keys


def strip_commands_for_summary(tex: str, max_chars: int = 240) -> str:
    tex = strip_comments(tex)
    tex = re.sub(r"\\[a-zA-Z@]+(\[[^\]]*\])?\{[^}]*\}", " ", tex)
    tex = re.sub(r"\\[a-zA-Z@]+\*?", " ", tex)
    tex = re.sub(r"\{|\}|\[|\]", " ", tex)
    tex = re.sub(r"\s+", " ", tex).strip()
    return tex[:max_chars]


TOKEN_RE = re.compile(r"[\u4e00-\u9fff]{2,}|[A-Za-z0-9]{2,}")


def tokenize(text: str) -> Set[str]:
    tokens: Set[str] = set()
    for tok in TOKEN_RE.findall(text):
        tokens.add(tok)
        # 对较长中文串补充 2~4 字 n-gram，提升章节名/文件名的匹配鲁棒性
        if tok and all("\u4e00" <= ch <= "\u9fff" for ch in tok) and len(tok) >= 4:
            for n in (2, 3, 4):
                if len(tok) < n:
                    continue
                for i in range(0, len(tok) - n + 1):
                    tokens.add(tok[i : i + n])
    return tokens


def jaccard(a: Set[str], b: Set[str]) -> float:
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b)
    return inter / union if union else 0.0


def normalize_title(title: str) -> str:
    s = title
    s = re.sub(r"^[\d\.\s（）()一二三四五六七八九十]+", "", s)
    return s.strip()


def normalize_filename(stem: str) -> str:
    s = stem
    s = re.sub(r"^[\d\.\s（）()一二三四五六七八九十]+", "", s)
    s = re.sub(r"[_.\-]+", " ", s)
    return s.strip()
