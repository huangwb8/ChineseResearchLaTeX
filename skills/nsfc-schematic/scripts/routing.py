from __future__ import annotations

import math
from typing import List, Literal, Optional, Tuple


Direction = Literal["top-to-bottom", "left-to-right", "bottom-to-top"]
RoutingMode = Literal["straight", "orthogonal"]

Rect = Tuple[int, int, int, int]  # (x0, y0, x1, y1)
Point = Tuple[int, int]  # (x, y)

_CJK_RANGES: tuple[tuple[int, int], ...] = (
    (0x4E00, 0x9FFF),
    (0x3400, 0x4DBF),
    (0xF900, 0xFAFF),
)


def rect_expand(rect: Rect, pad: int) -> Rect:
    x0, y0, x1, y1 = rect
    return (x0 - pad, y0 - pad, x1 + pad, y1 + pad)


def _clamp(v: int, lo: int, hi: int) -> int:
    if v < lo:
        return lo
    if v > hi:
        return hi
    return v


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


def polyline_hit_count(pts: List[Point], obstacles: List[Rect]) -> int:
    hits = 0
    for i in range(len(pts) - 1):
        p1 = pts[i]
        p2 = pts[i + 1]
        for rect in obstacles:
            if _segment_intersects_rect_axis_aligned(p1, p2, rect):
                hits += 1
                break
    return hits


def polyline_hits_obstacles(pts: List[Point], obstacles: List[Rect]) -> bool:
    return polyline_hit_count(pts, obstacles) > 0


def _dedup_points(pts: List[Point]) -> List[Point]:
    if not pts:
        return []
    out = [pts[0]]
    for p in pts[1:]:
        if p != out[-1]:
            out.append(p)
    return out


def _polyline_length(pts: List[Point]) -> float:
    total = 0.0
    for i in range(len(pts) - 1):
        total += math.hypot(pts[i + 1][0] - pts[i][0], pts[i + 1][1] - pts[i][1])
    return total


def _polyline_turn_count(pts: List[Point]) -> int:
    turns = 0
    for i in range(1, len(pts) - 1):
        ax = pts[i][0] - pts[i - 1][0]
        ay = pts[i][1] - pts[i - 1][1]
        bx = pts[i + 1][0] - pts[i][0]
        by = pts[i + 1][1] - pts[i][1]
        if (ax == 0 and by == 0) or (ay == 0 and bx == 0):
            turns += 1
    return turns


def _polyline_center_bias(pts: List[Point], canvas_w: int, canvas_h: int) -> float:
    if not pts:
        return 0.0
    cx = canvas_w / 2.0
    cy = canvas_h / 2.0
    diag = max(1.0, math.hypot(canvas_w, canvas_h))
    # Larger => farther from center (more likely to use "outer corridor").
    return sum(math.hypot(float(x) - cx, float(y) - cy) for x, y in pts) / (len(pts) * diag)


def _score_candidate(
    pts: List[Point],
    obstacles: List[Rect],
    *,
    canvas_w: int,
    canvas_h: int,
    prefer_outer: bool,
) -> Tuple[int, int, int, float]:
    hits = polyline_hit_count(pts, obstacles)
    turns = _polyline_turn_count(pts)
    length = int(round(_polyline_length(pts)))
    center_bias = _polyline_center_bias(pts, canvas_w, canvas_h)
    # For aux/risk, prefer farther from center (outer corridor) when tie-breaking.
    center_rank = -center_bias if prefer_outer else center_bias
    return (hits, turns, length, center_rank)


def _pick_best_candidate(
    candidates: List[List[Point]],
    obstacles: List[Rect],
    *,
    canvas_w: int,
    canvas_h: int,
    prefer_outer: bool,
) -> Optional[List[Point]]:
    best: Optional[List[Point]] = None
    best_score: Optional[Tuple[int, int, int, float]] = None
    for pts in candidates:
        pts = _dedup_points(pts)
        if len(pts) < 2:
            continue
        score = _score_candidate(pts, obstacles, canvas_w=canvas_w, canvas_h=canvas_h, prefer_outer=prefer_outer)
        if best_score is None or score < best_score:
            best = pts
            best_score = score
    return best


def _route_edge_orthogonal_ttb(
    src: Rect,
    tgt: Rect,
    obstacles: List[Rect],
    *,
    canvas_w: int,
    canvas_h: int,
    prefer_outer: bool,
) -> List[Point]:
    sx = (src[0] + src[2]) // 2
    sy = src[3]
    tx = (tgt[0] + tgt[2]) // 2
    ty = tgt[1]

    step = 40
    mid = (sy + ty) // 2
    candidates: List[List[Point]] = []

    y_candidates = [mid]
    for k in range(1, 16):
        y_candidates.append(mid + k * step)
        y_candidates.append(mid - k * step)

    for my in y_candidates:
        if 0 <= my <= canvas_h:
            candidates.append([(sx, sy), (sx, my), (tx, my), (tx, ty)])

    sign = 1 if ty >= sy else -1
    escape = max(36, step)
    y1 = _clamp(sy + sign * escape, 0, canvas_h)
    y2 = _clamp(ty - sign * escape, 0, canvas_h)
    edge_margin = 24
    x_corridors = [
        min(sx, tx) - 120,
        max(sx, tx) + 120,
        min(sx, tx) - 220,
        max(sx, tx) + 220,
        edge_margin,
        canvas_w - edge_margin,
    ]
    for cx0 in x_corridors:
        cx = _clamp(cx0, 0, canvas_w)
        candidates.append([(sx, sy), (sx, y1), (cx, y1), (cx, y2), (tx, y2), (tx, ty)])

    best = _pick_best_candidate(candidates, obstacles, canvas_w=canvas_w, canvas_h=canvas_h, prefer_outer=prefer_outer)
    if best:
        return best
    return [(sx, sy), (sx, mid), (tx, mid), (tx, ty)]


def _route_edge_orthogonal_btt(
    src: Rect,
    tgt: Rect,
    obstacles: List[Rect],
    *,
    canvas_w: int,
    canvas_h: int,
    prefer_outer: bool,
) -> List[Point]:
    sx = (src[0] + src[2]) // 2
    sy = src[1]
    tx = (tgt[0] + tgt[2]) // 2
    ty = tgt[3]

    step = 40
    mid = (sy + ty) // 2
    candidates: List[List[Point]] = []

    y_candidates = [mid]
    for k in range(1, 16):
        y_candidates.append(mid + k * step)
        y_candidates.append(mid - k * step)

    for my in y_candidates:
        if 0 <= my <= canvas_h:
            candidates.append([(sx, sy), (sx, my), (tx, my), (tx, ty)])

    sign = 1 if ty >= sy else -1
    escape = max(36, step)
    y1 = _clamp(sy + sign * escape, 0, canvas_h)
    y2 = _clamp(ty - sign * escape, 0, canvas_h)
    edge_margin = 24
    x_corridors = [
        min(sx, tx) - 120,
        max(sx, tx) + 120,
        min(sx, tx) - 220,
        max(sx, tx) + 220,
        edge_margin,
        canvas_w - edge_margin,
    ]
    for cx0 in x_corridors:
        cx = _clamp(cx0, 0, canvas_w)
        candidates.append([(sx, sy), (sx, y1), (cx, y1), (cx, y2), (tx, y2), (tx, ty)])

    best = _pick_best_candidate(candidates, obstacles, canvas_w=canvas_w, canvas_h=canvas_h, prefer_outer=prefer_outer)
    if best:
        return best
    return [(sx, sy), (sx, mid), (tx, mid), (tx, ty)]


def _route_edge_orthogonal_ltr(
    src: Rect,
    tgt: Rect,
    obstacles: List[Rect],
    *,
    canvas_w: int,
    canvas_h: int,
    prefer_outer: bool,
) -> List[Point]:
    sx = src[2]
    sy = (src[1] + src[3]) // 2
    tx = tgt[0]
    ty = (tgt[1] + tgt[3]) // 2

    step = 40
    mid = (sx + tx) // 2
    candidates: List[List[Point]] = []

    x_candidates = [mid]
    for k in range(1, 16):
        x_candidates.append(mid + k * step)
        x_candidates.append(mid - k * step)

    for mx in x_candidates:
        if 0 <= mx <= canvas_w:
            candidates.append([(sx, sy), (mx, sy), (mx, ty), (tx, ty)])

    sign = 1 if tx >= sx else -1
    escape = max(36, step)
    x1 = _clamp(sx + sign * escape, 0, canvas_w)
    x2 = _clamp(tx - sign * escape, 0, canvas_w)
    edge_margin = 24
    y_corridors = [
        min(sy, ty) - 120,
        max(sy, ty) + 120,
        min(sy, ty) - 220,
        max(sy, ty) + 220,
        edge_margin,
        canvas_h - edge_margin,
    ]
    for cy0 in y_corridors:
        cy = _clamp(cy0, 0, canvas_h)
        candidates.append([(sx, sy), (x1, sy), (x1, cy), (x2, cy), (x2, ty), (tx, ty)])

    best = _pick_best_candidate(candidates, obstacles, canvas_w=canvas_w, canvas_h=canvas_h, prefer_outer=prefer_outer)
    if best:
        return best
    return [(sx, sy), (mid, sy), (mid, ty), (tx, ty)]


def route_edge_points(
    direction: Direction,
    routing: RoutingMode,
    src: Rect,
    tgt: Rect,
    obstacles: List[Rect],
    canvas_w: int,
    canvas_h: int,
    *,
    edge_kind: Optional[str] = None,
) -> List[Point]:
    if routing == "straight":
        ax = (src[0] + src[2]) // 2
        ay = (src[1] + src[3]) // 2
        bx = (tgt[0] + tgt[2]) // 2
        by = (tgt[1] + tgt[3]) // 2
        return [(ax, ay), (bx, by)]

    prefer_outer = str(edge_kind or "").strip().lower() in {"aux", "risk"}

    if direction == "left-to-right":
        return _route_edge_orthogonal_ltr(
            src,
            tgt,
            obstacles,
            canvas_w=canvas_w,
            canvas_h=canvas_h,
            prefer_outer=prefer_outer,
        )
    if direction == "bottom-to-top":
        return _route_edge_orthogonal_btt(
            src,
            tgt,
            obstacles,
            canvas_w=canvas_w,
            canvas_h=canvas_h,
            prefer_outer=prefer_outer,
        )
    return _route_edge_orthogonal_ttb(
        src,
        tgt,
        obstacles,
        canvas_w=canvas_w,
        canvas_h=canvas_h,
        prefer_outer=prefer_outer,
    )


def _contains_cjk(text: str) -> bool:
    for ch in text:
        code = ord(ch)
        for lo, hi in _CJK_RANGES:
            if lo <= code <= hi:
                return True
    return False


def label_bbox_from_anchor(
    anchor: Point,
    text: str,
    font_px: int,
    *,
    padding_px: int = 4,
) -> Rect:
    body = (text or "").strip()
    size = max(8, int(font_px))
    if not body:
        w = max(12, size)
        h = max(12, size)
    else:
        char_w = size * (0.95 if _contains_cjk(body) else 0.62)
        w = int(max(16, len(body) * char_w + padding_px * 2))
        h = int(max(14, size * 1.35 + padding_px * 2))
    x = int(anchor[0])
    y = int(anchor[1])
    return (x - w // 2, y - h // 2, x + w // 2, y + h // 2)


def _bbox_intersects(a: Rect, b: Rect) -> bool:
    return not (a[2] <= b[0] or a[0] >= b[2] or a[3] <= b[1] or a[1] >= b[3])


def _bbox_distance(a: Rect, b: Rect) -> float:
    dx = 0
    if a[2] < b[0]:
        dx = b[0] - a[2]
    elif b[2] < a[0]:
        dx = a[0] - b[2]
    dy = 0
    if a[3] < b[1]:
        dy = b[1] - a[3]
    elif b[3] < a[1]:
        dy = a[1] - b[3]
    return math.hypot(float(dx), float(dy))


def choose_edge_label_anchor(
    pts: List[Point],
    *,
    text: str,
    font_px: int,
    obstacles: List[Rect],
    canvas_w: int,
    canvas_h: int,
) -> Point:
    if len(pts) < 2:
        return pts[0] if pts else (canvas_w // 2, canvas_h // 2)

    candidates: List[Point] = []
    for i in range(len(pts) - 1):
        ax, ay = pts[i]
        bx, by = pts[i + 1]
        mx = (ax + bx) // 2
        my = (ay + by) // 2
        candidates.append((mx, my))
        # Add extra anchors on long segments to increase odds of finding a free area.
        if abs(ax - bx) + abs(ay - by) >= 160:
            candidates.append((int(round(ax * 0.7 + bx * 0.3)), int(round(ay * 0.7 + by * 0.3))))
            candidates.append((int(round(ax * 0.3 + bx * 0.7)), int(round(ay * 0.3 + by * 0.7))))

    # Default center as a fallback candidate.
    candidates.append(((pts[0][0] + pts[-1][0]) // 2, (pts[0][1] + pts[-1][1]) // 2))

    best = candidates[-1]
    best_score: Optional[Tuple[int, int, float]] = None

    canvas_rect = (0, 0, int(canvas_w), int(canvas_h))
    for c in candidates:
        bbox = label_bbox_from_anchor(c, text, font_px)
        overlap = 0
        min_clear = 1e9
        for r in obstacles:
            if _bbox_intersects(bbox, r):
                overlap += 1
                min_clear = 0.0
            else:
                min_clear = min(min_clear, _bbox_distance(bbox, r))

        out_penalty = 0
        if bbox[0] < canvas_rect[0] or bbox[1] < canvas_rect[1] or bbox[2] > canvas_rect[2] or bbox[3] > canvas_rect[3]:
            out_penalty = 1

        score = (overlap, out_penalty, -min_clear)
        if best_score is None or score < best_score:
            best_score = score
            best = c

    return best
