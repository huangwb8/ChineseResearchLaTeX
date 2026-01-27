#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
逐段对齐工具（paragraph alignment）

目标：从 PDF 中提取“段落级”结构并进行匹配与像素对比，
用于替代整页像素对比在“空模板 vs 有正文”场景下的高噪声问题。
"""

from __future__ import annotations

import difflib
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class ParagraphLine:
    bbox: Tuple[float, float, float, float]
    text: str
    x0: float
    y0: float
    y1: float
    font_size: float


@dataclass
class Paragraph:
    page_num: int  # 1-based
    paragraph_id: int  # 1-based within page
    text: str
    bbox: Tuple[float, float, float, float]
    line_count: int
    lines: List[ParagraphLine]
    type: str  # heading|body|unknown
    image_rgb: Optional[Any] = None  # numpy array (H,W,3)


def _normalize_text_for_match(text: str) -> str:
    t = (text or "").strip()
    t = t.replace("\u00a0", " ").replace("~", " ")
    # 统一全角/半角常见符号
    t = t.replace("．", ".").replace("。", ".")
    t = t.replace("（", "(").replace("）", ")")
    t = t.replace("：", ":")
    # 删除空白
    t = "".join(t.split())
    return t


def _classify_paragraph(text: str, line_count: int) -> str:
    t = (text or "").strip()
    if not t:
        return "unknown"
    if line_count == 1:
        if t.startswith("（") and "）" in t:
            return "heading"
        if any(ch.isdigit() for ch in t[:3]):
            return "heading"
    return "body"


def extract_paragraphs_from_pdf(
    pdf_path,
    dpi: int = 150,
    page_num: Optional[int] = None,
    include_images: bool = False,
    y_gap_factor: float = 1.2,
    x0_tolerance: float = 2.0,
) -> List[Paragraph]:
    """
    从 PDF 提取段落（基于“行聚合”启发式）。

    include_images=True 时，会将每个段落裁剪为 RGB numpy array 存入 image_rgb。
    """
    import fitz  # PyMuPDF
    import numpy as np
    from PIL import Image
    import io

    doc = fitz.open(pdf_path)
    try:
        if page_num is not None:
            pages = [page_num - 1] if 1 <= page_num <= len(doc) else [0]
        else:
            pages = list(range(len(doc)))

        out: List[Paragraph] = []
        for pidx in pages:
            page = doc[pidx]
            data = page.get_text("dict")

            # 收集行
            pdf_lines: List[ParagraphLine] = []
            for block in data.get("blocks", []):
                if not block.get("lines"):
                    continue
                for line in block["lines"]:
                    spans = line.get("spans") or []
                    if not spans:
                        continue
                    txt = "".join((s.get("text") or "") for s in spans)
                    if not txt or not txt.strip():
                        continue
                    bbox = tuple(line.get("bbox") or (0, 0, 0, 0))
                    x0, y0, x1, y1 = float(bbox[0]), float(bbox[1]), float(bbox[2]), float(bbox[3])
                    s0 = spans[0]
                    pdf_lines.append(
                        ParagraphLine(
                            bbox=(x0, y0, x1, y1),
                            text=" ".join(str(txt).split()),
                            x0=x0,
                            y0=y0,
                            y1=y1,
                            font_size=float(s0.get("size") or 0.0),
                        )
                    )

            # 按阅读顺序排序
            pdf_lines.sort(key=lambda l: (l.y0, l.x0))

            # 聚合为段落
            paragraphs: List[List[ParagraphLine]] = []
            for ln in pdf_lines:
                if not paragraphs:
                    paragraphs.append([ln])
                    continue
                cur = paragraphs[-1]
                prev = cur[-1]
                prev_h = max(1.0, float(prev.y1 - prev.y0))
                gap = float(ln.y0 - prev.y1)
                same_indent = abs(float(ln.x0) - float(cur[0].x0)) <= x0_tolerance
                font_close = abs(float(ln.font_size) - float(cur[0].font_size)) <= 0.6
                if same_indent and font_close and gap <= (y_gap_factor * prev_h):
                    cur.append(ln)
                else:
                    paragraphs.append([ln])

            # 构造 Paragraph 对象
            para_id = 0
            for group in paragraphs:
                text = "".join([g.text for g in group]).strip()
                if not text:
                    continue
                para_id += 1
                x0 = min(l.bbox[0] for l in group)
                y0 = min(l.bbox[1] for l in group)
                x1 = max(l.bbox[2] for l in group)
                y1 = max(l.bbox[3] for l in group)
                bbox = (float(x0), float(y0), float(x1), float(y1))
                p = Paragraph(
                    page_num=pidx + 1,
                    paragraph_id=para_id,
                    text=text,
                    bbox=bbox,
                    line_count=len(group),
                    lines=group,
                    type=_classify_paragraph(text, len(group)),
                )

                if include_images:
                    mat = fitz.Matrix(dpi / 72, dpi / 72)
                    rect = fitz.Rect(*bbox)
                    pix = page.get_pixmap(matrix=mat, clip=rect)
                    img_data = pix.tobytes("ppm")
                    img = Image.open(io.BytesIO(img_data)).convert("RGB")
                    p.image_rgb = np.array(img)

                out.append(p)

        return out
    finally:
        doc.close()


def match_paragraphs(
    baseline: List[Paragraph],
    target: List[Paragraph],
    min_similarity: float = 0.85,
    max_candidates: int = 50,
) -> List[Dict[str, Any]]:
    """
    基于文本相似度（辅以页面约束）匹配段落。
    返回 match dict 列表（用于 JSON 序列化）。
    """
    tgt_by_page: Dict[int, List[Paragraph]] = {}
    for p in target:
        tgt_by_page.setdefault(p.page_num, []).append(p)

    matches: List[Dict[str, Any]] = []
    used_target: set[Tuple[int, int]] = set()

    for b in baseline:
        candidates = tgt_by_page.get(b.page_num, [])
        if not candidates:
            continue

        b_norm = _normalize_text_for_match(b.text)
        if not b_norm:
            continue

        scored: List[Tuple[float, Paragraph]] = []
        for t in candidates[:max_candidates]:
            if (t.page_num, t.paragraph_id) in used_target:
                continue
            t_norm = _normalize_text_for_match(t.text)
            if not t_norm:
                continue
            sim = difflib.SequenceMatcher(a=b_norm, b=t_norm).ratio()
            if sim >= min_similarity:
                scored.append((sim, t))

        if not scored:
            continue

        scored.sort(key=lambda x: x[0], reverse=True)
        sim, best = scored[0]
        used_target.add((best.page_num, best.paragraph_id))

        matches.append(
            {
                "page_num": b.page_num,
                "text_similarity": float(sim),
                "baseline": {
                    "paragraph_id": b.paragraph_id,
                    "text": b.text,
                    "bbox": list(b.bbox),
                    "type": b.type,
                    "line_count": b.line_count,
                },
                "target": {
                    "paragraph_id": best.paragraph_id,
                    "text": best.text,
                    "bbox": list(best.bbox),
                    "type": best.type,
                    "line_count": best.line_count,
                },
            }
        )

    return matches


def compute_internal_variance(p: Paragraph) -> Dict[str, float]:
    """段内统计（行高/缩进/字号方差）。"""
    import numpy as np

    if not p.lines:
        return {"line_height_variance": 0.0, "indent_variance": 0.0, "font_size_variance": 0.0}

    line_heights = [float(l.y1 - l.y0) for l in p.lines]
    indents = [float(l.x0) for l in p.lines]
    font_sizes = [float(l.font_size) for l in p.lines]

    return {
        "line_height_variance": float(np.var(line_heights)) if len(line_heights) > 1 else 0.0,
        "indent_variance": float(np.var(indents)) if len(indents) > 1 else 0.0,
        "font_size_variance": float(np.var(font_sizes)) if len(font_sizes) > 1 else 0.0,
    }


def image_diff_ratio(img1, img2, tolerance: int = 2) -> Tuple[float, int, int]:
    """复用 compare_pdf_pixels 的核心逻辑：返回 (ratio, diff_pixels, total_pixels)。"""
    import numpy as np
    from PIL import Image

    if img1 is None or img2 is None:
        return 1.0, 0, 0

    if img1.shape != img2.shape:
        img2_pil = Image.fromarray(img2.astype("uint8"))
        img2_pil = img2_pil.resize((img1.shape[1], img1.shape[0]))
        img2 = np.array(img2_pil)

    diff = np.abs(img1.astype(int) - img2.astype(int))
    mask = np.any(diff > tolerance, axis=2)
    total = int(mask.size)
    diff_pixels = int(np.sum(mask))
    ratio = float(diff_pixels) / float(total) if total else 0.0
    return ratio, diff_pixels, total
