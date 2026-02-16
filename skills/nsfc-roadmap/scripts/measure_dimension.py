from __future__ import annotations

"""
Multi-dimension measurements for nsfc-roadmap (no grading / no P0-P2 decisions).

This module is designed as AI-friendly evidence:
- scripts: collect deterministic metrics (structure / visual / readability)
- host AI: interpret whether a metric is acceptable in context (print vs screen, narrative intent, etc.)
"""

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from PIL import Image

from spec import load_spec
from utils import hex_to_rgb, load_yaml


def _norm_term(s: str) -> str:
    t = s.strip().replace("\r\n", "\n").replace("\r", "\n")
    for ch in (" ", "\t", "\n", "（", "）", "(", ")", "[", "]", "：", ":", "，", ",", "。", ".", "；", ";"):
        t = t.replace(ch, "")
    return t


def _srgb_channel_to_linear(x: float) -> float:
    if x <= 0.04045:
        return x / 12.92
    return ((x + 0.055) / 1.055) ** 2.4


def _relative_luminance(rgb: Tuple[int, int, int]) -> float:
    r, g, b = rgb
    rl = _srgb_channel_to_linear(r / 255.0)
    gl = _srgb_channel_to_linear(g / 255.0)
    bl = _srgb_channel_to_linear(b / 255.0)
    return 0.2126 * rl + 0.7152 * gl + 0.0722 * bl


def _contrast_ratio(rgb1: Tuple[int, int, int], rgb2: Tuple[int, int, int]) -> float:
    l1 = _relative_luminance(rgb1)
    l2 = _relative_luminance(rgb2)
    hi, lo = (l1, l2) if l1 >= l2 else (l2, l1)
    return (hi + 0.05) / (lo + 0.05)


def _safe_hex_to_rgb(s: str) -> Optional[Tuple[int, int, int]]:
    if not isinstance(s, str):
        return None
    try:
        return hex_to_rgb(s)
    except Exception:
        return None


def _downsample_gray(png_path: Path, size: Tuple[int, int]) -> Optional[List[int]]:
    try:
        with Image.open(png_path) as img:
            thumb = img.convert("L").resize(size)
            return list(thumb.getdata())
    except Exception:
        return None


def measure_structure(spec_yaml: Path, config_yaml: Path) -> Dict[str, Any]:
    _ = load_yaml(config_yaml)  # reserved for future
    spec_data = load_yaml(spec_yaml)
    spec = load_spec(spec_data)

    phase_labels = [p.label.strip() for p in spec.phases]
    dup_phase = sorted({x for x in phase_labels if phase_labels.count(x) >= 2})

    box_terms: Dict[str, List[str]] = {}
    total_boxes = 0
    risk_boxes = 0
    long_boxes: List[Dict[str, Any]] = []
    control_char_boxes: List[str] = []

    for ph in spec.phases:
        for r_idx, row in enumerate(ph.rows, start=1):
            for b_idx, box in enumerate(row.boxes, start=1):
                total_boxes += 1
                if box.kind == "risk":
                    risk_boxes += 1
                text = (box.text or "").strip()
                norm = _norm_term(text)
                if norm:
                    box_terms.setdefault(norm, []).append(f"phase:{ph.label}/row:{r_idx}/box:{b_idx}")
                if len(text) >= 60 and "\n" not in text:
                    long_boxes.append({"box_id": f"phase:{ph.label}/row:{r_idx}/box:{b_idx}", "chars": len(text)})
                if any(ch in text for ch in ("\x00", "\x01", "\x02")):
                    control_char_boxes.append(f"phase:{ph.label}/row:{r_idx}/box:{b_idx}")

    dup_terms = {k: v for k, v in box_terms.items() if len(v) >= 2}

    return {
        "phases": len(spec.phases),
        "phase_labels": phase_labels,
        "dup_phase_labels": dup_phase,
        "boxes_total": total_boxes,
        "risk_boxes": risk_boxes,
        "dup_terms_sample": [{"term_norm": k, "count": len(v), "locs": v[:5]} for k, v in list(dup_terms.items())[:8]],
        "long_singleline_boxes": long_boxes[:12],
        "control_char_boxes": control_char_boxes,
    }


def measure_visual(spec_yaml: Path, config_yaml: Path, png_path: Optional[Path] = None) -> Dict[str, Any]:
    _ = spec_yaml
    config = load_yaml(config_yaml)

    bg_hex = (config.get("renderer", {}) or {}).get("background", "#FFFFFF")
    bg = _safe_hex_to_rgb(str(bg_hex)) or (255, 255, 255)

    layout = config.get("layout", {}) if isinstance(config.get("layout", {}), dict) else {}
    phase_bar = layout.get("phase_bar", {}) if isinstance(layout.get("phase_bar", {}), dict) else {}
    bar_fill = _safe_hex_to_rgb(str(phase_bar.get("fill", "#2F75B5"))) or (47, 117, 181)
    bar_text = _safe_hex_to_rgb(str(phase_bar.get("text_color", "#FFFFFF"))) or (255, 255, 255)

    scheme = config.get("color_scheme", {}) if isinstance(config.get("color_scheme", {}), dict) else {}
    presets = scheme.get("presets", {}) if isinstance(scheme.get("presets", {}), dict) else {}
    scheme_name = str(scheme.get("name", "academic-blue"))
    pal = presets.get(scheme_name, {}) if isinstance(presets.get(scheme_name, {}), dict) else {}

    kinds = ["primary", "secondary", "decision", "critical", "risk", "auxiliary"]
    kind_contrasts: Dict[str, float] = {}
    kind_fills: Dict[str, Tuple[int, int, int]] = {}
    for k in kinds:
        fill = _safe_hex_to_rgb(str((pal.get(k, {}) or {}).get("fill", ""))) if isinstance(pal.get(k, {}), dict) else None
        if fill is None:
            continue
        kind_fills[k] = fill
        kind_contrasts[k] = _contrast_ratio(fill, bg)

    # Simple color distance proxy in RGB space among kind fills.
    fills = list(kind_fills.items())
    min_dist: Optional[float] = None
    for i in range(len(fills)):
        for j in range(i + 1, len(fills)):
            a = fills[i][1]
            b = fills[j][1]
            d = ((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2 + (a[2] - b[2]) ** 2) ** 0.5
            if min_dist is None or d < min_dist:
                min_dist = d

    png_gray_std: Optional[float] = None
    if png_path is not None and png_path.exists():
        pixels = _downsample_gray(png_path, (220, 130))
        if pixels:
            mean = sum(pixels) / max(1, len(pixels))
            var = sum((p - mean) ** 2 for p in pixels) / max(1, len(pixels))
            png_gray_std = var**0.5

    return {
        "phase_bar_contrast_text": _contrast_ratio(bar_fill, bar_text),
        "kind_contrasts_bg": kind_contrasts,
        "min_fill_distance_rgb": min_dist,
        "png_gray_std": png_gray_std,
    }


def measure_readability(spec_yaml: Path, config_yaml: Path, png_path: Optional[Path] = None) -> Dict[str, Any]:
    # Lightweight readability metrics: font size + density distribution.
    _ = spec_yaml
    config = load_yaml(config_yaml)

    renderer = config.get("renderer", {}) if isinstance(config.get("renderer", {}), dict) else {}
    fonts = renderer.get("fonts", {}) if isinstance(renderer.get("fonts", {}), dict) else {}
    font_size = int(fonts.get("default_size", 0) or 0)

    evaluation_cfg = config.get("evaluation", {}) if isinstance(config.get("evaluation", {}), dict) else {}
    thresholds = evaluation_cfg.get("thresholds", {}) if isinstance(evaluation_cfg.get("thresholds", {}), dict) else {}
    layout = config.get("layout", {}) if isinstance(config.get("layout", {}), dict) else {}
    min_font = int(thresholds.get("min_font_px", layout.get("min_font_size", 20)))

    # Reuse measure_roadmap density distribution if png is available (keep this module standalone).
    density: Optional[float] = None
    quadrant_density: Optional[Dict[str, float]] = None
    edge_density: Optional[Dict[str, float]] = None
    if png_path is not None and png_path.exists():
        pixels = _downsample_gray(png_path, (240, 140))
        if pixels:
            tw = 240
            th = 140

            def is_nonwhite(v: int) -> bool:
                return v < 245

            nonwhite = sum(1 for p in pixels if is_nonwhite(int(p)))
            density = nonwhite / max(1, len(pixels))

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

            band_w = max(1, int(round(tw * 0.12)))
            band_h = max(1, int(round(th * 0.12)))
            edge_density = {
                "top": block_density(0, 0, tw, min(th, band_h)),
                "bottom": block_density(0, max(0, th - band_h), tw, th),
                "left": block_density(0, 0, min(tw, band_w), th),
                "right": block_density(max(0, tw - band_w), 0, tw, th),
            }

    return {
        "font_size_px": font_size,
        "min_font_required_px": min_font,
        "density": density,
        "quadrant_density": quadrant_density,
        "edge_density": edge_density,
    }


def measure_all(
    spec_yaml: Path,
    config_yaml: Path,
    png_path: Optional[Path] = None,
) -> Dict[str, Any]:
    return {
        "structure": measure_structure(spec_yaml, config_yaml),
        "visual": measure_visual(spec_yaml, config_yaml, png_path=png_path),
        "readability": measure_readability(spec_yaml, config_yaml, png_path=png_path),
    }

