#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
段落匹配工具

输入：两份 extract_paragraphs.py 产出的 JSON
输出：匹配结果 JSON（用于逐段像素对比或诊断段落对齐问题）
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List


def _load_paragraphs(path: Path) -> List[Dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict) and "paragraphs" in data:
        return data["paragraphs"]
    if isinstance(data, list):
        return data
    raise ValueError(f"无法识别的段落 JSON 格式: {path}")


def main() -> int:
    parser = argparse.ArgumentParser(description="匹配两份 PDF 的段落（文本相似度）")
    parser.add_argument("baseline_json", type=Path, help="baseline 段落 JSON（extract_paragraphs.py 输出）")
    parser.add_argument("target_json", type=Path, help="target 段落 JSON（extract_paragraphs.py 输出）")
    parser.add_argument("--min-similarity", type=float, default=0.85, help="最小文本相似度阈值")
    parser.add_argument("--output", "-o", type=Path, required=True, help="输出 match JSON")

    args = parser.parse_args()
    if not args.baseline_json.exists() or not args.target_json.exists():
        print("❌ 输入文件不存在")
        return 1

    # 将 JSON 结构还原为 core.paragraph_alignment 的 Paragraph 对象列表
    from core.paragraph_alignment import Paragraph, ParagraphLine, match_paragraphs

    def to_obj(items: List[Dict[str, Any]]) -> List[Paragraph]:
        out: List[Paragraph] = []
        for it in items:
            lines = []
            for ln in it.get("lines", []):
                bbox = tuple(float(x) for x in ln.get("bbox", [0, 0, 0, 0]))
                lines.append(
                    ParagraphLine(
                        bbox=bbox,
                        text=str(ln.get("text") or ""),
                        x0=float(bbox[0]),
                        y0=float(bbox[1]),
                        y1=float(bbox[3]),
                        font_size=0.0,
                    )
                )
            out.append(
                Paragraph(
                    page_num=int(it.get("page_num") or 1),
                    paragraph_id=int(it.get("paragraph_id") or 1),
                    text=str(it.get("text") or ""),
                    bbox=tuple(float(x) for x in it.get("bbox", [0, 0, 0, 0])),
                    line_count=int(it.get("line_count") or len(lines)),
                    lines=lines,
                    type=str(it.get("type") or "unknown"),
                    image_rgb=None,
                )
            )
        return out

    baseline_items = _load_paragraphs(args.baseline_json)
    target_items = _load_paragraphs(args.target_json)

    matches = match_paragraphs(
        to_obj(baseline_items),
        to_obj(target_items),
        min_similarity=float(args.min_similarity),
    )

    payload: Dict[str, Any] = {
        "meta": {
            "generated_at": datetime.now().isoformat(),
            "baseline": str(args.baseline_json),
            "target": str(args.target_json),
            "min_similarity": float(args.min_similarity),
        },
        "matches": matches,
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"✅ 已写入: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

