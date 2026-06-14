#!/usr/bin/env python3
"""
bib_utils.py - BibTeX 解析与（可选）PDF 摘要段抽取

注意：
- 仅做确定性抽取；抽取失败应降级而非中断
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List, Optional


def parse_bib_file(bib_path: Path) -> Dict[str, dict]:
    """解析 BibTeX 为 dict[bibkey -> fields(lowercase)]."""
    text = bib_path.read_text(encoding="utf-8", errors="ignore")
    entries: Dict[str, dict] = {}

    try:
        import bibtexparser  # type: ignore

        bib_db = bibtexparser.loads(text)
        for e in bib_db.entries:
            key = e.get("ID") or e.get("id")
            if not key:
                continue
            entries[key] = {k.lower(): v for k, v in e.items()}
        if entries:
            return entries
    except Exception:
        # fallback to manual parsing
        pass

    raw_entries = re.split(r"@\w+\s*\{", text)
    for chunk in raw_entries[1:]:
        if "}" not in chunk:
            continue
        key_part, rest = chunk.split(",", 1)
        key = key_part.strip()
        fields: Dict[str, str] = {}
        for field_match in re.finditer(r"(\w+)\s*=\s*[{\"]([^}\"]+)", rest):
            fields[field_match.group(1).lower()] = field_match.group(2).strip()
        entries[key] = fields
    return entries


def find_pdf_for_entry(entry: dict, base_dir: Path) -> Optional[Path]:
    """从 bib entry 的 file/pdf/url 字段里尽力解析出本地 PDF 路径。"""
    file_field = entry.get("file") or entry.get("pdf") or entry.get("url")
    if not file_field:
        return None
    raw = str(file_field)

    # 常见 BibTeX `file` 字段格式：
    # - "/abs/path/to/paper.pdf"
    # - "relative/paper.pdf"
    # - "/abs/path/paper.pdf:PDF" (Zotero)
    # - "C:\\path\\paper.pdf:PDF" (Windows)
    # - 多附件用 ';' 分隔
    parts = [p.strip() for p in raw.split(";") if p.strip()]
    for part in parts or [raw.strip()]:
        m = re.search(r"(?P<path>(?:[A-Za-z]:)?[^;]*?\.pdf)", part, re.IGNORECASE)
        candidate = (m.group("path") if m else part).strip().strip("{}").strip()
        candidate = candidate.lstrip(":")  # Zotero 有时会多一个 ':'
        if not candidate:
            continue

        p = Path(candidate)
        if not p.is_absolute():
            p = base_dir / p

        if p.exists() and p.suffix.lower() == ".pdf":
            return p

    return None


def extract_pdf_text(pdf_path: Path, max_pages: int, warnings: List[str]) -> str:
    """抽取 PDF 前 max_pages 页文本；失败则返回空串并写 warnings。"""
    if not pdf_path.exists():
        return ""

    try:
        import pdfplumber  # type: ignore

        text_parts: List[str] = []
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages[:max_pages]:
                text_parts.append(page.extract_text() or "")
        return "\n".join(text_parts).strip()
    except Exception as e:
        warnings.append(f"pdfplumber 不可用或解析失败，尝试 PyPDF2。原因: {e}")

    try:
        from PyPDF2 import PdfReader  # type: ignore

        reader = PdfReader(str(pdf_path))
        texts: List[str] = []
        for idx, page in enumerate(reader.pages):
            if idx >= max_pages:
                break
            try:
                texts.append(page.extract_text() or "")
            except Exception as inner:
                warnings.append(f"PyPDF2 解析第 {idx+1} 页失败: {inner}")
        return "\n".join(texts).strip()
    except Exception as e:
        warnings.append(f"PyPDF2 不可用或解析失败: {e}")
        return ""

