from __future__ import annotations

"""
Shared deterministic geometry helpers.

Why:
- Keep measurement collectors and heuristic evaluators consistent.
- Avoid subtle drift when the same math is implemented in multiple files.
"""

import math
from typing import Dict, List, Tuple

from spec_parser import Edge, Node


def pair_overlap_ratio(a: Node, b: Node) -> float:
    ax1, ay1 = a.x + a.w, a.y + a.h
    bx1, by1 = b.x + b.w, b.y + b.h

    ix0 = max(a.x, b.x)
    iy0 = max(a.y, b.y)
    ix1 = min(ax1, bx1)
    iy1 = min(ay1, by1)
    if ix1 <= ix0 or iy1 <= iy0:
        return 0.0

    inter = (ix1 - ix0) * (iy1 - iy0)
    denom = min(a.w * a.h, b.w * b.h)
    return inter / max(1, denom)


def center(n: Node) -> Tuple[float, float]:
    return (n.x + n.w / 2.0, n.y + n.h / 2.0)


def _orientation(a: Tuple[float, float], b: Tuple[float, float], c: Tuple[float, float]) -> float:
    return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])


def _segments_intersect(
    p1: Tuple[float, float],
    p2: Tuple[float, float],
    p3: Tuple[float, float],
    p4: Tuple[float, float],
) -> bool:
    o1 = _orientation(p1, p2, p3)
    o2 = _orientation(p1, p2, p4)
    o3 = _orientation(p3, p4, p1)
    o4 = _orientation(p3, p4, p2)
    return (o1 * o2 < 0) and (o3 * o4 < 0)


def edge_cross_count(edges: List[Edge], node_map: Dict[str, Node]) -> int:
    count = 0
    for i in range(len(edges)):
        for j in range(i + 1, len(edges)):
            e1 = edges[i]
            e2 = edges[j]
            if len({e1.source, e1.target, e2.source, e2.target}) < 4:
                continue
            n1s = node_map.get(e1.source)
            n1t = node_map.get(e1.target)
            n2s = node_map.get(e2.source)
            n2t = node_map.get(e2.target)
            if not all((n1s, n1t, n2s, n2t)):
                continue
            if _segments_intersect(center(n1s), center(n1t), center(n2s), center(n2t)):
                count += 1
    return count


def axis_aligned_proper_cross(
    a1: Tuple[float, float],
    a2: Tuple[float, float],
    b1: Tuple[float, float],
    b2: Tuple[float, float],
    *,
    eps: float = 1e-6,
) -> bool:
    """
    Proper crossing for axis-aligned segments (orthogonal routing):
    - Only count vertical vs horizontal intersections
    - Exclude endpoint-only touching (strict interior intersection)
    - Ignore collinear overlaps
    """
    ax0, ay0 = a1
    ax1, ay1 = a2
    bx0, by0 = b1
    bx1, by1 = b2

    a_vert = abs(ax0 - ax1) < eps and abs(ay0 - ay1) > eps
    a_horz = abs(ay0 - ay1) < eps and abs(ax0 - ax1) > eps
    b_vert = abs(bx0 - bx1) < eps and abs(by0 - by1) > eps
    b_horz = abs(by0 - by1) < eps and abs(bx0 - bx1) > eps

    if a_vert and b_horz:
        x = ax0
        y = by0
        ay_min, ay_max = (ay0, ay1) if ay0 <= ay1 else (ay1, ay0)
        bx_min, bx_max = (bx0, bx1) if bx0 <= bx1 else (bx1, bx0)
        return (ay_min + eps) < y < (ay_max - eps) and (bx_min + eps) < x < (bx_max - eps)

    if a_horz and b_vert:
        x = bx0
        y = ay0
        ax_min, ax_max = (ax0, ax1) if ax0 <= ax1 else (ax1, ax0)
        by_min, by_max = (by0, by1) if by0 <= by1 else (by1, by0)
        return (ax_min + eps) < x < (ax_max - eps) and (by_min + eps) < y < (by_max - eps)

    return False


def rect(n: Node) -> Tuple[float, float, float, float]:
    return (float(n.x), float(n.y), float(n.x + n.w), float(n.y + n.h))


def _point_in_rect(p: Tuple[float, float], r: Tuple[float, float, float, float]) -> bool:
    x, y = p
    x0, y0, x1, y1 = r
    return (x0 <= x <= x1) and (y0 <= y <= y1)


def _on_segment(a: Tuple[float, float], b: Tuple[float, float], c: Tuple[float, float]) -> bool:
    return min(a[0], b[0]) <= c[0] <= max(a[0], b[0]) and min(a[1], b[1]) <= c[1] <= max(a[1], b[1])


def _segments_intersect_inclusive(
    p1: Tuple[float, float],
    p2: Tuple[float, float],
    p3: Tuple[float, float],
    p4: Tuple[float, float],
) -> bool:
    o1 = _orientation(p1, p2, p3)
    o2 = _orientation(p1, p2, p4)
    o3 = _orientation(p3, p4, p1)
    o4 = _orientation(p3, p4, p2)

    if (o1 * o2 < 0) and (o3 * o4 < 0):
        return True

    eps = 1e-9
    if abs(o1) < eps and _on_segment(p1, p2, p3):
        return True
    if abs(o2) < eps and _on_segment(p1, p2, p4):
        return True
    if abs(o3) < eps and _on_segment(p3, p4, p1):
        return True
    if abs(o4) < eps and _on_segment(p3, p4, p2):
        return True
    return False


def segment_intersects_rect(
    a: Tuple[float, float],
    b: Tuple[float, float],
    r: Tuple[float, float, float, float],
) -> bool:
    if _point_in_rect(a, r) or _point_in_rect(b, r):
        return True
    x0, y0, x1, y1 = r
    edges = [
        ((x0, y0), (x1, y0)),
        ((x1, y0), (x1, y1)),
        ((x1, y1), (x0, y1)),
        ((x0, y1), (x0, y0)),
    ]
    return any(_segments_intersect_inclusive(a, b, e0, e1) for e0, e1 in edges)


def _dist_point_to_segment(p: Tuple[float, float], a: Tuple[float, float], b: Tuple[float, float]) -> float:
    px, py = p
    ax, ay = a
    bx, by = b
    vx = bx - ax
    vy = by - ay
    denom = vx * vx + vy * vy
    if denom <= 1e-12:
        return math.hypot(px - ax, py - ay)
    t = ((px - ax) * vx + (py - ay) * vy) / denom
    t = max(0.0, min(1.0, t))
    cx = ax + t * vx
    cy = ay + t * vy
    return math.hypot(px - cx, py - cy)


def _dist_segment_to_segment(
    a1: Tuple[float, float],
    a2: Tuple[float, float],
    b1: Tuple[float, float],
    b2: Tuple[float, float],
) -> float:
    if _segments_intersect_inclusive(a1, a2, b1, b2):
        return 0.0
    return min(
        _dist_point_to_segment(a1, b1, b2),
        _dist_point_to_segment(a2, b1, b2),
        _dist_point_to_segment(b1, a1, a2),
        _dist_point_to_segment(b2, a1, a2),
    )


def dist_segment_to_rect(
    a: Tuple[float, float],
    b: Tuple[float, float],
    r: Tuple[float, float, float, float],
) -> float:
    if segment_intersects_rect(a, b, r):
        return 0.0
    x0, y0, x1, y1 = r
    edges = [
        ((x0, y0), (x1, y0)),
        ((x1, y0), (x1, y1)),
        ((x1, y1), (x0, y1)),
        ((x0, y1), (x0, y0)),
    ]
    return min(_dist_segment_to_segment(a, b, e0, e1) for e0, e1 in edges)

