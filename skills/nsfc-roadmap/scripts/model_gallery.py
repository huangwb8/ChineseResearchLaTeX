from __future__ import annotations

from math import ceil
from pathlib import Path
import shutil
from typing import Dict, List, Optional

from PIL import Image, ImageDraw, ImageFont

from template_library import TemplateInfo
from utils import dump_yaml, pick_font, warn, write_text


def _load_font(font_candidates: List[str], size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    choice = pick_font(font_candidates, size=size)
    if choice.path is None:
        return ImageFont.load_default()
    try:
        return ImageFont.truetype(str(choice.path), size=size)
    except Exception:
        # Fall back to default font to keep the planning step robust.
        return ImageFont.load_default()


def materialize_model_gallery(
    templates: List[TemplateInfo],
    src_dir: Path,
    out_dir: Path,
    *,
    font_candidates: Optional[List[str]] = None,
    sheet_width_px: int = 2400,
    cols: int = 3,
) -> Dict[str, str]:
    """
    Build a visual "model gallery" for host-AI selection:
    - Copy referenced model images into out_dir/models/
    - Generate a contact sheet (out_dir/models_contact_sheet.png) with id + family labels
    - Write a small index YAML (out_dir/models_index.yaml)

    Returns a dict with key paths (posix strings).
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    models_dir = out_dir / "models"
    models_dir.mkdir(parents=True, exist_ok=True)

    # Copy images (keep names stable).
    copied: List[TemplateInfo] = []
    for t in templates:
        src = src_dir / t.file
        if not src.exists() or not src.is_file():
            warn(f"模板图片不存在（已跳过）：{src}")
            continue
        dst = models_dir / t.file
        try:
            shutil.copy2(src, dst)
        except Exception as exc:
            warn(f"复制模板图片失败（已跳过）：{src} -> {dst} ({exc})")
            continue
        copied.append(t)

    # Index for deterministic consumption (even if contact sheet is not used).
    index = {
        "version": 1,
        "models_dir": models_dir.as_posix(),
        "templates": [
            {
                "id": t.id,
                "file": t.file,
                "family": t.family,
                "render_family": t.render_family,
            }
            for t in copied
        ],
    }
    index_path = out_dir / "models_index.yaml"
    write_text(index_path, dump_yaml(index))  # type: ignore[arg-type]

    # Contact sheet: keep it simple and readable.
    if not copied:
        return {
            "models_dir": models_dir.as_posix(),
            "models_index": index_path.as_posix(),
        }

    cols = max(1, int(cols))
    n = len(copied)
    rows = ceil(n / cols)

    pad = 30
    tile_w = max(320, (int(sheet_width_px) - pad * (cols + 1)) // cols)
    img_h = int(tile_w * 0.66)
    label_h = 90
    tile_h = img_h + label_h
    sheet_h = pad + rows * tile_h + pad * (rows + 0)

    sheet = Image.new("RGB", (int(sheet_width_px), int(sheet_h)), (255, 255, 255))
    draw = ImageDraw.Draw(sheet)

    fc = font_candidates or []
    font = _load_font(fc, size=28)
    font_small = _load_font(fc, size=22)

    for idx, t in enumerate(copied):
        r = idx // cols
        c = idx % cols
        x0 = pad + c * (tile_w + pad)
        y0 = pad + r * tile_h

        # Tile background + border.
        draw.rectangle([x0, y0, x0 + tile_w, y0 + tile_h], outline=(210, 210, 210), width=2)

        img_path = models_dir / t.file
        try:
            im = Image.open(img_path)
            im = im.convert("RGB")
            # Fit into (tile_w, img_h) with aspect ratio preserved.
            im.thumbnail((tile_w - 20, img_h - 20), Image.Resampling.LANCZOS)
            px = x0 + (tile_w - im.size[0]) // 2
            py = y0 + (img_h - im.size[1]) // 2
            sheet.paste(im, (px, py))
        except Exception as exc:
            warn(f"读取模板图片失败（已跳过渲染）：{img_path} ({exc})")

        # Labels (id + family), keep ASCII-friendly.
        label_y = y0 + img_h + 12
        draw.text((x0 + 12, label_y), f"{t.id}", fill=(20, 20, 20), font=font)
        fam = (t.family or "").strip()
        rf = (t.render_family or "").strip()
        fam_line = f"family: {fam}" if fam else "family: (unknown)"
        if rf and rf != fam:
            fam_line = fam_line + f"  |  render_family: {rf}"
        draw.text((x0 + 12, label_y + 38), fam_line, fill=(60, 60, 60), font=font_small)

    sheet_path = out_dir / "models_contact_sheet.png"
    try:
        sheet.save(sheet_path)
    except Exception as exc:
        warn(f"写出 contact sheet 失败（已跳过）：{sheet_path} ({exc})")
        return {
            "models_dir": models_dir.as_posix(),
            "models_index": index_path.as_posix(),
        }

    return {
        "models_dir": models_dir.as_posix(),
        "models_index": index_path.as_posix(),
        "contact_sheet": sheet_path.as_posix(),
    }
