#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
逐段像素对比工具

对比两份 PDF 的“匹配段落”像素差异，输出段落级指标与聚合指标。
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple


def _variance(vals: List[float]) -> float:
    if len(vals) <= 1:
        return 0.0
    m = sum(vals) / len(vals)
    return sum((v - m) ** 2 for v in vals) / len(vals)


def main() -> int:
    parser = argparse.ArgumentParser(description="逐段像素对比（paragraph mode）")
    parser.add_argument("baseline_pdf", type=Path, help="基准 PDF")
    parser.add_argument("target_pdf", type=Path, help="目标 PDF")
    parser.add_argument("--dpi", type=int, default=150, help="渲染 DPI")
    parser.add_argument("--tolerance", type=int, default=2, help="像素容差（RGB）")
    parser.add_argument("--min-similarity", type=float, default=0.85, help="段落文本匹配阈值")
    parser.add_argument("--page", type=int, default=None, help="仅对比指定页（1-based）")
    parser.add_argument("--output", "-o", type=Path, required=True, help="输出 JSON")

    args = parser.parse_args()
    if not args.baseline_pdf.exists() or not args.target_pdf.exists():
        print("❌ 输入 PDF 不存在")
        return 1

    from core.paragraph_alignment import (
        compute_internal_variance,
        extract_paragraphs_from_pdf,
        image_diff_ratio,
        match_paragraphs,
    )

    baseline_paras = extract_paragraphs_from_pdf(
        args.baseline_pdf, dpi=args.dpi, page_num=args.page, include_images=True
    )
    target_paras = extract_paragraphs_from_pdf(
        args.target_pdf, dpi=args.dpi, page_num=args.page, include_images=True
    )

    matches = match_paragraphs(
        baseline_paras, target_paras, min_similarity=float(args.min_similarity)
    )

    # 建立 id -> Paragraph
    bmap: Dict[Tuple[int, int], Any] = {(p.page_num, p.paragraph_id): p for p in baseline_paras}
    tmap: Dict[Tuple[int, int], Any] = {(p.page_num, p.paragraph_id): p for p in target_paras}

    per_match: List[Dict[str, Any]] = []
    x0_diffs: List[float] = []
    y0_diffs: List[float] = []
    gap_diffs: List[float] = []
    internal_vars: List[float] = []

    # 先按 baseline 段落顺序排序，方便计算 gap 差异
    matches_sorted = sorted(
        matches,
        key=lambda m: (int(m.get("page_num") or 1), float(m["baseline"]["bbox"][1]), int(m["baseline"]["paragraph_id"])),
    )

    prev_b = None
    prev_t = None
    total_weight = 0
    weighted_sum = 0.0

    for m in matches_sorted:
        page_num = int(m.get("page_num") or 1)
        b_id = int(m["baseline"]["paragraph_id"])
        t_id = int(m["target"]["paragraph_id"])
        b = bmap.get((page_num, b_id))
        t = tmap.get((page_num, t_id))
        if b is None or t is None:
            continue

        ratio, diff_pixels, total_pixels = image_diff_ratio(b.image_rgb, t.image_rgb, tolerance=int(args.tolerance))
        total_weight += total_pixels
        weighted_sum += ratio * float(total_pixels)

        pos_diff = {
            "x0": float(t.bbox[0] - b.bbox[0]),
            "y0": float(t.bbox[1] - b.bbox[1]),
            "x1": float(t.bbox[2] - b.bbox[2]),
            "y1": float(t.bbox[3] - b.bbox[3]),
        }
        x0_diffs.append(pos_diff["x0"])
        y0_diffs.append(pos_diff["y0"])

        iv_b = compute_internal_variance(b)
        iv_t = compute_internal_variance(t)
        internal_vars.append((float(iv_b["line_height_variance"]) + float(iv_t["line_height_variance"])) / 2.0)

        if prev_b is not None and prev_t is not None and b.page_num == prev_b.page_num and t.page_num == prev_t.page_num:
            b_gap = float(b.bbox[1] - prev_b.bbox[3])
            t_gap = float(t.bbox[1] - prev_t.bbox[3])
            gap_diffs.append(t_gap - b_gap)
        prev_b, prev_t = b, t

        per_match.append(
            {
                "page_num": page_num,
                "baseline_paragraph_id": b.paragraph_id,
                "target_paragraph_id": t.paragraph_id,
                "text_similarity": float(m.get("text_similarity") or 0.0),
                "pixel_diff_ratio": float(ratio),
                "diff_pixels": int(diff_pixels),
                "total_pixels": int(total_pixels),
                "position_diff": pos_diff,
                "internal_variance": {
                    "baseline": iv_b,
                    "target": iv_t,
                },
            }
        )

    avg_ratio = (weighted_sum / float(total_weight)) if total_weight else 1.0

    payload: Dict[str, Any] = {
        "meta": {
            "generated_at": datetime.now().isoformat(),
            "baseline_pdf": str(args.baseline_pdf),
            "target_pdf": str(args.target_pdf),
            "dpi": int(args.dpi),
            "tolerance": int(args.tolerance),
            "min_similarity": float(args.min_similarity),
            "page": args.page,
        },
        "avg_paragraph_pixel_diff": float(avg_ratio),
        "paragraph_position_variance": float(_variance(y0_diffs)),
        "paragraph_spacing_variance": float(_variance(gap_diffs)),
        "indent_variance": float(_variance(x0_diffs)),
        "avg_internal_line_variance": float(sum(internal_vars) / len(internal_vars)) if internal_vars else 0.0,
        "matches": per_match,
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"✅ 已写入: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

