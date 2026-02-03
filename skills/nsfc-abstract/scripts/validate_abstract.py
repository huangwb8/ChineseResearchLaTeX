#!/usr/bin/env python3
"""
Validate abstract length constraints for nsfc-abstract skill output.

Expected input contains:
  [ZH] ... [/ZH]
  [EN] ... [/EN]
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Optional, Tuple


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _extract_block(text: str, begin: str, end: str) -> str:
    # Non-greedy across newlines
    pattern = re.compile(re.escape(begin) + r"(.*?)" + re.escape(end), re.DOTALL)
    m = pattern.search(text)
    if not m:
        raise ValueError(f"未找到分段标记：{begin}...{end}")
    return m.group(1).strip()

def _extract_blocks_by_headings(text: str, zh_heading: str, en_heading: str) -> Tuple[str, str]:
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

    if zh_i is None or en_i is None or zh_i > en_i:
        raise ValueError(f"未找到标题分段：{zh_heading} 与 {en_heading}")

    zh = "\n".join(lines[zh_i + 1 : en_i]).strip()

    # EN content ends at the next markdown heading (any level) if present,
    # e.g. "## 长度自检" appended by writer script.
    en_lines = []
    for line in lines[en_i + 1 :]:
        if line.lstrip().startswith("#"):
            break
        en_lines.append(line)
    en = "\n".join(en_lines).strip()
    if not zh or not en:
        raise ValueError("标题分段已找到，但内容为空（请在标题下方写入正文）")
    return zh, en


def _normalize_for_count(text: str) -> str:
    # Abstracts are typically submitted as a single paragraph. Users may format
    # outputs with newlines/spaces for readability; count after collapsing
    # whitespace to reduce surprises.
    return re.sub(r"\s+", " ", text).strip()


def _load_limits_from_config(skill_root: Path) -> tuple[int, int, str, str, str, str, str, str, str]:
    """
    Avoid external deps (PyYAML). We only need a few scalar fields, so parse by regex.
    """
    config_path = skill_root / "config.yaml"
    if not config_path.exists():
        return 400, 4000, "[ZH]", "[/ZH]", "[EN]", "[/EN]"

    raw = config_path.read_text(encoding="utf-8")

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
        m = re.search(rf"^[ \\t]*{re.escape(key)}:[ \\t]*(.+?)\s*$", raw, re.M)
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
    zh_heading = _str("zh_heading", "# 中文摘要")
    en_heading = _str("en_heading", "# English Abstract")
    out_name = _str("filename", "NSFC-ABSTRACTS.md")
    return zh_max, en_max, zh_begin, zh_end, en_begin, en_end, zh_heading, en_heading, out_name


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(
        formatter_class=argparse.RawTextHelpFormatter,
        description=(
            "Validate nsfc-abstract output length constraints.\n"
            "It extracts [ZH]...[/ZH] and [EN]...[/EN] blocks, then counts characters.\n"
            "Counting collapses consecutive whitespace into a single space by default."
        ),
        epilog=(
            "Exit codes:\n"
            "  0  success (and within limits when --strict is used)\n"
            "  1  exceeded limits with --strict\n"
            "  2  input format error (missing markers)\n"
        ),
    )
    ap.add_argument("file", help="包含 [ZH]/[EN] 分段标记的文本文件路径（或 - 表示 stdin）")
    ap.add_argument("--strict", action="store_true", help="超限则返回非 0")
    args = ap.parse_args(argv)

    skill_root = Path(__file__).resolve().parents[1]
    (
        zh_max,
        en_max,
        zh_begin,
        zh_end,
        en_begin,
        en_end,
        zh_heading,
        en_heading,
        out_name,
    ) = _load_limits_from_config(skill_root)

    if args.file == "-":
        text = sys.stdin.read()
    else:
        text = _read_text(Path(args.file))

    zh_raw = None
    en_raw = None
    try:
        zh_raw = _extract_block(text, zh_begin, zh_end)
        en_raw = _extract_block(text, en_begin, en_end)
    except ValueError:
        # Fall back to heading-based extraction.
        try:
            zh_raw, en_raw = _extract_blocks_by_headings(text, zh_heading, en_heading)
        except ValueError as e:
            print(f"[ERROR] {e}", file=sys.stderr)
            print("", file=sys.stderr)
            print("修复提示（两种任选其一）：", file=sys.stderr)
            print("A) 标记格式：", file=sys.stderr)
            print(f"{zh_begin}\n（中文摘要正文）\n{zh_end}", file=sys.stderr)
            print(f"{en_begin}\n(English abstract translation)\n{en_end}", file=sys.stderr)
            print("", file=sys.stderr)
            print("B) 标题格式（推荐，便于直接保存为文件）：", file=sys.stderr)
            print(f"{zh_heading}\n（中文摘要正文）\n\n{en_heading}\n(English abstract translation)", file=sys.stderr)
            print("", file=sys.stderr)
            print(f"提示：本 skill 约定输出文件为工作目录下的 `{out_name}`（可用 write_abstracts_md.py 生成）。", file=sys.stderr)
            return 2

    zh = _normalize_for_count(zh_raw)
    en = _normalize_for_count(en_raw)

    zh_len = len(zh)
    en_len = len(en)
    zh_raw_len = len(zh_raw)
    en_raw_len = len(en_raw)

    zh_ok = zh_len <= zh_max
    en_ok = en_len <= en_max

    print("Length Check (whitespace-collapsed)")
    print(f"- Limits: ZH<= {zh_max}, EN<= {en_max}")
    print(f"- Markers: ZH {zh_begin}..{zh_end}; EN {en_begin}..{en_end}")
    print(f"- Headings: ZH {zh_heading}; EN {en_heading}")
    print(f"- ZH: {zh_len}/{zh_max} ({'OK' if zh_ok else 'EXCEEDED'}) [raw={zh_raw_len}]")
    print(f"- EN: {en_len}/{en_max} ({'OK' if en_ok else 'EXCEEDED'}) [raw={en_raw_len}]")

    if args.strict and (not zh_ok or not en_ok):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
