from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from PIL import ImageDraw, ImageFont, Image

from measure_roadmap import measure as measure_roadmap
from spec import load_spec
from utils import FontChoice, load_yaml, pick_font, warn


@dataclass
class Defect:
    severity: str  # P0/P1/P2
    where: str
    message: str
    dimension: str


def _load_font(
    font_choice: FontChoice,
) -> Union[ImageFont.FreeTypeFont, ImageFont.ImageFont]:
    if font_choice.path is None:
        return ImageFont.load_default()
    try:
        return ImageFont.truetype(str(font_choice.path), font_choice.size)
    except Exception:
        return ImageFont.load_default()


def _visual_score_from_measurements(
    density_measure: Dict[str, Any],
    min_w: int,
    min_h: int,
    expected_boxes: int,
    thresholds: Dict[str, Any],
    defects: List[Defect],
) -> Tuple[int, Dict[str, Any]]:
    metrics: Dict[str, Any] = {}

    if not bool(density_measure.get("available")):
        # Keep behavior consistent with legacy evaluator.
        code = str(density_measure.get("error_code") or "")
        err = str(density_measure.get("error") or "")
        if code == "png_missing":
            defects.append(
                Defect(
                    severity="P2",
                    where="global",
                    message="未提供 PNG，跳过视觉评估（建议启用渲染产物评估）",
                    dimension="density",
                )
            )
            return 70, metrics
        defects.append(
            Defect(
                severity="P1",
                where="global",
                message=f"PNG 读取失败：{err or 'unknown'}",
                dimension="density",
            )
        )
        return 60, metrics

    png_size = density_measure.get("png_size") or {}
    try:
        w = int(png_size.get("w", 0))
        h = int(png_size.get("h", 0))
    except Exception:
        w, h = 0, 0

    score = 85
    metrics["png_size"] = {"w": w, "h": h}

    if w < min_w or h < min_h:
        defects.append(
            Defect(
                severity="P1",
                where="global",
                message=f"分辨率偏低：{w}x{h}，建议至少 {min_w}x{min_h}",
                dimension="density",
            )
        )
        score -= 12

    try:
        density = float(density_measure.get("density", 0.0))
    except Exception:
        density = 0.0
    metrics["density"] = density

    crowded_p1 = float(thresholds.get("crowded_density_p1", 0.35))
    if density > crowded_p1:
        defects.append(
            Defect(
                severity="P1",
                where="global",
                message=f"画面元素偏拥挤（像素密度={density:.2f}），建议增加画布/间距或缩短文案",
                dimension="density",
            )
        )
        score -= 10
    else:
        blank_min_boxes = int(thresholds.get("blank_check_min_boxes", 8))
        blank_p0 = float(thresholds.get("blank_density_p0", 0.01))
        blank_p1 = float(thresholds.get("blank_density_p1", 0.02))

        if expected_boxes >= blank_min_boxes and density < blank_p0:
            defects.append(
                Defect(
                    severity="P0",
                    where="global",
                    message=(
                        f"疑似渲染内容缺失/被忽略：spec.boxes={expected_boxes} 但像素密度={density:.3f}。"
                        "请优先检查 drawio 是否为合法 XML，并确认渲染链路未异常跳过。"
                    ),
                    dimension="density",
                )
            )
            score -= 35
        elif expected_boxes >= blank_min_boxes and density < blank_p1:
            defects.append(
                Defect(
                    severity="P1",
                    where="global",
                    message=(
                        f"疑似渲染内容偏少：spec.boxes={expected_boxes} 但像素密度={density:.3f}。"
                        "建议检查 drawio 合法性与渲染产物是否被覆盖/裁剪。"
                    ),
                    dimension="density",
                )
            )
            score -= 18
        elif density < 0.05:
            defects.append(
                Defect(
                    severity="P2",
                    where="global",
                    message=f"画面元素偏稀疏（像素密度={density:.2f}），可考虑收紧间距提升信息密度",
                    dimension="density",
                )
            )
            score -= 3

    return max(0, min(100, score)), metrics


def evaluate(
    spec_yaml: Path,
    config_yaml: Path,
    png_path: Optional[Path] = None,
    drawio_path: Optional[Path] = None,
) -> Dict[str, Any]:
    config = load_yaml(config_yaml)
    spec_data = load_yaml(spec_yaml)
    spec = load_spec(spec_data)

    renderer = config["renderer"]
    layout = config["layout"]
    evaluation_cfg = config.get("evaluation", {}) or {}
    thresholds = evaluation_cfg.get("thresholds", {}) or {}

    # Resolve default png path from config if not explicitly given.
    if png_path is None:
        try:
            artifacts = (config.get("output", {}) or {}).get("artifacts", {}) or {}
            png_name = artifacts.get("png")
            if isinstance(png_name, str):
                cand = spec_yaml.parent / png_name
                png_path = cand if cand.exists() else png_path
        except Exception:
            png_path = None

    measurements = measure_roadmap(spec_yaml, config_yaml, png_path=png_path, drawio_path=drawio_path).get("measurements", {})

    defects: List[Defect] = []
    metrics: Dict[str, Any] = {}

    min_font = int(thresholds.get("min_font_px", layout.get("min_font_size", 20)))
    font_choice = pick_font(renderer["fonts"]["candidates"], int(renderer["fonts"]["default_size"]))
    if font_choice.path is None:
        warn("未找到可用中文字体候选；输出可能出现中文乱码/方框。")
    font_size = int(font_choice.size)
    if font_size < min_font:
        defects.append(
            Defect(
                severity="P0",
                where="global",
                message=f"默认字号过小：{font_size}px < min_font_size({min_font}px)",
                dimension="text",
            )
        )

    box_count = int(measurements.get("boxes", 0) or 0)

    # Structural issues from measurement layer (mapped to legacy messages for zero-regression).
    for issue in measurements.get("structural_issues", []) if isinstance(measurements.get("structural_issues", []), list) else []:
        if not isinstance(issue, dict):
            continue
        code = str(issue.get("code", "")).strip()
        where = str(issue.get("where", "")).strip() or "global"
        if code == "missing_rows":
            defects.append(Defect(severity="P0", where=where, message="阶段缺少 rows", dimension="overflow"))
        elif code == "no_space_for_rows":
            defects.append(
                Defect(
                    severity="P0",
                    where=where,
                    message="画布高度不足导致 rows 无法布局（available_row_h<=0）",
                    dimension="overflow",
                )
            )
        elif code == "no_space_for_text_h":
            defects.append(
                Defect(severity="P0", where=where, message="box padding 过大导致文字区域高度<=0", dimension="overflow")
            )
        elif code == "no_space_for_boxes":
            defects.append(
                Defect(severity="P0", where=where, message="画布宽度不足导致 boxes 无法布局（available_w<=0）", dimension="overflow")
            )
        elif code == "no_space_for_text_w":
            defects.append(
                Defect(severity="P0", where=where, message="box padding 过大导致文字区域宽度<=0", dimension="overflow")
            )
        else:
            # Unknown structural issues should not break evaluation; keep it as P1 to surface.
            defects.append(Defect(severity="P1", where=where, message=f"结构测量异常：{code}", dimension="overflow"))

    overflow_count = 0
    for m in measurements.get("overflow_boxes", []) if isinstance(measurements.get("overflow_boxes", []), list) else []:
        if not isinstance(m, dict):
            continue
        overflow_count += 1
        defects.append(
            Defect(
                severity="P0",
                where=str(m.get("box_id", "")).strip() or "global",
                message=f"文字溢出：text_h={int(m.get('text_h', 0))}px > max_text_h={int(m.get('max_h', 0))}px",
                dimension="overflow",
            )
        )

    near_overflow_count = 0
    near_ratio = float(thresholds.get("near_overflow_ratio_p1", 0.92))
    too_many_lines_count = 0
    max_lines_p2 = int(thresholds.get("too_many_lines_p2", 5))
    extreme_ratio_count = 0

    for m in measurements.get("box_text_measures", []) if isinstance(measurements.get("box_text_measures", []), list) else []:
        if not isinstance(m, dict):
            continue
        box_id = str(m.get("box_id", "")).strip() or "global"
        try:
            ratio = float(m.get("ratio", 0.0))
        except Exception:
            ratio = 0.0
        try:
            text_h = int(m.get("text_h", 0))
            max_h = int(m.get("max_h", 0))
        except Exception:
            text_h, max_h = 0, 0

        # Skip already-overflowed boxes (P0 already emitted).
        if text_h > max_h:
            continue

        if ratio >= near_ratio:
            near_overflow_count += 1
            defects.append(
                Defect(
                    severity="P1",
                    where=box_id,
                    message=f"文字接近溢出：占用 {ratio:.0%}（建议增高或减字号）",
                    dimension="overflow",
                )
            )

        try:
            lines = int(m.get("lines", 0))
        except Exception:
            lines = 0
        if lines >= max_lines_p2:
            too_many_lines_count += 1
            defects.append(
                Defect(
                    severity="P2",
                    where=box_id,
                    message=f"换行过多：{lines} 行（建议精简或调整分行）",
                    dimension="text",
                )
            )

        try:
            ratio_wh = float(m.get("ratio_wh", 0.0))
        except Exception:
            ratio_wh = 0.0
        if ratio_wh > 8.5 or ratio_wh < 0.9:
            extreme_ratio_count += 1
            defects.append(
                Defect(
                    severity="P2",
                    where=box_id,
                    message=f"框体比例偏极端（w/h={ratio_wh:.1f}），建议调整列数/权重/画布比例",
                    dimension="balance",
                )
            )

    # Phase balance proxy: if one phase consumes too much vertical space.
    phase_heights = (measurements.get("phase_balance") or {}).get("heights", [])
    if isinstance(phase_heights, list) and len(phase_heights) >= 3:
        try:
            ratio_bal = float((measurements.get("phase_balance") or {}).get("ratio", 0.0) or 0.0)
        except Exception:
            ratio_bal = 0.0
        if ratio_bal > float(thresholds.get("phase_balance_warn_ratio", 1.8)):
            defects.append(
                Defect(
                    severity="P2",
                    where="global",
                    message="阶段高度分配偏不均衡（建议检查某阶段 rows 是否过多/过少，或适当调整画布高度）",
                    dimension="balance",
                )
            )

    # Connectivity check (mainline edges should exist when phases>=2). Only trust parsed XML.
    edges = (measurements.get("edges") or {}) if isinstance(measurements.get("edges") or {}, dict) else {}
    edge_metrics: Dict[str, Any] = {"edges": {"total": 0, "missing_endpoints": 0}}
    if bool(edges.get("available")):
        total_edges = int(edges.get("total", 0) or 0)
        missing = int(edges.get("missing_endpoints", 0) or 0)
        edge_metrics["edges"]["total"] = total_edges
        edge_metrics["edges"]["missing_endpoints"] = missing
        min_expected_edges = max(0, len(spec.phases) - 1)
        if min_expected_edges > 0 and total_edges == 0:
            defects.append(
                Defect(
                    severity="P1",
                    where="drawio",
                    message="路线图主线连线缺失（phases>=2 但 edges=0）；建议生成 Phase1→Phase2→… 的主链箭头",
                    dimension="connections",
                )
            )
        if missing > 0:
            defects.append(
                Defect(
                    severity="P0",
                    where="drawio",
                    message=f"检测到 {missing} 条连线缺少 source/target（可能导致导出后连线丢失）",
                    dimension="connections",
                )
            )
    metrics["connections"] = edge_metrics

    # Heuristic scoring (based on layout/connection defects only; visual is scored separately).
    hp0 = sum(1 for d in defects if d.severity == "P0")
    hp1 = sum(1 for d in defects if d.severity == "P1")
    hp2 = sum(1 for d in defects if d.severity == "P2")
    heuristic = 100 - hp0 * 25 - hp1 * 10 - hp2 * 3
    heuristic = max(0, min(100, heuristic))

    # Visual scoring (PNG density + near-blank checks)
    min_png_w = int(thresholds.get("min_png_width_px", 1600))
    min_png_h = int(thresholds.get("min_png_height_px", 1100))
    density_measure = {
        "available": bool(measurements.get("density_available")),
        "error_code": measurements.get("density_error_code"),
        "error": measurements.get("density_error"),
        "png_size": measurements.get("png_size"),
        "density": measurements.get("density"),
    }
    visual, visual_metrics = _visual_score_from_measurements(
        density_measure, min_png_w, min_png_h, box_count, thresholds, defects
    )
    metrics["visual"] = visual_metrics

    # Final defect counts (include visual defects for reporting/optimization decisions).
    p0 = sum(1 for d in defects if d.severity == "P0")
    p1 = sum(1 for d in defects if d.severity == "P1")
    p2 = sum(1 for d in defects if d.severity == "P2")

    weights = evaluation_cfg.get("weights", {}) or {}
    w_h = float(weights.get("heuristic", 0.7))
    w_v = float(weights.get("visual", 0.3))
    score = int(round(w_h * heuristic + w_v * visual))
    score = max(0, min(100, score))

    return {
        "score": score,
        "scores": {"heuristic": heuristic, "visual": visual, "weights": {"heuristic": w_h, "visual": w_v}},
        "counts": {
            "boxes": box_count,
            "overflow": overflow_count,
            "near_overflow": near_overflow_count,
            "too_many_lines": too_many_lines_count,
            "extreme_ratio": extreme_ratio_count,
            "p0": p0,
            "p1": p1,
            "p2": p2,
        },
        "font": {
            "path": str(font_choice.path) if font_choice.path else None,
            "size": font_choice.size,
            "min_required": min_font,
        },
        "canvas": {"width_px": int(renderer["canvas"]["width_px"]), "height_px": int(renderer["canvas"]["height_px"])},
        "metrics": metrics,
        "defects": [asdict(d) for d in defects],
        "measurements": measurements,
    }


def main() -> None:
    import argparse
    import json

    p = argparse.ArgumentParser(description="Evaluate nsfc-roadmap layout (heuristic).")
    p.add_argument("--mode", required=False, default="heuristic", help="heuristic|ai（ai=仅输出 measurements.json）")
    p.add_argument("--spec", required=True, type=Path)
    p.add_argument("--config", required=True, type=Path)
    p.add_argument("--png", required=False, type=Path, default=None)
    p.add_argument("--drawio", required=False, type=Path, default=None)
    p.add_argument("--out", required=False, type=Path, default=None)
    args = p.parse_args()

    mode = str(args.mode or "heuristic").strip().lower()
    if mode not in {"heuristic", "ai"}:
        raise SystemExit("`--mode` must be heuristic|ai")

    if mode == "ai":
        result = measure_roadmap(args.spec, args.config, png_path=args.png, drawio_path=args.drawio)
    else:
        result = evaluate(args.spec, args.config, png_path=args.png, drawio_path=args.drawio)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
