from __future__ import annotations

"""
Roadmap measurements (no grading / no P0-P2 decisions).

Design principle:
- Scripts do measurement (deterministic math / parsing).
- Host AI (or heuristic fallback) does interpretation / severity decisions.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
import xml.etree.ElementTree as ET

from PIL import Image, ImageDraw, ImageFont

from spec import load_spec
from utils import FontChoice, load_yaml, pick_font, warn


@dataclass(frozen=True)
class BoxTextMeasure:
    box_id: str
    text_h: int
    max_h: int
    ratio: float
    lines: int
    # Optional: used by heuristic fallback / debugging.
    text_w: int
    max_w: int
    box_w: int
    box_h: int
    ratio_wh: float


def _load_font(
    font_choice: FontChoice,
) -> Union[ImageFont.FreeTypeFont, ImageFont.ImageFont]:
    if font_choice.path is None:
        return ImageFont.load_default()
    try:
        return ImageFont.truetype(str(font_choice.path), font_choice.size)
    except Exception:
        return ImageFont.load_default()


def _wrap_text(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont, max_width: int) -> List[str]:
    # Keep consistent with evaluate_roadmap (same line-break behavior is part of determinism).
    words: List[str] = []
    for part in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        if part.strip() == "":
            words.append("")
        else:
            words.append(part.strip())

    lines: List[str] = []
    for w in words:
        if w == "":
            lines.append("")
            continue
        current = ""
        for ch in w:
            candidate = ch if current == "" else (current + ch)
            bbox = draw.textbbox((0, 0), candidate, font=font)
            if bbox[2] <= max_width:
                current = candidate
            else:
                if current:
                    lines.append(current)
                    current = ch
                else:
                    lines.append(ch)
                    current = ""
        if current:
            lines.append(current)
    return lines


def _text_height(draw: ImageDraw.ImageDraw, lines: List[str], font: ImageFont.ImageFont) -> int:
    heights: List[int] = []
    for line in lines:
        bb = draw.textbbox((0, 0), line, font=font)
        heights.append(bb[3] - bb[1])
    return sum(heights) + max(0, (len(lines) - 1)) * 6


def measure_density(png_path: Optional[Path]) -> Dict[str, Any]:
    """
    Measure pixel density proxies from a rendered PNG.

    Returns:
      - available: bool
      - png_size: {w,h} (if available)
      - density: non-white ratio on thumb (if available)
      - quadrant_density: {tl,tr,bl,br} (if available)
      - edge_density: {top,bottom,left,right} (if available)
      - error: string (if not available)
    """
    if png_path is None or not png_path.exists():
        return {"available": False, "error_code": "png_missing"}

    try:
        with Image.open(png_path) as img:
            w, h = img.size
            thumb = img.convert("L").resize((240, 140))
            tw, th = thumb.size
            pixels = list(thumb.getdata())
    except Exception as exc:
        # Keep error text close to legacy evaluator's "PNG 读取失败：{exc}".
        return {"available": False, "error_code": "png_open_failed", "error": str(exc)}

    def is_nonwhite(v: int) -> bool:
        return v < 245

    total = max(1, len(pixels))
    nonwhite = sum(1 for p in pixels if is_nonwhite(int(p)))
    density = nonwhite / total

    # Quadrants: split thumb into 4 blocks.
    def block_density(x0: int, y0: int, x1: int, y1: int) -> float:
        count = 0
        nonw = 0
        for yy in range(y0, y1):
            base = yy * tw
            for xx in range(x0, x1):
                count += 1
                if is_nonwhite(int(pixels[base + xx])):
                    nonw += 1
        return nonw / max(1, count)

    mx = tw // 2
    my = th // 2
    quadrant_density = {
        "tl": block_density(0, 0, mx, my),
        "tr": block_density(mx, 0, tw, my),
        "bl": block_density(0, my, mx, th),
        "br": block_density(mx, my, tw, th),
    }

    # Edge density: use a fixed-width band on thumb.
    band_w = max(1, int(round(tw * 0.12)))
    band_h = max(1, int(round(th * 0.12)))
    edge_density = {
        "top": block_density(0, 0, tw, min(th, band_h)),
        "bottom": block_density(0, max(0, th - band_h), tw, th),
        "left": block_density(0, 0, min(tw, band_w), th),
        "right": block_density(max(0, tw - band_w), 0, tw, th),
    }

    return {
        "available": True,
        "png_size": {"w": w, "h": h},
        "density": density,
        "quadrant_density": quadrant_density,
        "edge_density": edge_density,
    }


def _compute_layout_geometry(spec: Any, config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Compute the same geometry as renderer/evaluator: phase heights and content box.
    This function should stay consistent with evaluate_roadmap to avoid drift.
    """
    renderer = config["renderer"]
    layout = config["layout"]

    font_choice = pick_font(renderer["fonts"]["candidates"], int(renderer["fonts"]["default_size"]))
    if font_choice.path is None:
        warn("未找到可用中文字体候选；输出可能出现中文乱码/方框。")
    font = _load_font(font_choice)

    img = Image.new("RGB", (10, 10), (255, 255, 255))
    draw = ImageDraw.Draw(img)

    width = int(renderer["canvas"]["width_px"])
    height = int(renderer["canvas"]["height_px"])
    margin = int(renderer["canvas"]["margin_px"])
    spacing = int(layout["spacing_px"])

    content_left = margin
    content_right = width - margin

    title_cfg = layout.get("title", {}) if isinstance(layout.get("title", {}), dict) else {}
    notes_cfg = layout.get("notes", {}) if isinstance(layout.get("notes", {}), dict) else {}
    title_enabled = bool(title_cfg.get("enabled", True))
    notes_enabled = bool(notes_cfg.get("enabled", True))

    title_h = 0
    if title_enabled:
        title_size = int(renderer["fonts"]["title_size"])
        title_font = _load_font(pick_font(renderer["fonts"]["candidates"], title_size))
        title_bbox = draw.textbbox((0, 0), getattr(spec, "title", ""), font=title_font)
        title_h = title_bbox[3] - title_bbox[1]

    note = (getattr(spec, "notes", "") or "").strip()
    note_h = 0
    if notes_enabled and note:
        note_bbox = draw.textbbox((0, 0), note, font=font)
        note_h = note_bbox[3] - note_bbox[1]

    content_top = margin + (title_h + spacing if title_enabled else 0)
    content_bottom = height - margin - (note_h + spacing if (notes_enabled and note) else 0)

    phase_gap = spacing
    phase_count = len(getattr(spec, "phases", []) or [])
    available_h = max(1, (content_bottom - content_top - phase_gap * (phase_count - 1)))
    phase_weights: List[int] = [max(1, len(p.rows)) for p in getattr(spec, "phases", [])]
    total_weight = sum(phase_weights) if phase_weights else 1
    phase_heights: List[int] = []
    used = 0
    for i, wgt in enumerate(phase_weights):
        if i == phase_count - 1:
            ph = max(1, available_h - used)
        else:
            ph = max(1, int(round(available_h * (wgt / total_weight))))
        phase_heights.append(ph)
        used += ph
    drift = available_h - sum(phase_heights)
    if phase_heights and drift != 0:
        phase_heights[-1] = max(1, phase_heights[-1] + drift)

    return {
        "font_choice": font_choice,
        "font": font,
        "draw": draw,
        "canvas": {"width_px": width, "height_px": height, "margin_px": margin},
        "content": {
            "left": content_left,
            "right": content_right,
            "top": content_top,
            "bottom": content_bottom,
        },
        "spacing_px": spacing,
        "phase_heights": phase_heights,
    }


def measure_overflow(spec: Any, config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Measure text overflow / near overflow / line wraps per box.
    """
    renderer = config["renderer"]
    layout = config["layout"]

    g = _compute_layout_geometry(spec, config)
    draw: ImageDraw.ImageDraw = g["draw"]
    font: ImageFont.ImageFont = g["font"]
    spacing = int(g["spacing_px"])
    content = g["content"]
    phase_heights: List[int] = list(g["phase_heights"])

    width = int(renderer["canvas"]["width_px"])
    height = int(renderer["canvas"]["height_px"])
    phase_bar_w = int(layout["phase_bar"]["width_px"])
    box_padding = int(layout["box"]["padding_px"])

    content_left = int(content["left"])
    content_right = int(content["right"])
    content_top = int(content["top"])

    phase_gap = spacing
    box_count = 0
    box_text_measures: List[BoxTextMeasure] = []
    overflow_boxes: List[BoxTextMeasure] = []
    # "Near overflow" is intentionally kept as *candidates* (top ratios) without thresholds.
    near_overflow_candidates: List[BoxTextMeasure] = []
    box_line_counts: List[Dict[str, Any]] = []
    box_ratio_wh_list: List[Dict[str, Any]] = []
    structural_issues: List[Dict[str, Any]] = []

    for p_idx, phase in enumerate(getattr(spec, "phases", [])):
        phase_y0 = content_top + sum(phase_heights[:p_idx]) + p_idx * phase_gap
        phase_h = phase_heights[p_idx] if p_idx < len(phase_heights) else 1
        phase_y1 = phase_y0 + phase_h

        area_x0 = content_left + phase_bar_w + spacing
        area_x1 = content_right
        area_y0 = phase_y0
        area_y1 = phase_y1

        rows = phase.rows
        if not rows:
            structural_issues.append({"code": "missing_rows", "where": f"phase:{phase.label}"})
            continue

        row_gap = spacing
        available_row_h = (area_y1 - area_y0) - row_gap * (len(rows) - 1)
        if available_row_h <= 0:
            structural_issues.append(
                {"code": "no_space_for_rows", "where": f"phase:{phase.label}", "available_row_h": available_row_h}
            )
            continue
        row_h = max(1, available_row_h // len(rows))

        for r_idx, row in enumerate(rows):
            row_y0 = area_y0 + r_idx * (row_h + row_gap)
            row_y1 = area_y1 if r_idx == len(rows) - 1 else min(area_y1, row_y0 + row_h)
            max_text_h = (row_y1 - row_y0) - 2 * box_padding
            if max_text_h <= 0:
                structural_issues.append(
                    {"code": "no_space_for_text_h", "where": f"phase:{phase.label}/row:{r_idx+1}", "max_text_h": max_text_h}
                )
                continue

            weights = [b.weight for b in row.boxes]
            total_w_row = sum(weights)
            box_gap = spacing
            available_w = (area_x1 - area_x0) - box_gap * (len(row.boxes) - 1)
            if available_w <= 0 or total_w_row <= 0:
                structural_issues.append(
                    {
                        "code": "no_space_for_boxes",
                        "where": f"phase:{phase.label}/row:{r_idx+1}",
                        "available_w": available_w,
                        "total_weight": total_w_row,
                    }
                )
                continue

            x = area_x0
            for b_idx, box in enumerate(row.boxes):
                w = int(round(available_w * (weights[b_idx] / total_w_row)))
                if b_idx == len(row.boxes) - 1:
                    w = area_x1 - x
                bx0, bx1 = x, x + w

                max_text_w = (bx1 - bx0) - 2 * box_padding
                if max_text_w <= 0:
                    structural_issues.append(
                        {"code": "no_space_for_text_w", "where": f"phase:{phase.label}/row:{r_idx+1}/box:{b_idx+1}", "max_text_w": max_text_w}
                    )
                    x = bx1 + box_gap
                    continue

                lines = _wrap_text(draw, box.text, font, max_text_w)
                th = _text_height(draw, lines, font)
                box_count += 1

                ratio = th / max(1, max_text_h)
                text_bbox = draw.textbbox((0, 0), box.text.replace("\n", ""), font=font)
                tw = max(0, text_bbox[2] - text_bbox[0])
                box_w = max(1, bx1 - bx0)
                box_h = max(1, row_y1 - row_y0)
                ratio_wh = box_w / box_h

                m = BoxTextMeasure(
                    box_id=f"phase:{phase.label}/row:{r_idx+1}/box:{b_idx+1}",
                    text_h=int(th),
                    max_h=int(max_text_h),
                    ratio=float(ratio),
                    lines=int(len(lines)),
                    text_w=int(tw),
                    max_w=int(max_text_w),
                    box_w=int(box_w),
                    box_h=int(box_h),
                    ratio_wh=float(ratio_wh),
                )
                box_text_measures.append(m)
                if th > max_text_h:
                    overflow_boxes.append(m)
                box_line_counts.append({"box_id": m.box_id, "lines": m.lines})
                box_ratio_wh_list.append({"box_id": m.box_id, "ratio_wh": m.ratio_wh})

                x = bx1 + box_gap

    # Pick top-N non-overflow boxes by ratio as "near overflow" candidates (AI can decide thresholds).
    non_overflow = [m for m in box_text_measures if m not in overflow_boxes]
    non_overflow.sort(key=lambda m: m.ratio, reverse=True)
    near_overflow_candidates = non_overflow[: min(10, len(non_overflow))]

    return {
        "box_count": box_count,
        "box_text_measures": box_text_measures,
        "overflow_boxes": overflow_boxes,
        "near_overflow_candidates": near_overflow_candidates,
        "box_line_counts": box_line_counts,
        "box_ratio_wh_list": box_ratio_wh_list,
        "structural_issues": structural_issues,
        "geometry": {
            "canvas": {"width_px": width, "height_px": height},
            "phase_heights": phase_heights,
        },
        "font_choice": g["font_choice"],
    }


def measure_balance(spec: Any, config: Dict[str, Any]) -> Dict[str, Any]:
    g = _compute_layout_geometry(spec, config)
    phase_heights: List[int] = list(g["phase_heights"])
    if not phase_heights:
        return {"phase_heights": [], "ratio": None, "max_h": None, "mean_h": None}
    max_h = max(phase_heights)
    mean_h = sum(phase_heights) / max(1, len(phase_heights))
    ratio = (max_h / mean_h) if mean_h > 0 else None
    return {"phase_heights": phase_heights, "max_h": max_h, "mean_h": mean_h, "ratio": ratio}


def measure_edges(drawio_path: Optional[Path]) -> Dict[str, Any]:
    metrics: Dict[str, Any] = {"available": False, "total": 0, "missing_endpoints": 0, "edge_list": []}
    if drawio_path is None or not drawio_path.exists():
        return metrics
    try:
        root = ET.parse(drawio_path).getroot()
    except Exception:
        return metrics

    cells = root.findall(".//mxCell")
    edges = []
    for c in cells:
        if c.get("edge") == "1":
            edges.append(c)

    missing = 0
    edge_list: List[Dict[str, Any]] = []
    for e in edges:
        src = e.get("source")
        tgt = e.get("target")
        if not src or not tgt:
            missing += 1
        edge_list.append({"id": e.get("id"), "source": src, "target": tgt, "style": e.get("style")})

    metrics.update(
        {
            "available": True,
            "total": len(edges),
            "missing_endpoints": missing,
            "edge_list": edge_list,
        }
    )
    return metrics


def measure_font(config: Dict[str, Any]) -> Dict[str, Any]:
    renderer = config.get("renderer", {}) or {}
    layout = config.get("layout", {}) or {}
    evaluation_cfg = config.get("evaluation", {}) or {}
    thresholds = evaluation_cfg.get("thresholds", {}) or {}

    font_size = int(((renderer.get("fonts", {}) or {}).get("default_size", 0)) or 0)
    min_font = int(thresholds.get("min_font_px", (layout.get("min_font_size", 20) if isinstance(layout, dict) else 20)))
    return {"current": font_size, "min_required": min_font}


def measure(
    spec_yaml: Path,
    config_yaml: Path,
    png_path: Optional[Path] = None,
    drawio_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    Produce a stable measurements dict for host AI consumption.
    """
    config = load_yaml(config_yaml)
    spec_data = load_yaml(spec_yaml)
    spec = load_spec(spec_data)

    overflow = measure_overflow(spec, config)
    balance = measure_balance(spec, config)
    density = measure_density(png_path)
    edges = measure_edges(drawio_path)
    font = measure_font(config)

    # Convert BoxTextMeasure to plain dict for JSON serialization.
    box_text_measures = [m.__dict__ for m in overflow["box_text_measures"]]
    overflow_boxes = [m.__dict__ for m in overflow["overflow_boxes"]]
    near_overflow_boxes = [m.__dict__ for m in overflow["near_overflow_candidates"]]

    return {
        "measurements": {
            "density": density.get("density") if density.get("available") else None,
            "png_size": density.get("png_size") if density.get("available") else None,
            "quadrant_density": density.get("quadrant_density") if density.get("available") else None,
            "edge_density": density.get("edge_density") if density.get("available") else None,
            "density_available": bool(density.get("available")),
            "density_error_code": density.get("error_code"),
            "density_error": density.get("error"),
            "box_text_measures": box_text_measures,
            "overflow_boxes": overflow_boxes,
            "near_overflow_boxes": near_overflow_boxes,
            "box_line_counts": overflow["box_line_counts"],
            "box_ratio_wh_list": overflow["box_ratio_wh_list"],
            "structural_issues": overflow["structural_issues"],
            "phase_balance": {
                "heights": balance.get("phase_heights", []),
                "max_h": balance.get("max_h"),
                "mean_h": balance.get("mean_h"),
                "ratio": balance.get("ratio"),
            },
            "edges": {
                "available": edges.get("available"),
                "total": edges.get("total"),
                "missing_endpoints": edges.get("missing_endpoints"),
            },
            "font": font,
            "canvas": overflow["geometry"]["canvas"],
            "boxes": int(overflow.get("box_count", 0) or 0),
        }
    }


def main() -> None:
    import argparse
    import json

    p = argparse.ArgumentParser(description="Measure nsfc-roadmap (no grading).")
    p.add_argument("--spec", required=True, type=Path)
    p.add_argument("--config", required=True, type=Path)
    p.add_argument("--png", required=False, type=Path, default=None)
    p.add_argument("--drawio", required=False, type=Path, default=None)
    p.add_argument("--out", required=False, type=Path, default=None)
    args = p.parse_args()

    res = measure(args.spec, args.config, png_path=args.png, drawio_path=args.drawio)
    s = json.dumps(res, ensure_ascii=False, indent=2) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(s, encoding="utf-8")
    else:
        print(s, end="")


if __name__ == "__main__":
    main()
