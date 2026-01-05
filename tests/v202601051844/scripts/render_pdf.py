#!/usr/bin/env python3
import argparse
from pathlib import Path

import fitz  # PyMuPDF


def main() -> int:
    parser = argparse.ArgumentParser(description="Render PDF pages to PNG via PyMuPDF.")
    parser.add_argument("--pdf", required=True, help="Input PDF path")
    parser.add_argument("--outdir", required=True, help="Output directory")
    parser.add_argument("--dpi", type=int, default=200, help="Render DPI (default: 200)")
    parser.add_argument(
        "--pages",
        default="1",
        help="Pages to render, 1-based: '1' or '1-3' or '1,3,5' or 'all' (default: 1)",
    )
    args = parser.parse_args()

    pdf_path = Path(args.pdf)
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    doc = fitz.open(pdf_path)
    try:
        if args.pages.strip().lower() == "all":
            pages = list(range(1, doc.page_count + 1))
        else:
            pages = []
            for part in args.pages.split(","):
                part = part.strip()
                if not part:
                    continue
                if "-" in part:
                    a, b = part.split("-", 1)
                    start = int(a.strip())
                    end = int(b.strip())
                    pages.extend(range(start, end + 1))
                else:
                    pages.append(int(part))

        pages = [p for p in pages if 1 <= p <= doc.page_count]
        if not pages:
            raise SystemExit(f"No valid pages to render (pdf pages={doc.page_count}).")

        zoom = args.dpi / 72.0
        matrix = fitz.Matrix(zoom, zoom)

        for page_no in pages:
            page = doc.load_page(page_no - 1)
            pix = page.get_pixmap(matrix=matrix, alpha=False)
            out_path = outdir / f"{pdf_path.stem}.p{page_no:02d}.png"
            pix.save(out_path.as_posix())
    finally:
        doc.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

