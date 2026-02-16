from __future__ import annotations

from typing import List, Literal, Tuple


Direction = Literal["top-to-bottom", "left-to-right", "bottom-to-top"]
RoutingMode = Literal["straight", "orthogonal"]

Rect = Tuple[int, int, int, int]  # (x0, y0, x1, y1)
Point = Tuple[int, int]  # (x, y)


def rect_expand(rect: Rect, pad: int) -> Rect:
    x0, y0, x1, y1 = rect
    return (x0 - pad, y0 - pad, x1 + pad, y1 + pad)


def _segment_intersects_rect_axis_aligned(p1: Point, p2: Point, rect: Rect) -> bool:
    """
    Axis-aligned segment vs axis-aligned rect intersection.

    This matches the routing output (orthogonal segments).
    """
    x0, y0, x1, y1 = rect
    ax, ay = p1
    bx, by = p2

    if ax == bx:
        x = ax
        if x < x0 or x > x1:
            return False
        sy, ty = (ay, by) if ay <= by else (by, ay)
        return not (ty < y0 or sy > y1)

    if ay == by:
        y = ay
        if y < y0 or y > y1:
            return False
        sx, tx = (ax, bx) if ax <= bx else (bx, ax)
        return not (tx < x0 or sx > x1)

    # Fallback (should not happen for orthogonal routing).
    return False


def polyline_hits_obstacles(pts: List[Point], obstacles: List[Rect]) -> bool:
    for i in range(len(pts) - 1):
        p1 = pts[i]
        p2 = pts[i + 1]
        for rect in obstacles:
            if _segment_intersects_rect_axis_aligned(p1, p2, rect):
                return True
    return False


def _route_edge_orthogonal_ttb(
    src: Rect,
    tgt: Rect,
    obstacles: List[Rect],
    canvas_h: int,
) -> List[Point]:
    # bottom-center -> (sx, mid_y) -> (tx, mid_y) -> top-center
    sx = (src[0] + src[2]) // 2
    sy = src[3]
    tx = (tgt[0] + tgt[2]) // 2
    ty = tgt[1]

    mid = (sy + ty) // 2
    step = 40
    candidates = [mid]
    for k in range(1, 15):
        candidates.append(mid + k * step)
        candidates.append(mid - k * step)

    for my in candidates:
        if my < 0 or my > canvas_h:
            continue
        pts = [(sx, sy), (sx, my), (tx, my), (tx, ty)]
        if not polyline_hits_obstacles(pts, obstacles):
            return pts

    # Fallback: direct elbow.
    return [(sx, sy), (sx, mid), (tx, mid), (tx, ty)]


def _route_edge_orthogonal_btt(
    src: Rect,
    tgt: Rect,
    obstacles: List[Rect],
    canvas_h: int,
) -> List[Point]:
    # top-center -> (sx, mid_y) -> (tx, mid_y) -> bottom-center
    sx = (src[0] + src[2]) // 2
    sy = src[1]
    tx = (tgt[0] + tgt[2]) // 2
    ty = tgt[3]

    mid = (sy + ty) // 2
    step = 40
    candidates = [mid]
    for k in range(1, 15):
        candidates.append(mid + k * step)
        candidates.append(mid - k * step)

    for my in candidates:
        if my < 0 or my > canvas_h:
            continue
        pts = [(sx, sy), (sx, my), (tx, my), (tx, ty)]
        if not polyline_hits_obstacles(pts, obstacles):
            return pts

    return [(sx, sy), (sx, mid), (tx, mid), (tx, ty)]


def _route_edge_orthogonal_ltr(
    src: Rect,
    tgt: Rect,
    obstacles: List[Rect],
    canvas_w: int,
) -> List[Point]:
    # right-center -> (mid_x, sy) -> (mid_x, ty) -> left-center
    sx = src[2]
    sy = (src[1] + src[3]) // 2
    tx = tgt[0]
    ty = (tgt[1] + tgt[3]) // 2

    mid = (sx + tx) // 2
    step = 40
    candidates = [mid]
    for k in range(1, 15):
        candidates.append(mid + k * step)
        candidates.append(mid - k * step)

    for mx in candidates:
        if mx < 0 or mx > canvas_w:
            continue
        pts = [(sx, sy), (mx, sy), (mx, ty), (tx, ty)]
        if not polyline_hits_obstacles(pts, obstacles):
            return pts

    return [(sx, sy), (mid, sy), (mid, ty), (tx, ty)]


def route_edge_points(
    direction: Direction,
    routing: RoutingMode,
    src: Rect,
    tgt: Rect,
    obstacles: List[Rect],
    canvas_w: int,
    canvas_h: int,
) -> List[Point]:
    if routing == "straight":
        ax = (src[0] + src[2]) // 2
        ay = (src[1] + src[3]) // 2
        bx = (tgt[0] + tgt[2]) // 2
        by = (tgt[1] + tgt[3]) // 2
        return [(ax, ay), (bx, by)]

    if direction == "left-to-right":
        return _route_edge_orthogonal_ltr(src, tgt, obstacles, canvas_w=canvas_w)
    if direction == "bottom-to-top":
        return _route_edge_orthogonal_btt(src, tgt, obstacles, canvas_h=canvas_h)
    return _route_edge_orthogonal_ttb(src, tgt, obstacles, canvas_h=canvas_h)

