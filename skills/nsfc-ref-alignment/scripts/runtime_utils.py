#!/usr/bin/env python3
from __future__ import annotations

import datetime as dt
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


def python_executable() -> str:
    return sys.executable or "python3"


def utc_timestamp_compact() -> str:
    # Use local time (not UTC) to match user expectations in filenames.
    return dt.datetime.now().strftime("%Y%m%d%H%M%S")


def load_config(skill_root: Path) -> Tuple[Dict[str, Any], List[str]]:
    """
    Best-effort load YAML config; fallback to minimal defaults if PyYAML is missing.
    Returns (config, warnings).
    """
    warnings: List[str] = []
    cfg_path = skill_root / "config.yaml"
    if not cfg_path.exists():
        return {}, [f"config.yaml not found at {cfg_path}"]

    text = cfg_path.read_text(encoding="utf-8", errors="ignore")
    try:
        import yaml  # type: ignore

        data = yaml.safe_load(text) or {}
        if not isinstance(data, dict):
            warnings.append("config.yaml parsed but is not a dict; fallback to empty config")
            return {}, warnings
        return data, warnings
    except Exception as e:
        warnings.append(f"PyYAML unavailable or failed to parse config.yaml ({e}); using fallback defaults")
        return {}, warnings


def strip_latex_comment(line: str) -> str:
    """
    Remove unescaped '%' comments from a LaTeX line while keeping content before it.
    """
    for i, ch in enumerate(line):
        if ch != "%":
            continue
        bs = 0
        j = i - 1
        while j >= 0 and line[j] == "\\":
            bs += 1
            j -= 1
        if bs % 2 == 1:
            continue
        return line[:i].rstrip()
    return line.rstrip("\n")


def sanitize_lines_for_parsing(lines: List[str]) -> List[str]:
    """
    Preprocess lines for command extraction:
    - strip comments
    - blank out verbatim-like environments (keep line count stable)
    """
    out: List[str] = []
    in_verbatim = False
    for line in lines:
        stripped = line.strip()
        if not in_verbatim and (
            r"\begin{verbatim}" in stripped
            or r"\begin{lstlisting}" in stripped
            or r"\begin{minted}" in stripped
        ):
            in_verbatim = True
            out.append("")
            continue
        if in_verbatim and (
            r"\end{verbatim}" in stripped
            or r"\end{lstlisting}" in stripped
            or r"\end{minted}" in stripped
        ):
            in_verbatim = False
            out.append("")
            continue
        if in_verbatim:
            out.append("")
            continue
        out.append(strip_latex_comment(line))
    return out


def relpath_safe(path: Path, base: Path) -> str:
    try:
        return str(path.resolve().relative_to(base.resolve()))
    except Exception:
        return str(path)

