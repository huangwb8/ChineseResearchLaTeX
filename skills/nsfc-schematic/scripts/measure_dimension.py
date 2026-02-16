from __future__ import annotations

"""
Pure measurement collectors for nsfc-schematic multi-dimensional critiques.

Design:
- Hardcode only deterministic calculations (counts, ratios, WCAG contrast math, PNG proxies).
- Do NOT decide severity (P0/P1/P2) here; that belongs to heuristic evaluators or host AI.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from spec_parser import SchematicSpec
from color_math import contrast_ratio
from utils import hex_to_rgb


def measure_structure(spec: SchematicSpec, config: Dict[str, Any]) -> Dict[str, Any]:
    checks = (config.get("planning", {}) or {}).get("checks", {})
    checks = checks if isinstance(checks, dict) else {}

    groups = spec.groups
    nodes = [n for g in groups for n in g.children]
    edges = spec.edges

    gid = [g.id.lower() for g in groups]
    glabel = [g.label for g in groups]
    has_input = any("input" in x for x in gid) or any("输入" in x for x in glabel)
    has_output = any("output" in x for x in gid) or any("输出" in x for x in glabel)

    return {
        "groups": len(groups),
        "nodes": len(nodes),
        "edges": len(edges),
        "edge_density_ratio": (len(edges) / max(1, len(nodes))),
        "nodes_per_group": [{"group_id": g.id, "label": g.label, "count": len(g.children)} for g in groups],
        "has_input_group": bool(has_input),
        "has_output_group": bool(has_output),
        # Reference bounds only (NOT a pass/fail standard in AI mode).
        "config_bounds": {
            "groups_min": int(checks.get("groups_min", 1) or 1),
            "groups_max": int(checks.get("groups_max", 8) or 8),
            "nodes_per_group_min": int(checks.get("nodes_per_group_min", 1) or 1),
            "nodes_per_group_max": int(checks.get("nodes_per_group_max", 10) or 10),
            "total_nodes_max": int(checks.get("total_nodes_max", 30) or 30),
            "edge_density_max_ratio": float(checks.get("edge_density_max_ratio", 2.0) or 2.0),
            "require_input_output": bool(checks.get("require_input_output", False)),
        },
    }


def _safe_hex_to_rgb(v: Any) -> Optional[Tuple[int, int, int]]:
    if not isinstance(v, str):
        return None
    try:
        return hex_to_rgb(v)
    except Exception:
        return None


def _downsample_gray(png_path: Path, size: Tuple[int, int]) -> Optional[List[int]]:
    try:
        from PIL import Image  # type: ignore
    except Exception:
        return None

    try:
        with Image.open(png_path) as img:
            thumb = img.convert("L").resize(size)
            return list(thumb.getdata())
    except Exception:
        return None


def measure_visual(
    spec: SchematicSpec,
    config: Dict[str, Any],
    *,
    palette: Dict[str, Any],
    png_path: Optional[Path] = None,
) -> Dict[str, Any]:
    bg_hex = (config.get("renderer", {}) or {}).get("background", "#FFFFFF")
    bg = _safe_hex_to_rgb(bg_hex) or (255, 255, 255)
    text_hex = palette.get("text", "#1F1F1F")
    text = _safe_hex_to_rgb(text_hex) or (31, 31, 31)

    thresholds = (config.get("evaluation", {}) or {}).get("thresholds", {})
    thresholds = thresholds if isinstance(thresholds, dict) else {}
    contrast_p0 = float(thresholds.get("wcag_contrast_p0", 3.0))
    contrast_p1 = float(thresholds.get("wcag_contrast_p1", 4.5))

    used_kinds = {n.kind for g in spec.groups for n in g.children}
    per_kind: Dict[str, Any] = {}
    for kind in sorted(used_kinds):
        kind_cfg = palette.get(kind)
        if not isinstance(kind_cfg, dict):
            continue
        fill_hex = kind_cfg.get("fill")
        stroke_hex = kind_cfg.get("stroke")
        fill = _safe_hex_to_rgb(fill_hex)
        stroke = _safe_hex_to_rgb(stroke_hex)
        if fill is None:
            continue
        per_kind[str(kind)] = {
            "fill": fill_hex,
            "stroke": stroke_hex,
            "contrast_to_text": contrast_ratio(fill, text),
            "contrast_to_bg": contrast_ratio(fill, bg),
        }
        if stroke is not None:
            per_kind[str(kind)]["stroke_contrast_to_bg"] = contrast_ratio(stroke, bg)

    group_bg_contrast: Optional[float] = None
    group_bg = palette.get("group_bg", {})
    if isinstance(group_bg, dict):
        gfill = _safe_hex_to_rgb(group_bg.get("fill"))
        if gfill is not None:
            group_bg_contrast = contrast_ratio(gfill, text)

    png_gray_std: Optional[float] = None
    png_density: Optional[float] = None
    if png_path is not None and png_path.exists():
        pixels = _downsample_gray(png_path, (240, 140))
        if pixels is not None:
            mean = sum(pixels) / max(1, len(pixels))
            var = sum((p - mean) ** 2 for p in pixels) / max(1, len(pixels))
            png_gray_std = var**0.5
            nonwhite = sum(1 for p in pixels if p < 245)
            png_density = nonwhite / max(1, len(pixels))

    return {
        "background": str(bg_hex),
        "text": str(text_hex),
        "per_kind_contrast": per_kind,
        "group_bg_contrast_to_text": group_bg_contrast,
        "png_gray_std": png_gray_std,
        "png_density": png_density,
        "wcag_thresholds": {"p0": contrast_p0, "p1": contrast_p1},
    }


def measure_readability(
    spec: SchematicSpec,
    config: Dict[str, Any],
    *,
    png_path: Optional[Path] = None,
) -> Dict[str, Any]:
    thresholds = (config.get("evaluation", {}) or {}).get("thresholds", {})
    thresholds = thresholds if isinstance(thresholds, dict) else {}
    crowded_p1 = float(thresholds.get("crowded_density_p1", 0.35))
    crowded_p0 = float(thresholds.get("crowded_density_p0", 0.45))

    font_cfg = (config.get("layout", {}) or {}).get("font", {})
    font_cfg = font_cfg if isinstance(font_cfg, dict) else {}
    node_font = int(font_cfg.get("node_label_size", 0) or 0)
    edge_font = int(font_cfg.get("edge_label_size", node_font) or node_font)
    has_edge_labels = any(bool(getattr(e, "label", "").strip()) for e in spec.edges)

    # Optional PNG proxy: keep it consistent with evaluate_dimension.py.
    png_density: Optional[float] = None
    if png_path is not None and png_path.exists():
        pixels = _downsample_gray(png_path, (240, 140))
        if pixels is not None:
            nonwhite = sum(1 for p in pixels if p < 245)
            png_density = nonwhite / max(1, len(pixels))

    return {
        "node_label_size": node_font,
        "edge_label_size": edge_font,
        "has_edge_labels": bool(has_edge_labels),
        "png_density": png_density,
        # Reference bounds only (NOT a pass/fail standard in AI mode).
        "config_bounds": {
            "min_font_px": int(thresholds.get("min_font_px", 18) or 18),
            "warn_font_px": int(thresholds.get("warn_font_px", 20) or 20),
            "min_edge_font_px": int(thresholds.get("min_edge_font_px", thresholds.get("min_font_px", 18)) or 18),
            "warn_edge_font_px": int(thresholds.get("warn_edge_font_px", thresholds.get("warn_font_px", 20)) or 20),
        },
        "crowded_thresholds": {"p1": crowded_p1, "p0": crowded_p0},
    }
