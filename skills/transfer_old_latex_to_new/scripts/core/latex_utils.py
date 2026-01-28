#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable, List, Set, Tuple


INPUT_RE = re.compile(r"\\(input|include)\{([^}]+)\}")
GRAPHICS_RE = re.compile(r"\\(includegraphics|epsfig)\*?(?:\[[^\]]*\])?\{([^}]+)\}")
LSTINPUTLISTING_RE = re.compile(r"\\lstinputlisting(?:\[[^\]]*\])?\{([^}]+)\}")
IMPORT_RE = re.compile(r"\\(import|includefrom)\*?\{([^}]+)\}\{([^}]+)\}")


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
CITE_RE = re.compile(r"\\cite[a-zA-Z]*\*?\{([^}]+)\}")


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


def extract_graphics(tex: str) -> Set[str]:
    """
    提取图片引用路径
    支持: \includegraphics[options]{path}, \epsfig[options]{file=path}
    """
    tex = strip_comments(tex)
    paths: Set[str] = set()
    for match in GRAPHICS_RE.finditer(tex):
        raw = match.group(2).strip()
        if "file=" in raw:
            for part in raw.split(","):
                part = part.strip()
                if part.startswith("file="):
                    raw = part.split("=", 1)[1].strip()
                    break
        if raw:
            paths.add(raw)
    return paths


def extract_lstinputlisting(tex: str) -> Set[str]:
    """
    提取代码文件引用路径
    支持: \lstinputlisting[options]{path}
    """
    tex = strip_comments(tex)
    return set(m.group(1).strip() for m in LSTINPUTLISTING_RE.finditer(tex))


def extract_imports(tex: str) -> Set[str]:
    """
    提取 LaTeX import 路径
    支持: \import{path}{file}, \includefrom{path}{file}
    """
    tex = strip_comments(tex)
    paths: Set[str] = set()
    for match in IMPORT_RE.finditer(tex):
        base = match.group(2).strip()
        filename = match.group(3).strip()
        if not filename:
            continue
        combined = Path(base) / filename if base else Path(filename)
        paths.add(str(combined).replace("\\", "/"))
    return paths


def extract_all_resource_paths(tex: str) -> Set[str]:
    """
    提取所有外部资源文件路径（图片、代码、其他文件）
    """
    resources: Set[str] = set()
    resources.update(extract_graphics(tex))
    resources.update(extract_lstinputlisting(tex))
    resources.update(extract_imports(tex))
    return resources


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
