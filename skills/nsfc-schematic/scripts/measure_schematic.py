from __future__ import annotations

"""
Pure measurement collectors for nsfc-schematic main evaluator.

Design:
- Keep only deterministic computations (geometry, routing, pixel proxies).
- Do NOT decide severity (P0/P1/P2) here; that belongs to heuristic evaluators or host AI.
"""

import math
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from geometry import (
    axis_aligned_proper_cross,
    dist_segment_to_rect,
    edge_cross_count,
    pair_overlap_ratio,
    rect,
    segment_intersects_rect,
)
from routing import rect_expand, route_edge_points
from spec_parser import Edge, Node, SchematicSpec


def measure_text(spec: SchematicSpec, config: Dict[str, Any]) -> Dict[str, Any]:
    thresholds = config.get("evaluation", {}).get("thresholds", {})
    thresholds = thresholds if isinstance(thresholds, dict) else {}

    node_font = int(config.get("layout", {}).get("font", {}).get("node_label_size", 0) or 0)
    edge_font = int(config.get("layout", {}).get("font", {}).get("edge_label_size", node_font) or node_font)
    has_edge_labels = any(bool(getattr(e, "label", "").strip()) for e in spec.edges)

    scale = float(thresholds.get("print_scale_ratio", 0.5))
    min_after_scale = int(thresholds.get("print_scale_min_font", 10))

    return {
        "node_label_size": node_font,
        "edge_label_size": edge_font,
        "has_edge_labels": bool(has_edge_labels),
        "print_scale_ratio": scale,
        "print_scale_min_font": min_after_scale,
        "effective_after_scale": {"node": node_font * scale, "edge": edge_font * scale},
        # Reference thresholds only (NOT a pass/fail standard in AI mode).
        "config_bounds": {
            "min_font_px": int(thresholds.get("min_font_px", 18) or 18),
            "warn_font_px": int(thresholds.get("warn_font_px", 20) or 20),
            "min_edge_font_px": int(thresholds.get("min_edge_font_px", thresholds.get("min_font_px", 18)) or 18),
            "warn_edge_font_px": int(thresholds.get("warn_edge_font_px", thresholds.get("warn_font_px", 20)) or 20),
        },
    }


def measure_text_density(spec: SchematicSpec, config: Dict[str, Any]) -> List[Dict[str, Any]]:
    node_font = int(config.get("layout", {}).get("font", {}).get("node_label_size", 0) or 0)
    nodes = [n for g in spec.groups for n in g.children]
    out: List[Dict[str, Any]] = []
    for n in nodes:
        text = "".join(ch for ch in n.label if not ch.isspace())
        if not text:
            continue
        chars_per_line = max(1, int((max(40, n.w - 32)) / max(8, node_font * 0.6)))
        est_lines = int(math.ceil(len(text) / chars_per_line))
        required_h = est_lines * (node_font + 4) + 16
        overflow_px = int(required_h - n.h)
        out.append(
            {
                "node_id": n.id,
                "label_chars": len(text),
                "chars_per_line": int(chars_per_line),
                "estimated_lines": int(est_lines),
                "required_h": int(required_h),
                "actual_h": int(n.h),
                "overflow_px": int(overflow_px),
            }
        )
    return out


def measure_overlap(spec: SchematicSpec) -> List[Dict[str, Any]]:
    nodes = [n for g in spec.groups for n in g.children]
    out: List[Dict[str, Any]] = []
    for i in range(len(nodes)):
        for j in range(i + 1, len(nodes)):
            ratio = pair_overlap_ratio(nodes[i], nodes[j])
            if ratio > 0.0:
                out.append({"node_a": nodes[i].id, "node_b": nodes[j].id, "overlap_ratio": ratio})
    out.sort(key=lambda x: float(x.get("overlap_ratio", 0.0)), reverse=True)
    return out


def measure_canvas_bounds(spec: SchematicSpec, config: Dict[str, Any]) -> Dict[str, Any]:
    thresholds = config.get("evaluation", {}).get("thresholds", {})
    thresholds = thresholds if isinstance(thresholds, dict) else {}
    node_margin_warn = int(thresholds.get("node_margin_warn_px", 20))

    nodes = [n for g in spec.groups for n in g.children]
    out_of_bounds: List[Dict[str, Any]] = []
    near_boundary: List[Dict[str, Any]] = []

    for n in nodes:
        x1, y1 = n.x + n.w, n.y + n.h
        if n.x < 0 or n.y < 0 or x1 > spec.canvas_width or y1 > spec.canvas_height:
            out_of_bounds.append(
                {
                    "node_id": n.id,
                    "bounds": {"x": n.x, "y": n.y, "w": n.w, "h": n.h},
                }
            )
            continue
        min_margin = min(n.x, n.y, spec.canvas_width - x1, spec.canvas_height - y1)
        if min_margin < node_margin_warn:
            near_boundary.append({"node_id": n.id, "min_margin_px": int(min_margin)})

    near_boundary.sort(key=lambda x: int(x.get("min_margin_px", 1_000_000)))
    return {
        "canvas": {"w": int(spec.canvas_width), "h": int(spec.canvas_height)},
        "out_of_bounds_nodes": out_of_bounds,
        "near_boundary_nodes": near_boundary,
        "config_bounds": {"node_margin_warn_px": node_margin_warn},
    }


def measure_balance(spec: SchematicSpec) -> Dict[str, Any]:
    nodes = [n for g in spec.groups for n in g.children]
    total_area = sum(max(1, n.w * n.h) for n in nodes)
    if total_area <= 0:
        return {
            "center_of_mass": None,
            "canvas_center": {"cx": spec.canvas_width / 2.0, "cy": spec.canvas_height / 2.0},
            "offset_ratio": None,
        }

    cx = sum((n.x + n.w / 2) * (n.w * n.h) for n in nodes) / total_area
    cy = sum((n.y + n.h / 2) * (n.w * n.h) for n in nodes) / total_area
    ccx = spec.canvas_width / 2.0
    ccy = spec.canvas_height / 2.0
    dx = abs(cx - ccx) / max(1.0, ccx)
    dy = abs(cy - ccy) / max(1.0, ccy)

    return {
        "center_of_mass": {"cx": float(cx), "cy": float(cy)},
        "canvas_center": {"cx": float(ccx), "cy": float(ccy)},
        "offset_ratio": {"dx": float(dx), "dy": float(dy)},
    }


def measure_edges(spec: SchematicSpec, config: Dict[str, Any]) -> Dict[str, Any]:
    nodes = [n for g in spec.groups for n in g.children]
    node_map = {n.id: n for n in nodes}

    routing_raw = str(config.get("renderer", {}).get("internal_routing", "orthogonal"))
    routing_mode = "straight" if routing_raw == "straight" else "orthogonal"

    thresholds = config.get("evaluation", {}).get("thresholds", {})
    thresholds = thresholds if isinstance(thresholds, dict) else {}
    edge_node_min_dist = int(thresholds.get("edge_node_min_dist_px", 14))
    edge_long_diag_ratio = float(thresholds.get("edge_long_diag_warn_ratio", 0.35))
    edge_diagness_warn = float(thresholds.get("edge_diagness_warn", 0.35))

    missing_endpoints: List[Dict[str, Any]] = []
    self_loops: List[Dict[str, Any]] = []
    node_intersections: List[Dict[str, Any]] = []
    node_proximity: List[Dict[str, Any]] = []

    diag_len = math.hypot(spec.canvas_width, spec.canvas_height)
    long_diagonal_edges = 0
    lengths: List[float] = []
    diagness: List[float] = []

    edge_segs: List[Tuple[Edge, List[Tuple[Tuple[float, float], Tuple[float, float]]]]] = []

    for e in spec.edges:
        if e.source not in node_map or e.target not in node_map:
            missing_endpoints.append({"edge": f"{e.source}->{e.target}", "source_ok": e.source in node_map, "target_ok": e.target in node_map})
            continue
        if e.source == e.target:
            self_loops.append({"edge": f"{e.source}->{e.target}"})

        ns = node_map.get(e.source)
        nt = node_map.get(e.target)
        if not ns or not nt:
            continue

        src = rect(ns)
        tgt = rect(nt)
        obstacles = [rect_expand(rect(other), pad=10) for nid, other in node_map.items() if nid not in {e.source, e.target}]
        pts = route_edge_points(
            spec.direction,  # type: ignore[arg-type]
            routing_mode,  # type: ignore[arg-type]
            (int(src[0]), int(src[1]), int(src[2]), int(src[3])),
            (int(tgt[0]), int(tgt[1]), int(tgt[2]), int(tgt[3])),
            [(int(r[0]), int(r[1]), int(r[2]), int(r[3])) for r in obstacles],
            canvas_w=int(spec.canvas_width),
            canvas_h=int(spec.canvas_height),
        )

        segs: List[Tuple[Tuple[float, float], Tuple[float, float]]] = []
        total_len = 0.0
        for i in range(len(pts) - 1):
            a = (float(pts[i][0]), float(pts[i][1]))
            b = (float(pts[i + 1][0]), float(pts[i + 1][1]))
            segs.append((a, b))
            total_len += math.hypot(b[0] - a[0], b[1] - a[1])
        lengths.append(float(total_len))
        edge_segs.append((e, segs))

        if routing_mode == "straight" and segs:
            a0, b0 = segs[0][0], segs[-1][1]
            dx = abs(b0[0] - a0[0])
            dy = abs(b0[1] - a0[1])
            d = (min(dx, dy) / max(1.0, max(dx, dy))) if (dx > 0 or dy > 0) else 0.0
            diagness.append(float(d))
            if (total_len / max(1.0, diag_len) >= edge_long_diag_ratio) and (d >= edge_diagness_warn):
                long_diagonal_edges += 1
        else:
            diagness.append(0.0)

        # Route-aware segment vs other nodes.
        for nid, other in node_map.items():
            if nid in (e.source, e.target):
                continue
            r = rect(other)
            if any(segment_intersects_rect(a, b, r) for a, b in segs):
                node_intersections.append({"edge": f"{e.source}->{e.target}", "intersected_node": nid})
                break
            if segs:
                dist = min(dist_segment_to_rect(a, b, r) for a, b in segs)
                if 0.0 < dist < float(edge_node_min_dist):
                    node_proximity.append(
                        {"edge": f"{e.source}->{e.target}", "near_node": nid, "min_dist_px": float(dist)}
                    )
                    break

    # Edge-edge crossings
    crossings = 0
    if routing_mode == "straight":
        crossings = edge_cross_count(spec.edges, node_map)
    else:
        cross = 0
        for i in range(len(edge_segs)):
            e1, s1 = edge_segs[i]
            for j in range(i + 1, len(edge_segs)):
                e2, s2 = edge_segs[j]
                if len({e1.source, e1.target, e2.source, e2.target}) < 4:
                    continue
                hit = False
                for a1, a2 in s1:
                    for b1, b2 in s2:
                        if axis_aligned_proper_cross(a1, a2, b1, b2):
                            cross += 1
                            hit = True
                            break
                    if hit:
                        break
        crossings = cross

    lengths_out: Any = lengths
    if len(lengths) > 80:
        lengths_out = {
            "count": len(lengths),
            "avg": (sum(lengths) / len(lengths)) if lengths else 0.0,
            "max": max(lengths) if lengths else 0.0,
            "min": min(lengths) if lengths else 0.0,
        }

    return {
        "routing_mode": routing_mode,
        "total_edges": len(spec.edges),
        "missing_endpoints": missing_endpoints,
        "self_loops": self_loops,
        "crossings": int(crossings),
        "node_intersections": node_intersections,
        "node_proximity": node_proximity,
        "lengths": lengths_out,
        "diagness_avg": (sum(diagness) / len(diagness)) if diagness else 0.0,
        "long_diagonal_edges": int(long_diagonal_edges),
        # Reference thresholds only (NOT a pass/fail standard in AI mode).
        "config_bounds": {
            "edge_node_min_dist_px": edge_node_min_dist,
            "edge_long_diag_warn_ratio": edge_long_diag_ratio,
            "edge_diagness_warn": edge_diagness_warn,
        },
    }


def measure_visual(spec: SchematicSpec, png_path: Optional[Path]) -> Dict[str, Any]:
    if png_path is None or not png_path.exists():
        return {
            "png_path": str(png_path) if png_path else None,
            "png_size": None,
            "png_density": None,
            "png_gray_std": None,
            "expected_nodes": len([n for g in spec.groups for n in g.children]),
            "size_matches_spec": None,
        }

    try:
        from PIL import Image  # type: ignore
    except Exception:
        return {
            "png_path": str(png_path),
            "png_size": None,
            "png_density": None,
            "png_gray_std": None,
            "expected_nodes": len([n for g in spec.groups for n in g.children]),
            "size_matches_spec": None,
        }

    try:
        with Image.open(png_path) as img:
            w, h = img.size
            thumb = img.convert("L").resize((240, 140))
            pixels = list(thumb.getdata())
    except Exception:
        return {
            "png_path": str(png_path),
            "png_size": None,
            "png_density": None,
            "png_gray_std": None,
            "expected_nodes": len([n for g in spec.groups for n in g.children]),
            "size_matches_spec": None,
        }

    nonwhite = sum(1 for p in pixels if p < 245)
    density = nonwhite / max(1, len(pixels))
    mean = sum(pixels) / max(1, len(pixels))
    var = sum((p - mean) ** 2 for p in pixels) / max(1, len(pixels))
    gray_std = var**0.5
    return {
        "png_path": str(png_path),
        "png_size": {"w": int(w), "h": int(h)},
        "png_density": float(density),
        "png_gray_std": float(gray_std),
        "expected_nodes": len([n for g in spec.groups for n in g.children]),
        "size_matches_spec": bool((int(w), int(h)) == (int(spec.canvas_width), int(spec.canvas_height))),
    }


def measure_schematic(spec: SchematicSpec, config: Dict[str, Any], png_path: Optional[Path] = None) -> Dict[str, Any]:
    return {
        "measurements": {
            "text": measure_text(spec, config),
            "text_density": measure_text_density(spec, config),
            "overlap": measure_overlap(spec),
            "canvas_bounds": measure_canvas_bounds(spec, config),
            "balance": measure_balance(spec),
            "edges": measure_edges(spec, config),
            "visual": measure_visual(spec, png_path),
        }
    }
