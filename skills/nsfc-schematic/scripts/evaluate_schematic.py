from __future__ import annotations

from dataclasses import asdict, dataclass
import math
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from geometry import (
    axis_aligned_proper_cross as _axis_aligned_proper_cross,
    center as _center,
    dist_segment_to_rect as _dist_segment_to_rect,
    edge_cross_count as _edge_cross_count,
    pair_overlap_ratio as _pair_overlap_ratio,
    rect as _rect,
    segment_intersects_rect as _segment_intersects_rect,
)
from spec_parser import Edge, Node, SchematicSpec
from routing import rect_expand, route_edge_points


@dataclass
class Defect:
    severity: str  # P0/P1/P2
    where: str
    message: str
    dimension: str


def _visual_score(
    png_path: Optional[Path],
    min_w: int,
    min_h: int,
    expected_nodes: int,
    thresholds: Dict[str, Any],
    defects: List[Defect],
) -> int:
    if png_path is None or not png_path.exists():
        defects.append(
            Defect(
                severity="P2",
                where="global",
                message="未提供 PNG，跳过视觉评估（建议启用渲染产物评估）",
                dimension="overall_aesthetics",
            )
        )
        return 70

    try:
        from PIL import Image  # type: ignore
    except Exception as exc:  # pragma: no cover
        defects.append(
            Defect(
                severity="P2",
                where="global",
                message=f"缺少 Pillow，跳过 PNG 视觉评估（{exc}）",
                dimension="overall_aesthetics",
            )
        )
        return 70

    try:
        with Image.open(png_path) as img:
            w, h = img.size
            # Downsample for quick density proxy.
            thumb = img.convert("L").resize((240, 140))
            pixels = list(thumb.getdata())
    except Exception as exc:
        defects.append(
            Defect(
                severity="P1",
                where="global",
                message=f"PNG 读取失败：{exc}",
                dimension="overall_aesthetics",
            )
        )
        return 60

    score = 85
    if w < min_w or h < min_h:
        defects.append(
            Defect(
                severity="P1",
                where="global",
                message=f"分辨率偏低：{w}x{h}，建议至少 {min_w}x{min_h}",
                dimension="overall_aesthetics",
            )
        )
        score -= 15

    # Crowding proxy: too many non-background pixels after downsample.
    # This is intentionally weak (P2/P1) and should not dominate overall score.
    nonwhite = sum(1 for p in pixels if p < 245)
    density = nonwhite / max(1, len(pixels))
    if density > 0.35:
        defects.append(
            Defect(
                severity="P1",
                where="global",
                message=f"画面元素偏拥挤（像素密度={density:.2f}），建议增加画布/间距或缩短文案",
                dimension="overall_aesthetics",
            )
        )
        score -= 10
    else:
        blank_min_nodes = int(thresholds.get("blank_check_min_nodes", 6))
        blank_p0 = float(thresholds.get("blank_density_p0", 0.01))
        blank_p1 = float(thresholds.get("blank_density_p1", 0.02))

        # If the spec contains plenty of nodes, but the rendered PNG is near-blank,
        # it's usually a rendering failure (e.g. illegal drawio XML or CLI partial parse).
        if expected_nodes >= blank_min_nodes and density < blank_p0:
            defects.append(
                Defect(
                    severity="P0",
                    where="global",
                    message=(
                        f"疑似渲染内容缺失/被忽略：spec.nodes={expected_nodes} 但像素密度={density:.3f}。"
                        "请优先检查 schematic.drawio 是否为合法 XML（常见原因：label 含未转义的 <br>/< 等）。"
                    ),
                    dimension="overall_aesthetics",
                )
            )
            score -= 35
        elif expected_nodes >= blank_min_nodes and density < blank_p1:
            defects.append(
                Defect(
                    severity="P1",
                    where="global",
                    message=(
                        f"疑似渲染内容偏少：spec.nodes={expected_nodes} 但像素密度={density:.3f}。"
                        "建议检查 schematic.drawio 合法性与 draw.io CLI stderr。"
                    ),
                    dimension="overall_aesthetics",
                )
            )
            score -= 18
        elif density < 0.05:
            defects.append(
                Defect(
                    severity="P2",
                    where="global",
                    message=f"画面元素偏稀疏（像素密度={density:.2f}），可考虑收紧间距提升信息密度",
                    dimension="overall_aesthetics",
                )
            )
            score -= 3

    return max(0, min(100, score))


def _check_print_readability(config: Dict[str, Any], defects: List[Defect], *, has_edge_labels: bool) -> None:
    """Check readability after print scaling (e.g. A4 shrink)."""
    thresholds = config.get("evaluation", {}).get("thresholds", {})
    if not isinstance(thresholds, dict):
        return
    if not bool(thresholds.get("print_scale_check", False)):
        return

    try:
        node_font = int(config["layout"]["font"]["node_label_size"])
        edge_font = int(config["layout"]["font"].get("edge_label_size", node_font))
    except Exception:
        return

    scale = float(thresholds.get("print_scale_ratio", 0.5))
    min_after_scale = int(thresholds.get("print_scale_min_font", 10))

    effective_node = node_font * scale
    if effective_node < float(min_after_scale):
        suggest = int(math.ceil(min_after_scale / max(1e-9, scale)))
        defects.append(
            Defect(
                severity="P1",
                where="global",
                message=(
                    f"缩印后节点字号可能过小：{node_font}px × {scale} = {effective_node:.1f}px < 建议值 {min_after_scale}px。"
                    f"建议将 node_label_size 提升至 {suggest}px。"
                ),
                dimension="print_readability",
            )
        )

    if has_edge_labels:
        effective_edge = edge_font * scale
        if effective_edge < float(min_after_scale):
            suggest = int(math.ceil(min_after_scale / max(1e-9, scale)))
            defects.append(
                Defect(
                    severity="P0",
                    where="global",
                    message=(
                        f"缩印后连线标签字号过小：{edge_font}px × {scale} = {effective_edge:.1f}px < 建议值 {min_after_scale}px。"
                        f"建议将 edge_label_size 提升至 {suggest}px。"
                    ),
                    dimension="print_readability",
                )
            )


def evaluate_schematic(
    spec: SchematicSpec,
    config: Dict[str, Any],
    png_path: Optional[Path] = None,
    *,
    protocol_dir: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    Evaluate schematic quality.

    Notes:
    - Default mode is heuristic and returns the legacy output schema.
    - When config.yaml enables evaluation.evaluation_mode=ai, this function will still
      return an evaluation (heuristic fallback if no valid AI response is provided),
      while optionally emitting measurements / request templates via output_dir.
    """
    mode = str((config.get("evaluation", {}) or {}).get("evaluation_mode", "heuristic")).strip().lower() or "heuristic"
    if mode != "ai":
        out = evaluate_schematic_heuristic(spec, config, png_path)
        out.setdefault("evaluation_mode_requested", mode)
        out.setdefault("evaluation_source", "heuristic")
        return out

    # AI mode (offline protocol): script emits pure measurements + request/response templates,
    # and consumes ai_evaluation_response.json if user/host AI provides one.
    output_dir: Optional[Path] = protocol_dir
    if output_dir is None:
        # Backward-compatible internal hook (older callers may inject this key).
        out_dir = config.get("_output_dir")
        output_dir = out_dir if isinstance(out_dir, Path) else None

    return evaluate_schematic_ai_adapter(spec, config, png_path=png_path, output_dir=output_dir)


def evaluate_schematic_heuristic(
    spec: SchematicSpec,
    config: Dict[str, Any],
    png_path: Optional[Path] = None,
) -> Dict[str, Any]:
    defects: List[Defect] = []
    metrics: Dict[str, Any] = {}

    nodes = [n for g in spec.groups for n in g.children]
    node_map = {n.id: n for n in nodes}
    routing_raw = str(config.get("renderer", {}).get("internal_routing", "orthogonal"))
    routing_mode = "straight" if routing_raw == "straight" else "orthogonal"
    metrics["routing_mode"] = routing_mode

    evaluation_cfg = config.get("evaluation", {})
    if not isinstance(evaluation_cfg, dict):
        raise ValueError("config.yaml:evaluation 必须为 mapping")
    thresholds = evaluation_cfg.get("thresholds", {})
    if not isinstance(thresholds, dict):
        thresholds = {}
    min_font = int(thresholds.get("min_font_px", 18))
    warn_font = int(thresholds.get("warn_font_px", 20))
    min_edge_font = int(thresholds.get("min_edge_font_px", min_font))
    warn_edge_font = int(thresholds.get("warn_edge_font_px", warn_font))
    node_margin_warn = int(thresholds.get("node_margin_warn_px", 20))
    balance_warn = float(thresholds.get("balance_warn_ratio", 0.4))
    edge_node_min_dist = int(thresholds.get("edge_node_min_dist_px", 14))
    edge_long_diag_ratio = float(thresholds.get("edge_long_diag_warn_ratio", 0.35))
    edge_diagness_warn = float(thresholds.get("edge_diagness_warn", 0.35))

    # Export resolution sanity check (helps keep scoring stable across draw.io CLI variations).
    if png_path is not None and png_path.exists() and png_path.is_file():
        try:
            from PIL import Image  # type: ignore

            with Image.open(png_path) as im:
                pw, ph = im.size
            metrics["png_size"] = {"w": pw, "h": ph}
            if (pw, ph) != (int(spec.canvas_width), int(spec.canvas_height)):
                defects.append(
                    Defect(
                        severity="P1",
                        where="global",
                        message=(
                            f"PNG 导出尺寸与 spec 不一致：png={pw}x{ph} vs spec={spec.canvas_width}x{spec.canvas_height}。"
                            "建议检查 draw.io CLI 导出参数或启用内置尺寸修正。"
                        ),
                        dimension="export_resolution",
                    )
                )
        except Exception:
            # Non-fatal: keep evaluation usable even without PIL or on corrupted images.
            pass

    # 1) text readability
    node_font = int(config["layout"]["font"]["node_label_size"])
    edge_font = int(config["layout"]["font"].get("edge_label_size", node_font))
    has_edge_labels = any(bool(e.label.strip()) for e in spec.edges)
    if node_font < min_font:
        defects.append(
            Defect(
                severity="P0",
                where="global",
                message=f"节点字号过小：{node_font}px < {min_font}px",
                dimension="text_readability",
            )
        )
    elif node_font < warn_font:
        defects.append(
            Defect(
                severity="P1",
                where="global",
                message=f"节点字号偏小：{node_font}px < 建议值 {warn_font}px",
                dimension="text_readability",
            )
        )

    if has_edge_labels:
        if edge_font < min_edge_font:
            defects.append(
                Defect(
                    severity="P0",
                    where="global",
                    message=f"连线标签字号过小：{edge_font}px < {min_edge_font}px",
                    dimension="text_readability",
                )
            )
        elif edge_font < warn_edge_font:
            defects.append(
                Defect(
                    severity="P1",
                    where="global",
                    message=f"连线标签字号偏小：{edge_font}px < 建议值 {warn_edge_font}px",
                    dimension="text_readability",
                )
            )

    _check_print_readability(config, defects, has_edge_labels=has_edge_labels)

    # 1b) text density proxy (crowding inside node bounds)
    crowded_nodes = 0
    for n in nodes:
        text = "".join(ch for ch in n.label if not ch.isspace())
        if not text:
            continue
        # Approximate chars-per-line and required height.
        # Keep the proxy conservative: account for label padding/spacing.
        chars_per_line = max(1, int((max(40, n.w - 32)) / max(8, node_font * 0.6)))
        est_lines = int(math.ceil(len(text) / chars_per_line))
        required_h = est_lines * (node_font + 4) + 16
        if required_h > n.h:
            crowded_nodes += 1
            overflow_px = required_h - n.h
            sev = "P0" if overflow_px >= max(10, node_font) else "P1"
            defects.append(
                Defect(
                    severity=sev,
                    where=f"node:{n.id}",
                    message=(
                        f"节点文案可能溢出/遮挡（估算需要高度≈{required_h}px > 实际 {n.h}px）。"
                        "建议缩短文案或增大节点（本技能默认会自动扩容），必要时加大画布/间距。"
                    ),
                    dimension="text_overflow",
                )
            )

    # 2) overlap detection
    for i in range(len(nodes)):
        for j in range(i + 1, len(nodes)):
            ratio = _pair_overlap_ratio(nodes[i], nodes[j])
            if ratio > 0.10:
                defects.append(
                    Defect(
                        severity="P0",
                        where=f"node:{nodes[i].id}|{nodes[j].id}",
                        message=f"节点重叠比例过高：{ratio:.1%}",
                        dimension="node_overlap",
                    )
                )
            elif ratio > 0.0:
                defects.append(
                    Defect(
                        severity="P1",
                        where=f"node:{nodes[i].id}|{nodes[j].id}",
                        message=f"存在轻微重叠：{ratio:.1%}",
                        dimension="node_overlap",
                    )
                )

    # 3) edge completeness/crossing
    for e in spec.edges:
        if e.source not in node_map or e.target not in node_map:
            defects.append(
                Defect(
                    severity="P0",
                    where=f"edge:{e.source}->{e.target}",
                    message="连线端点不存在",
                    dimension="edge_integrity",
                )
            )
        if e.source == e.target:
            defects.append(
                Defect(
                    severity="P1",
                    where=f"edge:{e.source}->{e.target}",
                    message="连线形成自环，可能影响可读性",
                    dimension="edge_integrity",
                )
            )
    crossings = 0

    # 3b) edge aesthetics: long diagonal / intersects or too-close to nodes
    diag_len = math.hypot(spec.canvas_width, spec.canvas_height)
    long_diag_edges = 0
    edge_node_intersections = 0
    edge_node_too_close = 0
    edge_lengths: List[float] = []
    edge_diagness: List[float] = []
    edge_segs: List[Tuple[Edge, List[Tuple[Tuple[float, float], Tuple[float, float]]]]] = []

    for e in spec.edges:
        ns = node_map.get(e.source)
        nt = node_map.get(e.target)
        if not ns or not nt:
            continue
        src = _rect(ns)
        tgt = _rect(nt)
        # Exclude endpoints from obstacles, expand slightly to keep routes away from node borders.
        obstacles = [
            rect_expand(_rect(other), pad=10)
            for nid, other in node_map.items()
            if nid not in {e.source, e.target}
        ]
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
        edge_lengths.append(total_len)
        edge_segs.append((e, segs))

        if routing_mode == "straight" and segs:
            a0, b0 = segs[0][0], segs[-1][1]
            dx = abs(b0[0] - a0[0])
            dy = abs(b0[1] - a0[1])
            diagness = (min(dx, dy) / max(1.0, max(dx, dy))) if (dx > 0 or dy > 0) else 0.0
            edge_diagness.append(diagness)
            if (total_len / max(1.0, diag_len) >= edge_long_diag_ratio) and (diagness >= edge_diagness_warn):
                long_diag_edges += 1
        else:
            edge_diagness.append(0.0)

        # Segment vs other nodes (route-aware proxy; aligns better with draw.io orthogonal routing).
        for nid, other in node_map.items():
            if nid in (e.source, e.target):
                continue
            r = _rect(other)
            if any(_segment_intersects_rect(a, b, r) for a, b in segs):
                edge_node_intersections += 1
                defects.append(
                    Defect(
                        severity="P1",
                        where=f"edge:{e.source}->{e.target}",
                        message=f"连线可能穿越节点 {nid}（建议调整节点排列/对齐，减少穿越）",
                        dimension="edge_node_intersection",
                    )
                )
                break
            if segs:
                dist = min(_dist_segment_to_rect(a, b, r) for a, b in segs)
                if 0.0 < dist < float(edge_node_min_dist):
                    edge_node_too_close += 1
                    defects.append(
                        Defect(
                            severity="P2",
                            where=f"edge:{e.source}->{e.target}",
                            message=f"连线可能贴近节点 {nid}（最小距离≈{dist:.1f}px），缩印可读性可能受影响",
                            dimension="edge_node_proximity",
                        )
                    )
                    break

    if routing_mode == "straight" and long_diag_edges > 0:
        defects.append(
            Defect(
                severity="P1",
                where="global",
                message=f"存在较多长对角线连线：{long_diag_edges} 条（建议加强纵向主链路对齐/正交层次）",
                dimension="edge_length_diagonal",
            )
            )

    # 3c) edge-edge crossings (routing-aware for orthogonal mode)
    if routing_mode == "straight":
        crossings = _edge_cross_count(spec.edges, node_map)
    else:
        # Count crossings per edge-pair (not per segment-pair) to avoid over-penalizing long routed polylines.
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
                        if _axis_aligned_proper_cross(a1, a2, b1, b2):
                            cross += 1
                            hit = True
                            break
                    if hit:
                        break
        crossings = cross

    if crossings > 0:
        sev = "P2"
        if crossings > 2:
            sev = "P1"
        if crossings > 6:
            sev = "P0"
        defects.append(
            Defect(
                severity=sev,
                where="global",
                message=f"连线交叉：{crossings} 处（routing={routing_mode}）",
                dimension="edge_crossings",
            )
        )

    # 4) canvas overflow
    overflow = 0
    near_margin = 0
    for n in nodes:
        x1, y1 = n.x + n.w, n.y + n.h
        if n.x < 0 or n.y < 0 or x1 > spec.canvas_width or y1 > spec.canvas_height:
            overflow += 1
            defects.append(
                Defect(
                    severity="P0",
                    where=f"node:{n.id}",
                    message="节点超出画布边界",
                    dimension="canvas_overflow",
                )
            )
            continue
        min_margin = min(n.x, n.y, spec.canvas_width - x1, spec.canvas_height - y1)
        if min_margin < node_margin_warn:
            near_margin += 1
            defects.append(
                Defect(
                    severity="P1",
                    where=f"node:{n.id}",
                    message=f"节点距边界过近：{min_margin}px < {node_margin_warn}px",
                    dimension="canvas_overflow",
                )
            )

    # 5) visual balance
    total_area = sum(max(1, n.w * n.h) for n in nodes)
    if total_area > 0:
        cx = sum((n.x + n.w / 2) * (n.w * n.h) for n in nodes) / total_area
        cy = sum((n.y + n.h / 2) * (n.w * n.h) for n in nodes) / total_area
        dx = abs(cx - spec.canvas_width / 2) / max(1.0, spec.canvas_width / 2)
        dy = abs(cy - spec.canvas_height / 2) / max(1.0, spec.canvas_height / 2)
        if max(dx, dy) > balance_warn:
            defects.append(
                Defect(
                    severity="P1",
                    where="global",
                    message=f"视觉重心偏移较大：dx={dx:.2f}, dy={dy:.2f}",
                    dimension="visual_balance",
                )
            )

    # 6) overall aesthetics (limited local proxy)
    visual = _visual_score(
        png_path=png_path,
        min_w=int(spec.canvas_width),
        min_h=int(spec.canvas_height),
        expected_nodes=len(nodes),
        thresholds=thresholds if isinstance(thresholds, dict) else {},
        defects=defects,
    )

    p0 = sum(1 for d in defects if d.severity == "P0")
    p1 = sum(1 for d in defects if d.severity == "P1")
    p2 = sum(1 for d in defects if d.severity == "P2")

    heuristic = 100 - p0 * 22 - p1 * 8 - p2 * 2
    heuristic = max(0, min(100, heuristic))

    weights = config.get("evaluation", {}).get("weights", {})
    w_h = float(weights.get("heuristic", 0.7))
    w_v = float(weights.get("visual", 0.3))
    s = max(1e-9, w_h + w_v)
    w_h /= s
    w_v /= s
    score = int(round(w_h * heuristic + w_v * visual))

    metrics["edge"] = {
        "edge_count": len(spec.edges),
        "length_avg": (sum(edge_lengths) / len(edge_lengths)) if edge_lengths else 0.0,
        "length_max": max(edge_lengths) if edge_lengths else 0.0,
        "diagness_avg": (sum(edge_diagness) / len(edge_diagness)) if edge_diagness else 0.0,
        "long_diagonal_edges": long_diag_edges,
        "edge_node_intersections": edge_node_intersections,
        "edge_node_too_close": edge_node_too_close,
    }
    metrics["text"] = {"crowded_nodes": crowded_nodes}

    return {
        "score": score,
        "heuristic_score": heuristic,
        "visual_score": visual,
        "metrics": metrics,
        "counts": {
            "nodes": len(nodes),
            "groups": len(spec.groups),
            "edges": len(spec.edges),
            "overflow": overflow,
            "near_margin": near_margin,
            "edge_crossings": crossings,
            "p0": p0,
            "p1": p1,
            "p2": p2,
        },
        "defects": [asdict(d) for d in defects],
        "canvas": {"width": spec.canvas_width, "height": spec.canvas_height},
        "font": {
            "node_label_size": node_font,
            "edge_label_size": edge_font,
            "min_required": min_font,
            "min_required_node": min_font,
            "min_required_edge": min_edge_font,
        },
    }


def _load_json(path: Path) -> Optional[Dict[str, Any]]:
    import json

    try:
        raw = path.read_text(encoding="utf-8")
    except Exception:
        return None
    try:
        data = json.loads(raw)
    except Exception:
        return None
    return data if isinstance(data, dict) else None


def _normalize_defects(defects: Any) -> List[Dict[str, Any]]:
    if not isinstance(defects, list):
        return []
    out: List[Dict[str, Any]] = []
    for d in defects:
        if not isinstance(d, dict):
            continue
        sev = str(d.get("severity", "")).strip().upper() or "P2"
        if sev not in {"P0", "P1", "P2"}:
            sev = "P2"
        where = str(d.get("where", "")).strip() or "global"
        msg = str(d.get("message", "")).strip()
        dim = str(d.get("dimension", "")).strip() or "unknown"
        if not msg:
            continue
        item: Dict[str, Any] = {"severity": sev, "where": where, "message": msg, "dimension": dim}
        sug = d.get("suggestion")
        if isinstance(sug, dict):
            item["suggestion"] = sug
        out.append(item)
    return out


def evaluate_schematic_ai_adapter(
    spec: SchematicSpec,
    config: Dict[str, Any],
    *,
    png_path: Optional[Path],
    output_dir: Optional[Path],
) -> Dict[str, Any]:
    """
    Offline AI evaluation protocol:
    - Write measurements.json (pure measurements)
    - Write ai_evaluation_request.md + ai_evaluation_response.json template
    - If ai_evaluation_response.json is filled (valid), use it; else fallback to heuristic.
    """
    from utils import warn

    measurements: Optional[Dict[str, Any]] = None
    if isinstance(output_dir, Path):
        output_dir.mkdir(parents=True, exist_ok=True)
        try:
            from measure_schematic import measure_schematic  # local import to keep legacy import graph simple

            measurements = measure_schematic(spec, config, png_path=png_path)
        except Exception as exc:
            warn(f"AI 模式度量采集失败，已退化为 heuristic（{exc}）")
            out = evaluate_schematic_heuristic(spec, config, png_path)
            out["evaluation_mode_requested"] = "ai"
            out["evaluation_source"] = "heuristic_fallback"
            return out

        import json

        (output_dir / "measurements.json").write_text(
            json.dumps(measurements, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )

        req = output_dir / "ai_evaluation_request.md"
        resp = output_dir / "ai_evaluation_response.json"
        if not req.exists():
            req_lines = [
                "# AI Evaluation Request (nsfc-schematic)",
                "",
                "你是一个严格的图稿评审员。请基于 `measurements.json`（必要时结合 `schematic.png`）给出结构化缺陷清单与总分。",
                "",
                "## 输入证据",
                "",
                f"- measurements: `{(output_dir / 'measurements.json').name}`",
                f"- png: `{png_path.name}`" if isinstance(png_path, Path) else "- png: N/A",
                "",
                "## 输出（写入 ai_evaluation_response.json）",
                "",
                "```json",
                "{",
                "  \"score\": 0,",
                "  \"score_rationale\": \"\",",
                "  \"defects\": [",
                "    {",
                "      \"severity\": \"P1\",",
                "      \"where\": \"node:n1\",",
                "      \"dimension\": \"text_overflow\",",
                "      \"message\": \"\",",
                "      \"suggestion\": {\"action\": \"increase_gap\", \"parameter\": \"node_gap_x\", \"delta\": 10}",
                "    }",
                "  ]",
                "}",
                "```",
                "",
                "说明：",
                "- `defects[].severity` 仅允许 P0/P1/P2；`suggestion` 可省略。",
                "- `suggestion.action` 建议仅使用：`increase_canvas`、`increase_gap`、`increase_font`。",
                "- 建议的安全范围（超出会被脚本裁剪/忽略）：canvas delta ∈ [50, 500]；gap delta ∈ [2, 30]；font delta ∈ [1, 8]。",
                "",
            ]
            req.write_text("\n".join(req_lines), encoding="utf-8")

        if not resp.exists():
            resp.write_text(
                json.dumps({"score": 0, "score_rationale": "", "defects": []}, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )

        payload = _load_json(resp)
        if payload is not None:
            defects = _normalize_defects(payload.get("defects", []))
            score = payload.get("score")
            try:
                score_i = int(score)
            except Exception:
                score_i = 0
            score_i = max(0, min(100, score_i))
            score_rationale = str(payload.get("score_rationale", "")).strip()

            if defects or score_rationale or score_i:
                p0 = sum(1 for d in defects if d["severity"] == "P0")
                p1 = sum(1 for d in defects if d["severity"] == "P1")
                p2 = sum(1 for d in defects if d["severity"] == "P2")
                return {
                    "score": score_i,
                    "heuristic_score": score_i,
                    "visual_score": score_i,
                    # Keep legacy field for backward compatibility; AI mode also exposes a dedicated
                    # "measurements" field for consumers that want to avoid schema ambiguity.
                    "metrics": (measurements.get("measurements", {}) if isinstance(measurements, dict) else {}),
                    "measurements": (measurements.get("measurements", {}) if isinstance(measurements, dict) else {}),
                    "counts": {
                        "nodes": len([n for g in spec.groups for n in g.children]),
                        "groups": len(spec.groups),
                        "edges": len(spec.edges),
                        "p0": p0,
                        "p1": p1,
                        "p2": p2,
                    },
                    "defects": defects,
                    "canvas": {"width": spec.canvas_width, "height": spec.canvas_height},
                    "font": {
                        "node_label_size": int(config.get("layout", {}).get("font", {}).get("node_label_size", 0) or 0),
                        "edge_label_size": int(
                            config.get("layout", {}).get("font", {}).get("edge_label_size", 0)
                            or config.get("layout", {}).get("font", {}).get("node_label_size", 0)
                            or 0
                        ),
                    },
                    "evaluation_mode_requested": "ai",
                    "evaluation_source": "ai",
                    "score_rationale": score_rationale,
                }

        warn("AI 模式未检测到有效 ai_evaluation_response.json，已退化为 heuristic")

    # No output_dir (or missing AI response): keep script usable by falling back.
    out = evaluate_schematic_heuristic(spec, config, png_path)
    out["evaluation_mode_requested"] = "ai"
    out["evaluation_source"] = "heuristic_fallback"
    return out


def main() -> None:
    import argparse
    import json

    from spec_parser import load_schematic_spec
    from utils import fatal, load_yaml

    p = argparse.ArgumentParser(description="Evaluate nsfc-schematic quality.")
    p.add_argument("--spec", required=True, type=Path)
    p.add_argument("--config", required=True, type=Path)
    p.add_argument("--png", required=False, type=Path, default=None)
    p.add_argument("--out", required=False, type=Path, default=None)
    args = p.parse_args()

    try:
        cfg = load_yaml(args.config)
        spec_data = load_yaml(args.spec)
        spec = load_schematic_spec(spec_data, cfg)
        result = evaluate_schematic(spec, cfg, args.png, protocol_dir=(args.out.parent if args.out else None))
    except Exception as exc:
        fatal(str(exc))

    text = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding="utf-8")
    else:
        print(text, end="")


if __name__ == "__main__":
    main()
