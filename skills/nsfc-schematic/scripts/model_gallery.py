from __future__ import annotations

from dataclasses import dataclass
from math import ceil
from pathlib import Path
import shutil
from typing import Dict, List, Optional, Sequence, Tuple

from utils import dump_yaml, pick_font, warn, write_text


@dataclass(frozen=True)
class TemplateVisual:
    """
    Lightweight visual template metadata for planning-stage "visual picking".

    Notes:
    - `file` is the full reference image (optional).
    - `simple_file` is the simplified "skeleton" reference (optional).
    """

    id: str
    family: str
    file: Optional[str] = None
    simple_file: Optional[str] = None


def _load_pil():
    # Import lazily so plan_schematic.py won't fail if Pillow is not installed.
    try:
        from PIL import Image, ImageDraw, ImageFont  # type: ignore

        return Image, ImageDraw, ImageFont
    except Exception:
        return None


def _load_font(font_candidates: List[str], size: int):
    pil = _load_pil()
    if pil is None:
        return None
    _Image, _ImageDraw, ImageFont = pil
    choice = pick_font(font_candidates, size=size)
    if choice.path is None:
        return ImageFont.load_default()
    try:
        return ImageFont.truetype(str(choice.path), size=size)
    except Exception:
        return ImageFont.load_default()


def _copy_if_exists(src: Path, dst: Path) -> bool:
    if not src.exists() or not src.is_file():
        return False
    try:
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        return True
    except Exception as exc:
        warn(f"复制模板图片失败（已跳过）：{src} -> {dst} ({exc})")
        return False


def _build_contact_sheet(
    items: Sequence[Tuple[TemplateVisual, str]],
    models_dir: Path,
    out_path: Path,
    *,
    font_candidates: Optional[List[str]] = None,
    sheet_width_px: int = 2400,
    cols: int = 3,
) -> Optional[str]:
    """
    Render a simple contact sheet:
    - items: [(template, filename_in_models_dir), ...]
    - returns out_path (posix) on success; None on failure/skip
    """
    pil = _load_pil()
    if pil is None:
        warn("未安装 Pillow（PIL），已跳过 contact sheet 生成（不影响规划输出）")
        return None

    Image, ImageDraw, _ImageFont = pil

    if not items:
        return None

    cols = max(1, int(cols))
    n = len(items)
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
    font = _load_font(fc, size=28) or None
    font_small = _load_font(fc, size=22) or None

    for idx, (t, filename) in enumerate(items):
        r = idx // cols
        c = idx % cols
        x0 = pad + c * (tile_w + pad)
        y0 = pad + r * tile_h

        draw.rectangle([x0, y0, x0 + tile_w, y0 + tile_h], outline=(210, 210, 210), width=2)

        img_path = models_dir / filename
        try:
            im = Image.open(img_path)
            im = im.convert("RGB")
            im.thumbnail((tile_w - 20, img_h - 20), Image.Resampling.LANCZOS)
            px = x0 + (tile_w - im.size[0]) // 2
            py = y0 + (img_h - im.size[1]) // 2
            sheet.paste(im, (px, py))
        except Exception as exc:
            warn(f"读取模板图片失败（已跳过渲染）：{img_path} ({exc})")

        label_y = y0 + img_h + 12
        draw.text((x0 + 12, label_y), f"{t.id}", fill=(20, 20, 20), font=font)
        fam = (t.family or "").strip()
        fam_line = f"family: {fam}" if fam else "family: (unknown)"
        draw.text((x0 + 12, label_y + 38), fam_line, fill=(60, 60, 60), font=font_small)

    try:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        sheet.save(out_path)
        return out_path.as_posix()
    except Exception as exc:
        warn(f"写出 contact sheet 失败（已跳过）：{out_path} ({exc})")
        return None


def materialize_model_gallery(
    templates: List[TemplateVisual],
    src_dir: Path,
    out_dir: Path,
    *,
    font_candidates: Optional[List[str]] = None,
    sheet_width_px: int = 2400,
    cols: int = 3,
) -> Dict[str, str]:
    """
    Build a planning-stage "model gallery" (visual references):
    - Copy referenced images into out_dir/models/
    - Write out_dir/models_index.yaml (always)
    - Generate:
      - out_dir/models_contact_sheet.png (full refs, if any)
      - out_dir/models_simple_contact_sheet.png (skeleton refs, if any)

    Returns a dict of key paths (posix strings).
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    models_dir = out_dir / "models"
    models_dir.mkdir(parents=True, exist_ok=True)

    copied_full: List[Tuple[TemplateVisual, str]] = []
    copied_simple: List[Tuple[TemplateVisual, str]] = []

    for t in templates:
        if t.file:
            src = src_dir / t.file
            dst = models_dir / t.file
            if _copy_if_exists(src, dst):
                copied_full.append((t, t.file))
            else:
                warn(f"模板图片不存在（已跳过）：{src}")
        if t.simple_file:
            src = src_dir / t.simple_file
            dst = models_dir / t.simple_file
            if _copy_if_exists(src, dst):
                copied_simple.append((t, t.simple_file))
            else:
                warn(f"模板骨架图不存在（已跳过）：{src}")

    index = {
        "version": 1,
        "models_dir": models_dir.as_posix(),
        "templates": [
            {
                "id": t.id,
                "family": t.family,
                "file": t.file,
                "simple_file": t.simple_file,
            }
            for t in templates
        ],
    }
    index_path = out_dir / "models_index.yaml"
    write_text(index_path, dump_yaml(index))  # type: ignore[arg-type]

    out: Dict[str, str] = {
        "models_dir": models_dir.as_posix(),
        "models_index": index_path.as_posix(),
    }

    full_sheet = _build_contact_sheet(
        copied_full,
        models_dir,
        out_dir / "models_contact_sheet.png",
        font_candidates=font_candidates,
        sheet_width_px=sheet_width_px,
        cols=cols,
    )
    if full_sheet:
        out["contact_sheet"] = full_sheet

    simple_sheet = _build_contact_sheet(
        copied_simple,
        models_dir,
        out_dir / "models_simple_contact_sheet.png",
        font_candidates=font_candidates,
        sheet_width_px=sheet_width_px,
        cols=cols,
    )
    if simple_sheet:
        out["contact_sheet_simple"] = simple_sheet

    return out

