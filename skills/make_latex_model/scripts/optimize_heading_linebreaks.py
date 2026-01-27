#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LaTeX 标题换行优化工具

根据 PDF 基准中标题的“跨行换行点”，自动在 LaTeX 标题中插入 \\linebreak{}，
用于更稳定地匹配 PDF 的换行位置（尤其是括号提示语很长的 NSFC 标题）。

说明：
- 本脚本按标题 key 顺序对齐：section_1、subsection_1_1 ...（与 compare_headings 一致）
- 仅在“可见文本（忽略命令/花括号/~）归一化后与 PDF 完全一致”时才会改写
- 若标题包含复杂命令，插入位置以“可见字符位置”映射回原字符串，尽量避免破坏命令结构
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


def _normalize_ws(text: str) -> str:
    text = text.replace("\u00a0", " ").replace("~", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _normalize_for_match(text: str) -> str:
    t = _normalize_ws(text)
    t = t.replace("．", ".").replace("。", ".")
    t = t.replace("（", "(").replace("）", ")")
    t = t.replace("：", ":")
    t = re.sub(r"\s+", "", t)
    return t


def _extract_braced_arg(src: str, brace_start_idx: int) -> Tuple[str, int]:
    """从 src[brace_start_idx]=='{' 开始提取配对花括号内容（支持嵌套），返回 (arg, end_idx)。"""
    if brace_start_idx < 0 or brace_start_idx >= len(src) or src[brace_start_idx] != "{":
        return "", brace_start_idx
    depth = 1
    i = brace_start_idx + 1
    start = i
    while i < len(src) and depth > 0:
        ch = src[i]
        if ch == "\\" and i + 1 < len(src):
            i += 2
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
        i += 1
    if depth != 0:
        return "", brace_start_idx
    return src[start : i - 1], i


def _iter_command_args(src: str, command: str) -> List[Tuple[int, int, str]]:
    """
    返回所有命令的 braced 参数：(cmd_start, arg_brace_idx, arg_text)
    - cmd_start 指向 '\\'
    - arg_brace_idx 指向 '{'
    """
    out: List[Tuple[int, int, str]] = []
    for m in re.finditer(rf"\\{re.escape(command)}\s*\{{", src):
        brace_idx = m.end() - 1
        arg, end_idx = _extract_braced_arg(src, brace_idx)
        if arg:
            out.append((m.start(), brace_idx, arg))
    return out


def _mask_comments(tex: str) -> str:
    """
    将注释内容替换为空格（保持字符串长度不变），以便后续用索引在 original 上做安全替换。

    规则：遇到非转义 %，将该位置到行尾（不含换行符）的字符替换为 ' '。
    """
    out: List[str] = []
    for line in tex.splitlines(keepends=True):
        newline = ""
        body = line
        if line.endswith("\n"):
            newline = "\n"
            body = line[:-1]
        m = re.search(r"(?<!\\)%", body)
        if not m:
            out.append(body + newline)
            continue
        idx = m.start()
        out.append(body[:idx] + (" " * (len(body) - idx)) + newline)
    return "".join(out)


@dataclass
class _VisibleMap:
    visible: str
    raw_index_of_visible: List[int]  # len == len(visible)
    normalized: str
    raw_index_of_normalized: List[int]  # len == len(normalized)


def _build_visible_map(raw: str) -> _VisibleMap:
    """
    将 LaTeX 标题参数映射为“可见文本”并建立 index 映射：
    - visible：去掉命令/花括号后的可见字符序列（~ -> space；\\<non-alpha> 作为转义保留）
    - normalized：对 visible 做空白归一（与 PDF 提取的一致）
    """
    vis_chars: List[str] = []
    vis_map: List[int] = []

    i = 0
    while i < len(raw):
        ch = raw[i]
        if ch == "\\":
            # \command 或转义字符
            if i + 1 < len(raw) and raw[i + 1].isalpha():
                j = i + 1
                while j < len(raw) and raw[j].isalpha():
                    j += 1
                # 允许 \cmd* 形式
                if j < len(raw) and raw[j] == "*":
                    j += 1
                cmd = raw[i + 1 : j]

                # 特殊：\\ 或 \linebreak{} 等换行命令不产生可见字符
                if cmd in ("linebreak", "newline"):
                    i = j
                    # 跳过可选的 {..}
                    while i < len(raw) and raw[i].isspace():
                        i += 1
                    if i < len(raw) and raw[i] == "{":
                        _, end_idx = _extract_braced_arg(raw, i)
                        if end_idx > i:
                            i = end_idx
                    continue

                i = j
                continue
            # \{ \} \% \_ 等转义
            if i + 1 < len(raw):
                esc = raw[i + 1]
                vis_chars.append(" " if esc == "~" else esc)
                vis_map.append(i + 1)
                i += 2
                continue
            i += 1
            continue

        if ch in ("{", "}"):
            i += 1
            continue

        vis_chars.append(" " if ch == "~" else ch)
        vis_map.append(i)
        i += 1

    visible = "".join(vis_chars)

    # 对 visible 做空白归一，并把 normalized 的每个字符映射回 raw index
    norm_chars: List[str] = []
    norm_map: List[int] = []
    in_ws = False
    for c, raw_idx in zip(visible, vis_map):
        if c.isspace():
            if not norm_chars:
                # leading ws: skip
                continue
            if in_ws:
                continue
            norm_chars.append(" ")
            norm_map.append(raw_idx)
            in_ws = True
            continue
        in_ws = False
        norm_chars.append(c)
        norm_map.append(raw_idx)

    # trim trailing single space
    while norm_chars and norm_chars[-1] == " ":
        norm_chars.pop()
        norm_map.pop()

    return _VisibleMap(
        visible=visible,
        raw_index_of_visible=vis_map,
        normalized="".join(norm_chars),
        raw_index_of_normalized=norm_map,
    )


def _insert_linebreaks(raw_title: str, break_positions: List[int], pdf_norm_text: str) -> Tuple[str, int]:
    """
    在 raw_title 的合适位置插入 \\linebreak{}。

    break_positions：基于 PDF 标题文本（归一化后）的字符索引。
    返回 (new_raw_title, inserted_count)
    """
    vmap = _build_visible_map(raw_title)
    if _normalize_for_match(vmap.normalized) != _normalize_for_match(pdf_norm_text):
        return raw_title, 0

    # 将 break_positions 映射回 raw index（在插入过程中要处理偏移，故先算插入点列表）
    insert_raw_indices: List[int] = []
    for pos in sorted(set(int(p) for p in break_positions if p is not None)):
        if pos <= 0:
            continue
        if pos >= len(vmap.normalized):
            insert_raw_indices.append(len(raw_title))
            continue
        raw_idx = vmap.raw_index_of_normalized[pos]
        insert_raw_indices.append(raw_idx)

    if not insert_raw_indices:
        return raw_title, 0

    # 避免重复插入：如果插入点附近已存在 \linebreak{}，跳过
    marker = r"\linebreak{}"
    new = raw_title
    inserted = 0
    offset = 0

    for raw_idx in insert_raw_indices:
        ins_at = raw_idx + offset
        left = max(0, ins_at - 20)
        right = min(len(new), ins_at + 20)
        if marker in new[left:right]:
            continue
        new = new[:ins_at] + marker + new[ins_at:]
        offset += len(marker)
        inserted += 1

    return new, inserted


def _load_pdf_headings_from_json(path: Path) -> Dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    # 兼容 extract_headings_from_pdf.py 的输出（meta + headings）
    if isinstance(data, dict) and "headings" in data:
        return data["headings"]
    # 也允许直接就是 headings dict
    return data


def optimize_heading_linebreaks(tex_path: Path, pdf_headings: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
    """
    返回 (new_content, stats)。
    """
    original = tex_path.read_text(encoding="utf-8")
    masked = _mask_comments(original)

    # 只处理常见标题命令，并保持文档顺序（使用 masked 保持索引一致）
    tokens: List[Tuple[int, str, int, int, str]] = []  # (pos, kind, brace_idx, end_idx, raw_arg_from_original)

    for pos, brace_idx, _ in _iter_command_args(masked, "section"):
        _, end_idx = _extract_braced_arg(masked, brace_idx)
        if end_idx > brace_idx:
            tokens.append((pos, "section", brace_idx, end_idx, original[brace_idx + 1 : end_idx - 1]))
    for pos, brace_idx, _ in _iter_command_args(masked, "NSFCSubsection"):
        _, end_idx = _extract_braced_arg(masked, brace_idx)
        if end_idx > brace_idx:
            tokens.append((pos, "subsection", brace_idx, end_idx, original[brace_idx + 1 : end_idx - 1]))
    for pos, brace_idx, _ in _iter_command_args(masked, "subsection"):
        _, end_idx = _extract_braced_arg(masked, brace_idx)
        if end_idx > brace_idx:
            tokens.append((pos, "subsection", brace_idx, end_idx, original[brace_idx + 1 : end_idx - 1]))

    tokens.sort(key=lambda x: x[0])

    section_num = 0
    subsection_num = 0

    replacements: List[Tuple[int, int, str, int]] = []  # (start_idx, end_idx, new_arg, inserted)
    stats = {"checked": 0, "updated": 0, "skipped_mismatch": 0, "skipped_no_breaks": 0}

    for _, kind, brace_idx, end_idx, raw_arg in tokens:
        if kind == "section":
            section_num += 1
            subsection_num = 0
            key = f"section_{section_num}"
        else:
            if section_num <= 0:
                continue
            subsection_num += 1
            key = f"subsection_{section_num}_{subsection_num}"

        stats["checked"] += 1
        pdf_item = pdf_headings.get(key)
        if not isinstance(pdf_item, dict):
            stats["skipped_no_breaks"] += 1
            continue
        breaks = pdf_item.get("linebreaks") or []
        if not breaks:
            stats["skipped_no_breaks"] += 1
            continue

        pdf_text = str(pdf_item.get("text") or "")
        new_arg, inserted = _insert_linebreaks(raw_arg, breaks, pdf_text)
        if inserted <= 0:
            stats["skipped_mismatch"] += 1
            continue

        # 替换 brace 内容：original[brace_idx] == '{'；替换区间为 (brace_idx+1, end_idx-1)
        replacements.append((brace_idx + 1, end_idx - 1, new_arg, inserted))
        stats["updated"] += 1

    if not replacements:
        return original, stats

    # 应用替换（从后往前，避免偏移）
    new_content = original
    replacements.sort(key=lambda x: x[0], reverse=True)
    for start_idx, end_idx, new_arg, _ in replacements:
        new_content = new_content[:start_idx] + new_arg + new_content[end_idx:]

    return new_content, stats


def main() -> int:
    parser = argparse.ArgumentParser(description="根据 PDF 基准换行点优化 LaTeX 标题换行（插入 \\linebreak{}）")
    parser.add_argument("tex_file", type=Path, help="LaTeX 文件路径（main.tex）")
    parser.add_argument("--pdf-headings", type=Path, help="PDF 标题信息 JSON（extract_headings_from_pdf.py 输出）")
    parser.add_argument("--pdf-baseline", type=Path, help="PDF 基准文件（将直接提取标题信息）")
    parser.add_argument("--output", "-o", type=Path, help="输出文件路径（默认覆盖原文件）")
    parser.add_argument("--dry-run", action="store_true", help="只打印统计信息，不写文件")

    args = parser.parse_args()

    if not args.tex_file.exists():
        print(f"❌ LaTeX 文件不存在: {args.tex_file}")
        return 1

    if not args.pdf_headings and not args.pdf_baseline:
        print("❌ 必须提供 --pdf-headings 或 --pdf-baseline")
        return 1

    if args.pdf_headings:
        if not args.pdf_headings.exists():
            print(f"❌ PDF headings JSON 不存在: {args.pdf_headings}")
            return 1
        pdf_headings = _load_pdf_headings_from_json(args.pdf_headings)
    else:
        if not args.pdf_baseline.exists():
            print(f"❌ PDF 基准不存在: {args.pdf_baseline}")
            return 1
        try:
            from extract_headings_from_pdf import extract_headings_from_pdf
        except Exception as e:
            print(f"❌ 无法导入 extract_headings_from_pdf.py: {e}")
            return 1
        pdf_headings = extract_headings_from_pdf(args.pdf_baseline, check_format=True)

    new_content, stats = optimize_heading_linebreaks(args.tex_file, pdf_headings)

    print("============================================================")
    print("标题换行优化结果")
    print("============================================================")
    for k in ("checked", "updated", "skipped_no_breaks", "skipped_mismatch"):
        print(f"{k}: {stats.get(k)}")

    if args.dry_run:
        print("（dry-run）未写入文件")
        return 0

    out_path = args.output or args.tex_file
    out_path.write_text(new_content, encoding="utf-8")
    print(f"✅ 已写入: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
