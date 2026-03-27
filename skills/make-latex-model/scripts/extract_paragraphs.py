#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF 段落提取工具

从 PDF 提取段落级结构（bbox + text + lines），可选嵌入段落裁剪图像（base64 PNG）。
"""

from __future__ import annotations

import argparse
import base64
import json
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Any, Dict, List


def _encode_png_base64(img_rgb) -> str:
    from PIL import Image

    img = Image.fromarray(img_rgb.astype("uint8"))
    buf = BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("ascii")


def main() -> int:
    parser = argparse.ArgumentParser(description="从 PDF 中提取段落结构（逐段对齐用）")
    parser.add_argument("pdf_file", type=Path, help="PDF 文件路径")
    parser.add_argument("--page", type=int, default=None, help="只提取指定页（1-based），默认全部")
    parser.add_argument("--dpi", type=int, default=150, help="裁剪图像分辨率（仅 embed-images 时生效）")
    parser.add_argument("--embed-images", action="store_true", help="在 JSON 中嵌入段落图片（base64 PNG，文件会很大）")
    parser.add_argument("--output", "-o", type=Path, required=True, help="输出 JSON 路径")

    args = parser.parse_args()
    if not args.pdf_file.exists():
        print(f"❌ 文件不存在: {args.pdf_file}")
        return 1

    from core.paragraph_alignment import extract_paragraphs_from_pdf

    paras = extract_paragraphs_from_pdf(
        args.pdf_file,
        dpi=args.dpi,
        page_num=args.page,
        include_images=bool(args.embed_images),
    )

    payload: Dict[str, Any] = {
        "meta": {
            "generated_at": datetime.now().isoformat(),
            "source": str(args.pdf_file),
            "page": args.page,
            "dpi": args.dpi,
            "embed_images": bool(args.embed_images),
        },
        "paragraphs": [],
    }

    for p in paras:
        item: Dict[str, Any] = {
            "page_num": p.page_num,
            "paragraph_id": p.paragraph_id,
            "type": p.type,
            "text": p.text,
            "bbox": list(p.bbox),
            "line_count": p.line_count,
            "lines": [{"bbox": list(l.bbox), "text": l.text} for l in p.lines],
        }
        if args.embed_images and p.image_rgb is not None:
            item["image_base64_png"] = _encode_png_base64(p.image_rgb)
        payload["paragraphs"].append(item)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"✅ 已写入: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

