from __future__ import annotations

"""
Multi-dimension critique for nsfc-roadmap.

Goals:
- Add deterministic, human-aligned checks (structure / visual / readability).
- Keep it lightweight and dependency-free beyond existing project deps (PyYAML, Pillow).
- Produce per-dimension JSON for traceability.

Note:
This file intentionally does NOT call any external LLM API.
"""

from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from PIL import Image

from evaluate_roadmap import Defect
from spec import load_spec
from utils import clamp, hex_to_rgb, load_yaml


def _severity_penalty(sev: str) -> int:
    # Keep consistent with evaluate_roadmap heuristic scoring weights.
    if sev == "P0":
        return 25
    if sev == "P1":
        return 10
    if sev == "P2":
        return 3
    return 0


def _score_from_defects(defects: List[Defect]) -> int:
    score = 100
    for d in defects:
        score -= _severity_penalty(d.severity)
    return clamp(score, 0, 100)


def _norm_term(s: str) -> str:
    # Normalization for "same term / same box" checks.
    t = s.strip().replace("\r\n", "\n").replace("\r", "\n")
    # Collapse whitespace and common punctuation that often varies in specs.
    for ch in (" ", "\t", "\n", "（", "）", "(", ")", "[", "]", "：", ":", "，", ",", "。", ".", "；", ";"):
        t = t.replace(ch, "")
    return t


def _srgb_channel_to_linear(x: float) -> float:
    # WCAG sRGB -> linear
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


def evaluate_structure(spec_yaml: Path, config_yaml: Path) -> Dict[str, Any]:
    _ = load_yaml(config_yaml)  # reserved for future (avoid surprise if missing)
    spec_data = load_yaml(spec_yaml)
    spec = load_spec(spec_data)

    defects: List[Defect] = []
    metrics: Dict[str, Any] = {}

    metrics["phases"] = len(spec.phases)
    if len(spec.phases) < 2:
        defects.append(
            Defect(
                severity="P1",
                where="global",
                message="阶段数量偏少（建议至少 2 个阶段）",
                dimension="structure",
            )
        )

    phase_labels = [p.label.strip() for p in spec.phases]
    metrics["phase_labels"] = phase_labels
    dup_phase = {x for x in phase_labels if phase_labels.count(x) >= 2}
    if dup_phase:
        defects.append(
            Defect(
                severity="P0",
                where="global",
                message=f"阶段 label 重复：{sorted(dup_phase)}（会导致读者误解阶段含义）",
                dimension="structure",
            )
        )

    box_terms: Dict[str, List[str]] = {}
    total_boxes = 0
    risk_boxes = 0
    too_long_boxes = 0

    for ph in spec.phases:
        if not ph.rows:
            defects.append(
                Defect(
                    severity="P0",
                    where=f"phase:{ph.label}",
                    message="阶段缺少 rows（无法布局）",
                    dimension="structure",
                )
            )
            continue
        for r_idx, row in enumerate(ph.rows, start=1):
            if not row.boxes:
                defects.append(
                    Defect(
                        severity="P0",
                        where=f"phase:{ph.label}/row:{r_idx}",
                        message="row 缺少 boxes（无法布局）",
                        dimension="structure",
                    )
                )
                continue
            for b_idx, box in enumerate(row.boxes, start=1):
                total_boxes += 1
                if box.kind == "risk":
                    risk_boxes += 1
                text = (box.text or "").strip()
                norm = _norm_term(text)
                if norm:
                    box_terms.setdefault(norm, []).append(f"phase:{ph.label}/row:{r_idx}/box:{b_idx}")
                # Very long single-line text often implies overflow or unreadability.
                if len(text) >= 60 and "\n" not in text:
                    too_long_boxes += 1
                    defects.append(
                        Defect(
                            severity="P2",
                            where=f"phase:{ph.label}/row:{r_idx}/box:{b_idx}",
                            message="文本偏长且未分行（建议用换行/精简，避免拥挤与溢出）",
                            dimension="structure",
                        )
                    )

                # Safety: drawio value is XML-escaped, but raw spec text with control chars can still be surprising.
                if any(ch in text for ch in ("\x00", "\x01", "\x02")):
                    defects.append(
                        Defect(
                            severity="P1",
                            where=f"phase:{ph.label}/row:{r_idx}/box:{b_idx}",
                            message="检测到异常控制字符（建议清理，避免渲染器/导出异常）",
                            dimension="structure",
                        )
                    )

    metrics["boxes_total"] = total_boxes
    metrics["risk_boxes"] = risk_boxes
    metrics["long_singleline_boxes"] = too_long_boxes

    # Duplicate terms (exact normalized match).
    dup_terms = {k: v for k, v in box_terms.items() if len(v) >= 2}
    if dup_terms:
        # Limit to keep report readable.
        sample = list(dup_terms.items())[:5]
        msg_parts = []
        for term, locs in sample:
            msg_parts.append(f"{term} -> {len(locs)} 处")
        defects.append(
            Defect(
                severity="P2",
                where="global",
                message="检测到重复节点/术语（可能导致图面冗余）： " + "；".join(msg_parts),
                dimension="structure",
            )
        )

    if total_boxes >= 8 and risk_boxes == 0:
        defects.append(
            Defect(
                severity="P2",
                where="global",
                message="未发现 risk 类型节点（建议至少 1 个风险/备选方案节点以增强可信度）",
                dimension="structure",
            )
        )

    return {
        "dimension": "structure",
        "score": _score_from_defects(defects),
        "metrics": metrics,
        "defects": [asdict(d) for d in defects],
    }


def evaluate_visual(spec_yaml: Path, config_yaml: Path, png_path: Optional[Path] = None) -> Dict[str, Any]:
    # spec_yaml reserved for future (e.g. per-kind usage); keep signature stable.
    _ = spec_yaml
    config = load_yaml(config_yaml)

    defects: List[Defect] = []
    metrics: Dict[str, Any] = {}

    bg_hex = (config.get("renderer", {}) or {}).get("background", "#FFFFFF")
    bg = _safe_hex_to_rgb(str(bg_hex)) or (255, 255, 255)

    layout = config.get("layout", {}) if isinstance(config.get("layout", {}), dict) else {}
    phase_bar = layout.get("phase_bar", {}) if isinstance(layout.get("phase_bar", {}), dict) else {}
    bar_fill = _safe_hex_to_rgb(str(phase_bar.get("fill", "#2F75B5"))) or (47, 117, 181)
    bar_text = _safe_hex_to_rgb(str(phase_bar.get("text_color", "#FFFFFF"))) or (255, 255, 255)
    bar_contrast = _contrast_ratio(bar_fill, bar_text)
    metrics["phase_bar_contrast"] = bar_contrast
    if bar_contrast < 3.0:
        defects.append(
            Defect(
                severity="P0",
                where="phase_bar",
                message=f"阶段条文字对比度过低（contrast={bar_contrast:.2f} < 3.0），打印后可能不可读",
                dimension="visual",
            )
        )
    elif bar_contrast < 4.5:
        defects.append(
            Defect(
                severity="P1",
                where="phase_bar",
                message=f"阶段条文字对比度偏低（contrast={bar_contrast:.2f} < 4.5），建议提高对比度",
                dimension="visual",
            )
        )

    scheme = config.get("color_scheme", {}) if isinstance(config.get("color_scheme", {}), dict) else {}
    scheme_name = str(scheme.get("name", "academic-blue"))
    presets = scheme.get("presets", {}) if isinstance(scheme.get("presets", {}), dict) else {}
    preset = presets.get(scheme_name, {}) if isinstance(presets.get(scheme_name, {}), dict) else {}
    text_hex = preset.get("text", "#1F1F1F")
    box_text = _safe_hex_to_rgb(str(text_hex)) or (31, 31, 31)

    fill_colors: List[Tuple[int, int, int]] = []
    per_kind: Dict[str, Any] = {}
    for kind in ("primary", "secondary", "decision", "critical", "risk", "auxiliary"):
        v = preset.get(kind)
        if not isinstance(v, dict):
            continue
        fill_hex = v.get("fill")
        stroke_hex = v.get("stroke")
        fill = _safe_hex_to_rgb(str(fill_hex)) if fill_hex is not None else None
        stroke = _safe_hex_to_rgb(str(stroke_hex)) if stroke_hex is not None else None
        if fill is None:
            continue
        fill_colors.append(fill)
        c = _contrast_ratio(fill, box_text)
        per_kind[kind] = {"fill": fill_hex, "stroke": stroke_hex, "contrast_to_text": c}
        if c < 3.0:
            defects.append(
                Defect(
                    severity="P0",
                    where=f"color_scheme:{kind}",
                    message=f"{kind} 节点文字对比度过低（contrast={c:.2f} < 3.0），建议更换填充色或文字色",
                    dimension="visual",
                )
            )
        elif c < 4.5:
            defects.append(
                Defect(
                    severity="P1",
                    where=f"color_scheme:{kind}",
                    message=f"{kind} 节点文字对比度偏低（contrast={c:.2f} < 4.5），建议提高对比度",
                    dimension="visual",
                )
            )

        # Washed-out check: fill too close to background reduces "box presence" on print.
        c_bg = _contrast_ratio(fill, bg)
        if c_bg < 1.3:
            defects.append(
                Defect(
                    severity="P2",
                    where=f"color_scheme:{kind}",
                    message=f"{kind} 填充色与背景过于接近（contrast={c_bg:.2f}），打印后边界感可能不足",
                    dimension="visual",
                )
            )

        if stroke is not None:
            c_stroke_bg = _contrast_ratio(stroke, bg)
            per_kind[kind]["stroke_contrast_to_bg"] = c_stroke_bg

    metrics["scheme_name"] = scheme_name
    metrics["kinds"] = per_kind

    # Palette diversity (simple distance in sRGB).
    def dist(a: Tuple[int, int, int], b: Tuple[int, int, int]) -> float:
        return ((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2 + (a[2] - b[2]) ** 2) ** 0.5

    if len(fill_colors) >= 2:
        mind = min(dist(fill_colors[i], fill_colors[j]) for i in range(len(fill_colors)) for j in range(i + 1, len(fill_colors)))
        metrics["min_fill_distance"] = mind
        if mind < 18.0:
            defects.append(
                Defect(
                    severity="P2",
                    where="color_scheme",
                    message="配色区分度偏低（部分填充色过于接近），建议拉开色相/明度差异",
                    dimension="visual",
                )
            )

    # Optional: use PNG to detect near-monochrome (render failure or overly washed palette).
    if png_path is not None and png_path.exists():
        pixels = _downsample_gray(png_path, (240, 140))
        if pixels is not None:
            # Standard deviation proxy
            mean = sum(pixels) / max(1, len(pixels))
            var = sum((p - mean) ** 2 for p in pixels) / max(1, len(pixels))
            std = var ** 0.5
            metrics["png_gray_std"] = std
            if std < 6.0:
                defects.append(
                    Defect(
                        severity="P1",
                        where="png",
                        message="PNG 灰度对比度偏低（疑似过度发白或渲染异常），建议检查填充/描边/字号",
                        dimension="visual",
                    )
                )

    return {
        "dimension": "visual",
        "score": _score_from_defects(defects),
        "metrics": metrics,
        "defects": [asdict(d) for d in defects],
    }


def evaluate_readability(
    spec_yaml: Path, config_yaml: Path, png_path: Optional[Path] = None
) -> Dict[str, Any]:
    _ = spec_yaml
    config = load_yaml(config_yaml)
    eval_cfg = config.get("evaluation", {}) if isinstance(config.get("evaluation", {}), dict) else {}
    thresholds = eval_cfg.get("thresholds", {}) if isinstance(eval_cfg.get("thresholds", {}), dict) else {}

    defects: List[Defect] = []
    metrics: Dict[str, Any] = {}

    renderer = config.get("renderer", {}) if isinstance(config.get("renderer", {}), dict) else {}
    fonts = renderer.get("fonts", {}) if isinstance(renderer.get("fonts", {}), dict) else {}
    layout = config.get("layout", {}) if isinstance(config.get("layout", {}), dict) else {}

    font_size = int(fonts.get("default_size", 28) or 28)
    min_font = int(thresholds.get("min_font_px", layout.get("min_font_size", 20)) or 20)
    warn_font = int(thresholds.get("warn_font_px", max(min_font, 24)) or max(min_font, 24))
    metrics["font_size"] = font_size
    metrics["min_font_px"] = min_font
    metrics["warn_font_px"] = warn_font

    if font_size < min_font:
        defects.append(
            Defect(
                severity="P0",
                where="global",
                message=f"字号过小：{font_size}px < {min_font}px（A4 打印后大概率不可读）",
                dimension="readability",
            )
        )
    elif font_size < warn_font:
        defects.append(
            Defect(
                severity="P1",
                where="global",
                message=f"字号偏小：{font_size}px < {warn_font}px（建议增大字号或增大画布/减少文本）",
                dimension="readability",
            )
        )

    if png_path is None or not png_path.exists():
        defects.append(
            Defect(
                severity="P2",
                where="global",
                message="未提供 PNG，跳过可读性图像评估（建议启用 PNG 输出用于自检）",
                dimension="readability",
            )
        )
        return {
            "dimension": "readability",
            "score": _score_from_defects(defects),
            "metrics": metrics,
            "defects": [asdict(d) for d in defects],
        }

    pixels = _downsample_gray(png_path, (360, 210))
    if pixels is None:
        defects.append(
            Defect(
                severity="P1",
                where="png",
                message="PNG 读取失败，无法进行可读性评估",
                dimension="readability",
            )
        )
        return {
            "dimension": "readability",
            "score": _score_from_defects(defects),
            "metrics": metrics,
            "defects": [asdict(d) for d in defects],
        }

    # Density proxy (same spirit as evaluate_roadmap, but slightly richer: quadrant balance + edge crowding).
    nonwhite = sum(1 for p in pixels if p < 245)
    density = nonwhite / max(1, len(pixels))
    metrics["density"] = density

    crowded_p1 = float(thresholds.get("crowded_density_p1", 0.35))
    crowded_p0 = float(thresholds.get("crowded_density_p0", max(crowded_p1 + 0.10, 0.45)))
    metrics["crowded_density_p1"] = crowded_p1
    metrics["crowded_density_p0"] = crowded_p0

    if density >= crowded_p0:
        defects.append(
            Defect(
                severity="P0",
                where="global",
                message=f"整体过度拥挤（density={density:.2f} >= {crowded_p0:.2f}），A4 打印可读性风险高",
                dimension="readability",
            )
        )
    elif density >= crowded_p1:
        defects.append(
            Defect(
                severity="P1",
                where="global",
                message=f"整体偏拥挤（density={density:.2f} >= {crowded_p1:.2f}），优先精简文本/合并节点；如仍需更多空间，应在规划阶段减少内容而非无限拉长画布",
                dimension="readability",
            )
        )

    w, h = 360, 210
    def block(x0: int, y0: int, x1: int, y1: int) -> float:
        # (x0,y0) inclusive, (x1,y1) exclusive
        cnt = 0
        tot = 0
        for yy in range(y0, y1):
            row = yy * w
            for xx in range(x0, x1):
                tot += 1
                if pixels[row + xx] < 245:
                    cnt += 1
        return cnt / max(1, tot)

    q = {
        "tl": block(0, 0, w // 2, h // 2),
        "tr": block(w // 2, 0, w, h // 2),
        "bl": block(0, h // 2, w // 2, h),
        "br": block(w // 2, h // 2, w, h),
    }
    metrics["quadrant_density"] = q
    q_vals = list(q.values())
    if q_vals and (max(q_vals) - min(q_vals)) > 0.22:
        defects.append(
            Defect(
                severity="P2",
                where="png",
                message="画面密度分布不均（局部拥挤/空白明显），建议调整布局或阶段高度分配",
                dimension="readability",
            )
        )

    # Edge crowding: if borders are very dense, it often indicates insufficient margins / clipping risk.
    band = int(max(2, min(w, h) * 0.06))  # ~6%
    top = block(0, 0, w, band)
    bottom = block(0, h - band, w, h)
    left = block(0, 0, band, h)
    right = block(w - band, 0, w, h)
    metrics["edge_density"] = {"top": top, "bottom": bottom, "left": left, "right": right}
    if max(top, bottom, left, right) > 0.55:
        defects.append(
            Defect(
                severity="P2",
                where="png",
                message="边缘区域元素过密（可能边距不足或裁剪风险），建议增大 margin/border 或调整布局",
                dimension="readability",
            )
        )

    return {
        "dimension": "readability",
        "score": _score_from_defects(defects),
        "metrics": metrics,
        "defects": [asdict(d) for d in defects],
    }


def run_critiques(
    spec_yaml: Path,
    config_yaml: Path,
    png_path: Optional[Path],
    drawio_path: Optional[Path],
    dimensions: Iterable[str],
    max_workers: int = 3,
) -> Dict[str, Dict[str, Any]]:
    """
    Run per-dimension critique. Keep it deterministic and safe.

    Returns:
        {dimension_name: critique_result_dict}
    """
    dims = [str(d).strip() for d in dimensions if str(d).strip()]
    if not dims:
        return {}

    # ThreadPool is simpler and more robust than multiprocessing for a script invoked as a file.
    from concurrent.futures import ThreadPoolExecutor, as_completed

    def one(dim: str) -> Tuple[str, Dict[str, Any]]:
        if dim == "structure":
            return dim, evaluate_structure(spec_yaml, config_yaml)
        if dim == "visual":
            return dim, evaluate_visual(spec_yaml, config_yaml, png_path=png_path)
        if dim == "readability":
            return dim, evaluate_readability(spec_yaml, config_yaml, png_path=png_path)
        # Unknown dimension -> empty result (do not crash).
        return dim, {"dimension": dim, "score": 100, "metrics": {}, "defects": []}

    results: Dict[str, Dict[str, Any]] = {}
    workers = max(1, min(int(max_workers or 1), len(dims)))
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = [ex.submit(one, dim) for dim in dims]
        for f in as_completed(futs):
            dim, res = f.result()
            results[dim] = res
    return results


def main() -> None:
    import argparse
    import json

    p = argparse.ArgumentParser(description="Evaluate a single critique dimension for nsfc-roadmap.")
    p.add_argument("--mode", required=False, default="heuristic", help="heuristic|ai（ai=仅输出度量，不做 P0/P1/P2 判定）")
    p.add_argument("--dimension", required=True, type=str, help="structure|visual|readability")
    p.add_argument("--spec", required=True, type=Path)
    p.add_argument("--config", required=True, type=Path)
    p.add_argument("--png", required=False, type=Path, default=None)
    p.add_argument("--drawio", required=False, type=Path, default=None)
    p.add_argument("--out", required=False, type=Path, default=None)
    args = p.parse_args()

    dim = str(args.dimension).strip()
    mode = str(args.mode or "heuristic").strip().lower()
    if mode not in {"heuristic", "ai"}:
        raise SystemExit("`--mode` must be heuristic|ai")

    if mode == "ai":
        from measure_dimension import measure_readability, measure_structure, measure_visual

        if dim == "structure":
            metrics = measure_structure(args.spec, args.config)
        elif dim == "visual":
            metrics = measure_visual(args.spec, args.config, png_path=args.png)
        elif dim == "readability":
            metrics = measure_readability(args.spec, args.config, png_path=args.png)
        else:
            metrics = {}
        result = {"dimension": dim, "metrics": metrics}
    else:
        if dim == "structure":
            result = evaluate_structure(args.spec, args.config)
        elif dim == "visual":
            result = evaluate_visual(args.spec, args.config, png_path=args.png)
        elif dim == "readability":
            result = evaluate_readability(args.spec, args.config, png_path=args.png)
        else:
            result = {"dimension": dim, "score": 100, "metrics": {}, "defects": []}

    payload = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(payload, encoding="utf-8")
    else:
        print(payload, end="")


if __name__ == "__main__":
    main()
