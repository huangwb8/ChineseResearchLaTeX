#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF 标题提取工具

目的：从“基金委/Word 导出的 PDF 基准”中提取标题文字（可选：加粗片段、换行点），
作为标题对齐与格式对齐的唯一真相源（Single Source of Truth）。

使用方法:
  # 提取纯标题文本
  python3 scripts/extract_headings_from_pdf.py baseline.pdf --format json -o headings.json

  # 同时提取格式片段 + 标题跨行换行点
  python3 scripts/extract_headings_from_pdf.py baseline.pdf --check-format --format json -o headings_with_format.json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


MSBLUE_RGB = (0, 112, 192)


def _extract_color_rgb(color: Any) -> Optional[Tuple[int, int, int]]:
    """将 PyMuPDF 的颜色表示统一为 RGB 0-255。"""
    if color is None:
        return None
    if isinstance(color, (list, tuple)) and len(color) >= 3:
        r, g, b = color[0], color[1], color[2]
        # 既可能是 0-1，也可能是 0-255
        if isinstance(r, (int, float)) and r <= 1 and g <= 1 and b <= 1:
            return (int(round(r * 255)), int(round(g * 255)), int(round(b * 255)))
        return (int(round(r)), int(round(g)), int(round(b)))
    return None


def _is_span_bold(span: Dict[str, Any]) -> bool:
    """
    判断 PDF span 是否为“加粗”。

    PyMuPDF span.flags 的 bit4(16) 通常表示 bold，但不同 PDF/字体可能不一致；
    因此同时使用 font name 的启发式做兜底。
    """
    flags = int(span.get("flags", 0) or 0)
    if flags & 16:
        return True

    font = str(span.get("font", "") or "")
    font_upper = font.upper()
    return ("BOLD" in font_upper) or ("BD" in font_upper and "OBLIQUE" not in font_upper)


def _normalize_ws(text: str) -> str:
    text = text.replace("\u00a0", " ")
    text = text.replace("~", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _normalize_for_match(text: str) -> str:
    """
    用于跨来源（PDF vs LaTeX）标题匹配的粗归一化：
    - 去空白
    - 统一常见全角/半角编号符号
    """
    t = _normalize_ws(text)
    t = t.replace("．", ".").replace("。", ".")
    t = t.replace("（", "(").replace("）", ")")
    t = t.replace("：", ":")
    t = re.sub(r"\s+", "", t)
    return t


@dataclass
class _PdfLine:
    page: int
    bbox: Tuple[float, float, float, float]
    text: str
    spans: List[Dict[str, Any]]
    color_rgb: Optional[Tuple[int, int, int]]
    size: float


def _iter_pdf_lines(pdf_path: Path) -> Iterable[_PdfLine]:
    try:
        import fitz  # PyMuPDF
    except ImportError:
        print("错误: 需要安装 PyMuPDF (fitz)")
        print("安装命令: pip install PyMuPDF")
        sys.exit(1)

    doc = fitz.open(pdf_path)
    try:
        for page_idx in range(len(doc)):
            page = doc[page_idx]
            data = page.get_text("dict")
            for block in data.get("blocks", []):
                lines = block.get("lines")
                if not lines:
                    continue
                for line in lines:
                    spans = list(line.get("spans") or [])
                    if not spans:
                        continue
                    txt = "".join((s.get("text") or "") for s in spans)
                    if not txt or not txt.strip():
                        continue
                    # 使用 line 的 bbox（更适合做段/行聚合）
                    bbox = tuple(line.get("bbox") or (0, 0, 0, 0))
                    # 使用第一个 span 的主特征作为行级特征
                    s0 = spans[0]
                    color_rgb = _extract_color_rgb(s0.get("color"))
                    size = float(s0.get("size") or 0.0)
                    yield _PdfLine(
                        page=page_idx,
                        bbox=(float(bbox[0]), float(bbox[1]), float(bbox[2]), float(bbox[3])),
                        text=_normalize_ws(txt),
                        spans=spans,
                        color_rgb=color_rgb,
                        size=size,
                    )
    finally:
        doc.close()


def _looks_like_heading_start(text: str) -> Tuple[bool, Optional[str]]:
    """
    返回 (is_heading, kind) kind in {"section","subsection"}。
    """
    if re.match(r"^（[一二三四五六七八九十]+）", text):
        return True, "section"
    if re.match(r"^\s*\d+\s*[\.．、]", text):
        return True, "subsection"
    return False, None


def _merge_fragments(frags: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    merged: List[Dict[str, Any]] = []
    for f in frags:
        t = f.get("text", "")
        if not t:
            continue
        if not merged:
            merged.append({"text": t, "bold": bool(f.get("bold", False))})
            continue
        last = merged[-1]
        if bool(last.get("bold")) == bool(f.get("bold", False)):
            last["text"] += t
        else:
            merged.append({"text": t, "bold": bool(f.get("bold", False))})
    return merged


def _line_to_fragments(line: _PdfLine) -> List[Dict[str, Any]]:
    frags: List[Dict[str, Any]] = []
    for s in line.spans:
        t = s.get("text") or ""
        if not t:
            continue
        frags.append({"text": t.replace("\u00a0", " ").replace("~", " "), "bold": _is_span_bold(s)})
    return _merge_fragments(frags)


def extract_headings_from_pdf(pdf_path: Path, check_format: bool = False) -> Dict[str, Any]:
    """
    从 PDF 中提取标题。

    输出 key 与 compare_headings.py 保持一致：
      section_1, section_2, ...
      subsection_1_1, subsection_1_2, ...
    """
    if not pdf_path.exists():
        raise FileNotFoundError(str(pdf_path))

    # 先按文档顺序扫描行，并做“标题起始 + 续行”聚合
    lines = sorted(_iter_pdf_lines(pdf_path), key=lambda l: (l.page, l.bbox[1], l.bbox[0]))

    def _is_continuation(prev: _PdfLine, start: _PdfLine, nxt: _PdfLine) -> bool:
        # 不跨页
        if nxt.page != start.page:
            return False
        # 续行不能本身是一个新标题起始
        ok, _ = _looks_like_heading_start(nxt.text)
        if ok:
            return False
        # 缩进基本一致
        if abs(nxt.bbox[0] - start.bbox[0]) > 2.0:
            return False
        # 字号近似（允许 PDF 字号抖动）
        if abs(nxt.size - start.size) > 0.6:
            return False
        # 颜色近似（允许缺失）
        if start.color_rgb and nxt.color_rgb and start.color_rgb != nxt.color_rgb:
            return False
        # 行间距：下一行 top 与上一行 bottom 的间隔要小
        prev_h = max(1.0, float(prev.bbox[3] - prev.bbox[1]))
        gap = float(nxt.bbox[1] - prev.bbox[3])
        if gap > max(2.0, 1.2 * prev_h):
            return False
        return True

    groups: List[Dict[str, Any]] = []
    i = 0
    while i < len(lines):
        ln = lines[i]
        ok, kind = _looks_like_heading_start(ln.text)
        if not ok or not kind:
            i += 1
            continue

        # 轻量兜底：优先保留 MsBlue 的标题，但不强约束（避免误杀）
        # 这里不做过滤，仅保留未来可扩展点。
        _ = (ln.color_rgb == MSBLUE_RGB) if ln.color_rgb else None

        g_lines = [ln]
        j = i + 1
        while j < len(lines) and _is_continuation(g_lines[-1], ln, lines[j]):
            g_lines.append(lines[j])
            j += 1

        groups.append({"kind": kind, "lines": g_lines})
        i = j

    # 将 group 映射为 section/subsection key
    out: Dict[str, Any] = {}
    section_num = 0
    subsection_num = 0

    for g in groups:
        kind = g["kind"]
        g_lines = g["lines"]
        if not g_lines:
            continue

        # 合并文字与换行点
        texts = [l.text for l in g_lines]
        combined = "".join(texts)
        combined = _normalize_ws(combined)
        linebreaks: List[int] = []
        acc = 0
        for t in texts[:-1]:
            acc += len(_normalize_ws(t))
            if acc > 0:
                linebreaks.append(acc)

        if kind == "section":
            section_num += 1
            subsection_num = 0
            key = f"section_{section_num}"
        else:
            if section_num <= 0:
                continue
            subsection_num += 1
            key = f"subsection_{section_num}_{subsection_num}"

        if not check_format:
            out[key] = combined
        else:
            # 把跨行 fragments 拼起来，并在跨行处插入显式空白（避免片段直接拼接）
            frags: List[Dict[str, Any]] = []
            for idx, ln in enumerate(g_lines):
                frags.extend(_line_to_fragments(ln))
                if idx != len(g_lines) - 1:
                    frags.append({"text": " ", "bold": False})
            frags = _merge_fragments(frags)

            out[key] = {
                "text": combined,
                "fragments": frags,
                "linebreaks": linebreaks,
                "location": {
                    "page": int(g_lines[0].page) + 1,
                    "bbox": list(g_lines[0].bbox),
                },
                "normalized": _normalize_for_match(combined),
            }

    return out


def main() -> int:
    parser = argparse.ArgumentParser(
        description="从 PDF 中提取标题文字（可选：格式片段与换行点）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("pdf_file", type=Path, help="PDF 文件路径")
    parser.add_argument("--format", choices=["text", "json"], default="text", help="输出格式")
    parser.add_argument("--output", "-o", type=Path, help="输出文件路径（可选）")
    parser.add_argument("--check-format", action="store_true", help="提取格式信息（加粗/换行点）")

    args = parser.parse_args()

    if not args.pdf_file.exists():
        print(f"❌ 文件不存在: {args.pdf_file}")
        return 1

    headings = extract_headings_from_pdf(args.pdf_file, check_format=args.check_format)

    if args.format == "json":
        payload = {
            "meta": {
                "generated_at": datetime.now().isoformat(),
                "source": str(args.pdf_file),
                "check_format": bool(args.check_format),
            },
            "headings": headings,
        }
        out = json.dumps(payload, ensure_ascii=False, indent=2)
    else:
        lines = ["# PDF 标题提取结果", f"# 源文件: {args.pdf_file}", ""]
        for k in sorted(headings.keys()):
            v = headings[k]
            if isinstance(v, dict):
                lines.append(f"{k}: {v.get('text','')}")
            else:
                lines.append(f"{k}: {v}")
        out = "\n".join(lines)

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(out, encoding="utf-8")
        print(f"✅ 标题已提取到: {args.output}")
    else:
        print(out)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
