#!/usr/bin/env python3
"""
Write NSFC-ABSTRACTS.md in the current working directory.

Input formats supported:
  1) Marker format: [ZH]...[/ZH] and [EN]...[/EN]
  2) Markdown headings: "# 中文摘要" and "# English Abstract" (headings configurable)

This script is intentionally stdlib-only (no PyYAML).
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Optional, Tuple


def _extract_block_by_markers(text: str, begin: str, end: str) -> Optional[str]:
    pattern = re.compile(re.escape(begin) + r"(.*?)" + re.escape(end), re.DOTALL)
    m = pattern.search(text)
    return m.group(1).strip() if m else None


def _extract_block_by_headings(text: str, zh_heading: str, en_heading: str) -> Optional[Tuple[str, str]]:
    # Normalize line endings and keep original content lines.
    lines = text.splitlines()

    def _is_heading(line: str, heading: str) -> bool:
        return line.strip() == heading.strip()

    zh_i = None
    en_i = None
    for i, line in enumerate(lines):
        if zh_i is None and _is_heading(line, zh_heading):
            zh_i = i
            continue
        if en_i is None and _is_heading(line, en_heading):
            en_i = i
            continue

    if zh_i is None or en_i is None:
        return None
    if zh_i > en_i:
        # If swapped, treat as invalid format.
        return None

    zh_lines = lines[zh_i + 1 : en_i]
    en_lines = lines[en_i + 1 :]
    zh = "\n".join(zh_lines).strip()
    en = "\n".join(en_lines).strip()
    return zh, en


def _normalize_for_count(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _load_config(skill_root: Path) -> Tuple[int, int, str, str, str, str, str, str, str]:
    """
    Minimal config reader (no YAML deps). It searches for scalar keys by regex.
    """
    config_path = skill_root / "config.yaml"
    raw = config_path.read_text(encoding="utf-8") if config_path.exists() else ""

    def _strip_inline_comment(value: str) -> str:
        v = value.lstrip()
        if not v:
            return v
        if v[0] in {"\"", "'"}:
            q = v[0]
            out = []
            escaped = False
            for ch in v[1:]:
                if escaped:
                    out.append(ch)
                    escaped = False
                    continue
                if ch == "\\":
                    escaped = True
                    continue
                if ch == q:
                    break
                out.append(ch)
            return "".join(out)
        return v.split("#", 1)[0].rstrip()

    def _get_scalar(key: str) -> Optional[str]:
        m = re.search(rf"^[ \t]*{re.escape(key)}:[ \t]*(.+?)\s*$", raw, re.M)
        if not m:
            return None
        return _strip_inline_comment(m.group(1)).strip()

    def _int(key: str, default: int) -> int:
        v = _get_scalar(key)
        if v is None:
            return default
        return int(v) if v.isdigit() else default

    def _str(key: str, default: str) -> str:
        v = _get_scalar(key)
        return v if v is not None and v != "" else default

    zh_max = _int("zh_max_chars", 400)
    en_max = _int("en_max_chars", 4000)

    zh_begin = _str("zh_begin", "[ZH]")
    zh_end = _str("zh_end", "[/ZH]")
    en_begin = _str("en_begin", "[EN]")
    en_end = _str("en_end", "[/EN]")

    out_name = _str("filename", "NSFC-ABSTRACTS.md")
    zh_heading = _str("zh_heading", "# 中文摘要")
    en_heading = _str("en_heading", "# English Abstract")

    return zh_max, en_max, zh_begin, zh_end, en_begin, en_end, out_name, zh_heading, en_heading


def _parse_input(text: str, *, zh_begin: str, zh_end: str, en_begin: str, en_end: str, zh_heading: str, en_heading: str) -> Tuple[str, str]:
    zh = _extract_block_by_markers(text, zh_begin, zh_end)
    en = _extract_block_by_markers(text, en_begin, en_end)
    if zh is not None and en is not None:
        return zh, en

    by_h = _extract_block_by_headings(text, zh_heading, en_heading)
    if by_h is not None:
        return by_h

    raise ValueError(
        "无法解析输入。请使用以下任一格式：\n"
        f"1) 标记格式：{zh_begin}...{zh_end} 与 {en_begin}...{en_end}\n"
        f"2) 标题格式：{zh_heading} 与 {en_heading}"
    )


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("input", help="包含摘要内容的输入文件路径（或 - 表示 stdin）")
    ap.add_argument("--out", default=None, help="输出 Markdown 文件名（默认取 config.yaml:output.filename）")
    ap.add_argument("--strict", action="store_true", help="超限则返回非 0")
    args = ap.parse_args(argv)

    skill_root = Path(__file__).resolve().parents[1]
    zh_max, en_max, zh_begin, zh_end, en_begin, en_end, default_out, zh_heading, en_heading = _load_config(skill_root)

    if args.input == "-":
        raw = sys.stdin.read()
    else:
        raw = _read_text(Path(args.input))

    zh_raw, en_raw = _parse_input(
        raw,
        zh_begin=zh_begin,
        zh_end=zh_end,
        en_begin=en_begin,
        en_end=en_end,
        zh_heading=zh_heading,
        en_heading=en_heading,
    )

    zh = zh_raw.strip()
    en = en_raw.strip()

    zh_len = len(_normalize_for_count(zh))
    en_len = len(_normalize_for_count(en))

    zh_ok = zh_len <= zh_max
    en_ok = en_len <= en_max

    out_path = Path.cwd() / (args.out or default_out)
    out_text = (
        f"{zh_heading}\n\n{zh}\n\n"
        f"{en_heading}\n\n{en}\n\n"
        "## 长度自检\n"
        f"- 中文摘要字符数：{zh_len}/{zh_max}\n"
        f"- 英文摘要字符数：{en_len}/{en_max}\n"
    )
    out_path.write_text(out_text, encoding="utf-8")

    print(f"[OK] Wrote: {out_path}")
    print(f"- ZH: {zh_len}/{zh_max} ({'OK' if zh_ok else 'EXCEEDED'})")
    print(f"- EN: {en_len}/{en_max} ({'OK' if en_ok else 'EXCEEDED'})")

    if args.strict and (not zh_ok or not en_ok):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
