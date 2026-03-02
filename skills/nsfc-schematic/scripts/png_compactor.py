from __future__ import annotations

import io
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple

from PIL import Image


@dataclass(frozen=True)
class CompactResult:
    src_bytes: int
    dst_bytes: int
    src_size: Tuple[int, int]
    dst_size: Tuple[int, int]
    used_mode: str


def compacted_png_name(filename: str) -> str:
    """
    Convert `xxx.png` -> `xxx_compacted.png`.
    Falls back to appending `_compacted` if the suffix is not `.png`.
    """
    name = str(filename or "").strip()
    if not name:
        return "compacted.png"
    lower = name.lower()
    if lower.endswith(".png"):
        return name[:-4] + "_compacted.png"
    return name + "_compacted.png"


def _has_alpha(img: Image.Image) -> bool:
    if img.mode in {"RGBA", "LA"}:
        return True
    if img.mode == "P" and "transparency" in (img.info or {}):
        return True
    return False


def _resize_if_needed(img: Image.Image, *, target_long_edge_px: int) -> Image.Image:
    w, h = img.size
    if target_long_edge_px <= 0:
        return img
    long_edge = max(w, h)
    if long_edge <= target_long_edge_px:
        return img
    scale = float(target_long_edge_px) / float(long_edge)
    nw = max(1, int(round(w * scale)))
    nh = max(1, int(round(h * scale)))
    return img.resize((nw, nh), resample=Image.Resampling.LANCZOS)


def _encode_png_bytes(img: Image.Image, *, quantize: bool) -> Tuple[bytes, str]:
    buf = io.BytesIO()
    if quantize:
        q = img.quantize(colors=256, method=Image.Quantize.FASTOCTREE, dither=Image.Dither.NONE)
        q.save(buf, format="PNG", optimize=True, compress_level=9)
        return buf.getvalue(), "P(quantized-256)"
    img.save(buf, format="PNG", optimize=True, compress_level=9)
    return buf.getvalue(), img.mode


def compact_png(
    src_png: Path,
    dst_png: Path,
    *,
    target_long_edge_px: int = 2400,
) -> CompactResult:
    """
    Create a much smaller PNG for PDF embedding from a large (e.g. 4K) PNG.

    Strategy (deterministic):
    - downscale to `target_long_edge_px` (never upscale)
    - try both lossless-optimized RGB PNG and 256-color quantized PNG
    - pick the smaller one
    """
    src_png = Path(src_png)
    dst_png = Path(dst_png)
    if not src_png.exists() or not src_png.is_file():
        raise FileNotFoundError(f"src_png 不存在或不是文件：{src_png}")

    src_bytes = src_png.stat().st_size
    with Image.open(src_png) as im0:
        im0.load()
        src_size = (int(im0.size[0]), int(im0.size[1]))

        alpha = _has_alpha(im0)
        if alpha:
            bg = Image.new("RGB", im0.size, (255, 255, 255))
            try:
                bg.paste(im0.convert("RGBA"), mask=im0.convert("RGBA").split()[-1])
            except Exception:
                bg = im0.convert("RGB")
            im = bg
        else:
            im = im0.convert("RGB") if im0.mode != "RGB" else im0.copy()

    im = _resize_if_needed(im, target_long_edge_px=int(target_long_edge_px))
    dst_size = (int(im.size[0]), int(im.size[1]))

    best_bytes: Optional[bytes] = None
    best_mode = "unknown"

    b_rgb, m_rgb = _encode_png_bytes(im, quantize=False)
    best_bytes, best_mode = b_rgb, m_rgb

    b_q, m_q = _encode_png_bytes(im, quantize=True)
    if len(b_q) < len(best_bytes):
        best_bytes, best_mode = b_q, m_q

    dst_png.parent.mkdir(parents=True, exist_ok=True)
    dst_png.write_bytes(best_bytes)
    dst_bytes = dst_png.stat().st_size if dst_png.exists() else 0

    return CompactResult(
        src_bytes=int(src_bytes),
        dst_bytes=int(dst_bytes),
        src_size=src_size,
        dst_size=dst_size,
        used_mode=str(best_mode),
    )

