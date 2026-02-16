from __future__ import annotations

"""
nsfc-schematic 多维度批判性自检（structure / visual / readability）。

目标：
- 提供可复现、可追溯的 per-dimension 结构化证据（critique_*.json）。
- 不引入必须联网的依赖；不在脚本中直接调用任何外部 LLM API。
- 默认“保守扣分 + 可解释”：评分主要用于多轮优化的候选对比与复盘。
"""

from dataclasses import asdict, dataclass
from pathlib import Path
import json
from typing import Any, Dict, Iterable, List, Optional, Tuple

from spec_parser import SchematicSpec, load_schematic_spec
from color_math import contrast_ratio as _contrast_ratio
from measure_dimension import (
    measure_readability as measure_readability_metrics,
    measure_structure as measure_structure_metrics,
    measure_visual as measure_visual_metrics,
)
from utils import hex_to_rgb, is_safe_relative_path, load_yaml, skill_root


@dataclass
class Defect:
    severity: str  # P0/P1/P2
    where: str
    message: str
    dimension: str


def _severity_penalty(sev: str) -> int:
    # 保持“线性 + 可解释”，且不要压过主评估器。
    if sev == "P0":
        return 6
    if sev == "P1":
        return 3
    if sev == "P2":
        return 1
    return 0


def _score_from_defects(defects: List[Defect]) -> int:
    score = 100
    for d in defects:
        score -= _severity_penalty(d.severity)
    return max(0, min(100, score))


def _safe_hex_to_rgb(v: Any) -> Optional[Tuple[int, int, int]]:
    if not isinstance(v, str):
        return None
    try:
        return hex_to_rgb(v)
    except Exception:
        return None


def load_palette_from_assets(config: Dict[str, Any], *, skill_root_dir: Optional[Path] = None) -> Dict[str, Any]:
    """
    Load palette from assets (preferred) or inline presets.

    This is intentionally a pure file/config operation:
    - No network
    - No model calls
    """
    color_cfg = config.get("color_scheme", {}) if isinstance(config.get("color_scheme", {}), dict) else {}
    scheme_name = str(color_cfg.get("name", "")).strip()
    if not scheme_name:
        raise ValueError("config.yaml:color_scheme.name 不能为空")

    presets: Dict[str, Any]
    file_v = color_cfg.get("file")
    if isinstance(file_v, str) and file_v.strip():
        if not is_safe_relative_path(file_v):
            raise ValueError(f"color_scheme.file 必须是安全的相对路径（不得包含 `..` 或绝对/盘符路径）：{file_v!r}")
        root = skill_root_dir if isinstance(skill_root_dir, Path) else skill_root()
        palette_path = root / file_v
        payload = load_yaml(palette_path)
        presets = payload.get("color_schemes", {}) if isinstance(payload.get("color_schemes", {}), dict) else {}
    else:
        presets = color_cfg.get("presets", {}) if isinstance(color_cfg.get("presets", {}), dict) else {}

    preset = presets.get(scheme_name, {}) if isinstance(presets.get(scheme_name, {}), dict) else {}
    if not preset:
        raise ValueError(f"未找到配色方案：{scheme_name}")
    return preset


def _load_spec_and_config(spec_yaml: Path, config_yaml: Path) -> Tuple[SchematicSpec, Dict[str, Any]]:
    config = load_yaml(config_yaml)
    spec_data = load_yaml(spec_yaml)
    spec = load_schematic_spec(spec_data, config)
    return spec, config


def evaluate_structure(spec: SchematicSpec, config: Dict[str, Any]) -> Dict[str, Any]:

    defects: List[Defect] = []
    metrics: Dict[str, Any] = {}

    checks = (config.get("planning", {}) or {}).get("checks", {})
    checks = checks if isinstance(checks, dict) else {}

    groups = spec.groups
    nodes = [n for g in groups for n in g.children]
    edges = spec.edges

    metrics["groups"] = len(groups)
    metrics["nodes"] = len(nodes)
    metrics["edges"] = len(edges)

    gmin = int(checks.get("groups_min", 1) or 1)
    gmax = int(checks.get("groups_max", 8) or 8)
    if len(groups) < gmin:
        defects.append(
            Defect(
                severity="P1",
                where="global",
                message=f"分组数量偏少：{len(groups)} < {gmin}（建议至少包含输入/处理/输出层级）",
                dimension="structure",
            )
        )
    if len(groups) > gmax:
        defects.append(
            Defect(
                severity="P1",
                where="global",
                message=f"分组数量偏多：{len(groups)} > {gmax}（建议合并相近层级，减少读者负担）",
                dimension="structure",
            )
        )

    per_min = int(checks.get("nodes_per_group_min", 1) or 1)
    per_max = int(checks.get("nodes_per_group_max", 10) or 10)
    too_many = 0
    too_few = 0
    for g in groups:
        c = len(g.children)
        if c < per_min:
            too_few += 1
            defects.append(
                Defect(
                    severity="P1",
                    where=f"group:{g.id}",
                    message=f"分组节点过少：{c} < {per_min}",
                    dimension="structure",
                )
            )
        if c > per_max:
            too_many += 1
            defects.append(
                Defect(
                    severity="P1",
                    where=f"group:{g.id}",
                    message=f"分组节点过多：{c} > {per_max}（建议拆分/分层或精简）",
                    dimension="structure",
                )
            )
    metrics["groups_too_few_nodes"] = too_few
    metrics["groups_too_many_nodes"] = too_many

    total_max = int(checks.get("total_nodes_max", 30) or 30)
    if len(nodes) > total_max:
        defects.append(
            Defect(
                severity="P1",
                where="global",
                message=f"总节点数偏多：{len(nodes)} > {total_max}（建议只保留主链路与关键模块）",
                dimension="structure",
            )
        )

    density_max = float(checks.get("edge_density_max_ratio", 2.0) or 2.0)
    density = (len(edges) / max(1, len(nodes)))
    metrics["edge_density_ratio"] = density
    if density > density_max:
        defects.append(
            Defect(
                severity="P1",
                where="global",
                message=f"连线密度偏高：edges/nodes={density:.2f} > {density_max:.2f}（可能导致线缠绕/交叉）",
                dimension="structure",
            )
        )

    # Input/Output presence (heuristic; keep it simple and explainable).
    if bool(checks.get("require_input_output", False)):
        gid = [g.id.lower() for g in groups]
        glabel = [g.label for g in groups]
        has_input = any("input" in x for x in gid) or any("输入" in x for x in glabel)
        has_output = any("output" in x for x in gid) or any("输出" in x for x in glabel)
        if not has_input or not has_output:
            defects.append(
                Defect(
                    severity="P1",
                    where="global",
                    message="未明显识别到输入层/输出层（建议包含输入与输出以增强叙事闭环）",
                    dimension="structure",
                )
            )

    return {
        "dimension": "structure",
        "score": _score_from_defects(defects),
        "metrics": metrics,
        "defects": [asdict(d) for d in defects],
    }


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


def evaluate_visual(
    spec: SchematicSpec,
    config: Dict[str, Any],
    *,
    palette: Optional[Dict[str, Any]] = None,
    png_path: Optional[Path] = None,
) -> Dict[str, Any]:
    if palette is None:
        palette = load_palette_from_assets(config)

    defects: List[Defect] = []
    metrics: Dict[str, Any] = {}

    bg_hex = (config.get("renderer", {}) or {}).get("background", "#FFFFFF")
    bg = _safe_hex_to_rgb(bg_hex) or (255, 255, 255)
    text_hex = palette.get("text", "#1F1F1F")
    text = _safe_hex_to_rgb(text_hex) or (31, 31, 31)

    # WCAG contrast checks: treat as "print risk" proxy.
    # For large text, 3.0 is acceptable, but we still warn at 4.5 for robustness.
    contrast_p0 = float((config.get("evaluation", {}) or {}).get("thresholds", {}).get("wcag_contrast_p0", 3.0))
    contrast_p1 = float((config.get("evaluation", {}) or {}).get("thresholds", {}).get("wcag_contrast_p1", 4.5))
    metrics["wcag_contrast_p0"] = contrast_p0
    metrics["wcag_contrast_p1"] = contrast_p1

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
        c_text = _contrast_ratio(fill, text)
        c_bg = _contrast_ratio(fill, bg)
        per_kind[str(kind)] = {
            "fill": fill_hex,
            "stroke": stroke_hex,
            "contrast_to_text": c_text,
            "contrast_to_bg": c_bg,
        }
        if c_text < contrast_p0:
            defects.append(
                Defect(
                    severity="P0",
                    where=f"color_scheme:{kind}",
                    message=f"{kind} 节点文字对比度过低（contrast={c_text:.2f} < {contrast_p0:.1f}），打印后可能不可读",
                    dimension="visual_contrast",
                )
            )
        elif c_text < contrast_p1:
            defects.append(
                Defect(
                    severity="P1",
                    where=f"color_scheme:{kind}",
                    message=f"{kind} 节点文字对比度偏低（contrast={c_text:.2f} < {contrast_p1:.1f}），建议提高对比度",
                    dimension="visual_contrast",
                )
            )

        if c_bg < 1.3:
            defects.append(
                Defect(
                    severity="P2",
                    where=f"color_scheme:{kind}",
                    message=f"{kind} 填充色与背景过于接近（contrast={c_bg:.2f}），打印后边界感可能不足",
                    dimension="visual_contrast",
                )
            )

        if stroke is not None:
            per_kind[str(kind)]["stroke_contrast_to_bg"] = _contrast_ratio(stroke, bg)

    metrics["kinds"] = per_kind

    group_bg = palette.get("group_bg", {})
    if isinstance(group_bg, dict):
        gfill = _safe_hex_to_rgb(group_bg.get("fill"))
        if gfill is not None:
            c = _contrast_ratio(gfill, text)
            metrics["group_bg_contrast_to_text"] = c
            if c < contrast_p0:
                defects.append(
                    Defect(
                        severity="P0",
                        where="color_scheme:group_bg",
                        message=f"分组标题文字对比度过低（contrast={c:.2f} < {contrast_p0:.1f}）",
                        dimension="visual_contrast",
                    )
                )
            elif c < contrast_p1:
                defects.append(
                    Defect(
                        severity="P1",
                        where="color_scheme:group_bg",
                        message=f"分组标题文字对比度偏低（contrast={c:.2f} < {contrast_p1:.1f}），建议提高对比度",
                        dimension="visual_contrast",
                    )
                )

    # Optional PNG-based proxy: gray std + density grading.
    if png_path is not None and png_path.exists():
        pixels = _downsample_gray(png_path, (240, 140))
        if pixels is None:
            defects.append(
                Defect(
                    severity="P2",
                    where="png",
                    message="缺少 Pillow 或 PNG 读取失败：跳过视觉图像 proxy（不影响主流程）",
                    dimension="visual_proxy",
                )
            )
        else:
            mean = sum(pixels) / max(1, len(pixels))
            var = sum((p - mean) ** 2 for p in pixels) / max(1, len(pixels))
            std = var ** 0.5
            metrics["png_gray_std"] = std
            if std < 6.0:
                defects.append(
                    Defect(
                        severity="P1",
                        where="png",
                        message="PNG 灰度对比度偏低（疑似过度发白或渲染异常/配色过淡）",
                        dimension="visual_proxy",
                    )
                )

            nonwhite = sum(1 for p in pixels if p < 245)
            density = nonwhite / max(1, len(pixels))
            metrics["png_density"] = density
            if density < 0.05:
                defects.append(
                    Defect(
                        severity="P2",
                        where="png",
                        message="画面元素偏稀疏（density<0.05），可考虑收紧间距提升信息密度",
                        dimension="visual_proxy",
                    )
                )
            elif density > 0.45:
                defects.append(
                    Defect(
                        severity="P1",
                        where="png",
                        message="画面元素偏拥挤（density>0.45），建议增加画布/间距或精简文案",
                        dimension="visual_proxy",
                    )
                )

    return {
        "dimension": "visual",
        "score": _score_from_defects(defects),
        "metrics": metrics,
        "defects": [asdict(d) for d in defects],
    }


def evaluate_readability(
    spec: SchematicSpec,
    config: Dict[str, Any],
    *,
    png_path: Optional[Path] = None,
) -> Dict[str, Any]:

    defects: List[Defect] = []
    metrics: Dict[str, Any] = {}

    thresholds = (config.get("evaluation", {}) or {}).get("thresholds", {})
    thresholds = thresholds if isinstance(thresholds, dict) else {}

    node_font = int(((config.get("layout", {}) or {}).get("font", {}) or {}).get("node_label_size", 26) or 26)
    edge_font = int(((config.get("layout", {}) or {}).get("font", {}) or {}).get("edge_label_size", node_font) or node_font)
    min_font = int(thresholds.get("min_font_px", 20) or 20)
    warn_font = int(thresholds.get("warn_font_px", max(min_font, 24)) or max(min_font, 24))
    min_edge_font = int(thresholds.get("min_edge_font_px", min_font) or min_font)
    warn_edge_font = int(thresholds.get("warn_edge_font_px", warn_font) or warn_font)

    metrics["node_label_size"] = node_font
    metrics["edge_label_size"] = edge_font
    metrics["min_font_px"] = min_font
    metrics["warn_font_px"] = warn_font
    metrics["min_edge_font_px"] = min_edge_font
    metrics["warn_edge_font_px"] = warn_edge_font

    if node_font < min_font:
        defects.append(
            Defect(
                severity="P0",
                where="global",
                message=f"节点字号过小：{node_font}px < {min_font}px",
                dimension="readability",
            )
        )
    elif node_font < warn_font:
        defects.append(
            Defect(
                severity="P1",
                where="global",
                message=f"节点字号偏小：{node_font}px < 建议值 {warn_font}px",
                dimension="readability",
            )
        )

    has_edge_labels = any(bool((e.label or "").strip()) for e in spec.edges)
    metrics["has_edge_labels"] = has_edge_labels
    if has_edge_labels:
        if edge_font < min_edge_font:
            defects.append(
                Defect(
                    severity="P0",
                    where="global",
                    message=f"连线标签字号过小：{edge_font}px < {min_edge_font}px",
                    dimension="readability",
                )
            )
        elif edge_font < warn_edge_font:
            defects.append(
                Defect(
                    severity="P1",
                    where="global",
                    message=f"连线标签字号偏小：{edge_font}px < 建议值 {warn_edge_font}px",
                    dimension="readability",
                )
            )

    # PNG-based density proxy (helps catch "过度拥挤/边距不足"这类人类感知问题).
    if png_path is None or not png_path.exists():
        defects.append(
            Defect(
                severity="P2",
                where="global",
                message="未提供 PNG，跳过可读性图像 proxy（建议启用 PNG 输出用于自检）",
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
                severity="P2",
                where="png",
                message="缺少 Pillow 或 PNG 读取失败：跳过可读性图像 proxy（不影响主流程）",
                dimension="readability",
            )
        )
        return {
            "dimension": "readability",
            "score": _score_from_defects(defects),
            "metrics": metrics,
            "defects": [asdict(d) for d in defects],
        }

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
                where="png",
                message=f"整体过度拥挤（density={density:.2f} >= {crowded_p0:.2f}），缩印可读性风险高",
                dimension="readability",
            )
        )
    elif density >= crowded_p1:
        defects.append(
            Defect(
                severity="P1",
                where="png",
                message=f"整体偏拥挤（density={density:.2f} >= {crowded_p1:.2f}），建议增大画布/间距或精简文本",
                dimension="readability",
            )
        )

    return {
        "dimension": "readability",
        "score": _score_from_defects(defects),
        "metrics": metrics,
        "defects": [asdict(d) for d in defects],
    }


def penalty_from_critiques(
    critiques: Dict[str, Dict[str, Any]],
    *,
    penalty_cfg: Optional[Dict[str, Any]] = None,
) -> Tuple[int, Dict[str, Any]]:
    """
    Convert critique defects into a deterministic penalty for score_total.

    Returns:
        (penalty, summary)
    """
    cfg = penalty_cfg if isinstance(penalty_cfg, dict) else {}
    w0 = int(cfg.get("p0", 6) or 6)
    w1 = int(cfg.get("p1", 3) or 3)
    w2 = int(cfg.get("p2", 1) or 1)
    # Backward-compatible config keys:
    # - max_total (preferred in this repo)
    # - max_penalty (legacy)
    max_penalty = cfg.get("max_total", cfg.get("max_penalty"))
    max_penalty_i = int(max_penalty) if isinstance(max_penalty, (int, str)) and str(max_penalty).isdigit() else None

    p0 = p1 = p2 = 0
    per_dim: Dict[str, Dict[str, int]] = {}
    defects_total = 0

    for dim, payload in critiques.items():
        if not isinstance(payload, dict):
            continue
        ds = payload.get("defects", [])
        if not isinstance(ds, list):
            continue
        for d in ds:
            if not isinstance(d, dict):
                continue
            sev = str(d.get("severity", "")).strip()
            defects_total += 1
            per_dim.setdefault(dim, {"P0": 0, "P1": 0, "P2": 0})
            if sev == "P0":
                p0 += 1
                per_dim[dim]["P0"] += 1
            elif sev == "P1":
                p1 += 1
                per_dim[dim]["P1"] += 1
            elif sev == "P2":
                p2 += 1
                per_dim[dim]["P2"] += 1

    penalty = p0 * w0 + p1 * w1 + p2 * w2
    if max_penalty_i is not None:
        penalty = min(max_penalty_i, penalty)

    return penalty, {
        "weights": {"p0": w0, "p1": w1, "p2": w2, "max_total": max_penalty_i},
        "counts": {"p0": p0, "p1": p1, "p2": p2, "defects_total": defects_total},
        "per_dimension": per_dim,
    }


def evaluate_structure_from_files(spec_yaml: Path, config_yaml: Path) -> Dict[str, Any]:
    spec, config = _load_spec_and_config(spec_yaml, config_yaml)
    return evaluate_structure(spec, config)


def evaluate_visual_from_files(spec_yaml: Path, config_yaml: Path, *, png_path: Optional[Path]) -> Dict[str, Any]:
    spec, config = _load_spec_and_config(spec_yaml, config_yaml)
    palette = load_palette_from_assets(config)
    return evaluate_visual(spec, config, palette=palette, png_path=png_path)


def evaluate_readability_from_files(spec_yaml: Path, config_yaml: Path, *, png_path: Optional[Path]) -> Dict[str, Any]:
    spec, config = _load_spec_and_config(spec_yaml, config_yaml)
    return evaluate_readability(spec, config, png_path=png_path)


def run_critiques(
    spec_yaml: Path,
    config_yaml: Path,
    png_path: Optional[Path],
    dimensions: Iterable[str],
    max_workers: int = 3,
) -> Dict[str, Dict[str, Any]]:
    """
    Backward-compatible helper: run critique on file inputs.
    """
    dims = [str(d).strip() for d in dimensions if str(d).strip()]
    if not dims:
        return {}

    from concurrent.futures import ThreadPoolExecutor, as_completed

    def one(dim: str) -> Tuple[str, Dict[str, Any]]:
        if dim == "structure":
            return dim, evaluate_structure_from_files(spec_yaml, config_yaml)
        if dim == "visual":
            return dim, evaluate_visual_from_files(spec_yaml, config_yaml, png_path=png_path)
        if dim == "readability":
            return dim, evaluate_readability_from_files(spec_yaml, config_yaml, png_path=png_path)
        return dim, {"dimension": dim, "score": 100, "metrics": {}, "defects": []}

    results: Dict[str, Dict[str, Any]] = {}
    workers = max(1, min(int(max_workers or 1), len(dims)))
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = [ex.submit(one, dim) for dim in dims]
        for f in as_completed(futs):
            dim, res = f.result()
            results[dim] = res
    return results


def write_ai_dimension_protocol(
    out_dir: Path,
    *,
    spec: SchematicSpec,
    config: Dict[str, Any],
    palette: Optional[Dict[str, Any]],
    png_path: Optional[Path],
) -> Tuple[Path, Path, Path]:
    """
    AI 模式协议适配器：输出纯度量 + request/response 模板（不调用任何外部模型）。

    Files:
    - dimension_measurements.json
    - ai_dimension_request.md
    - ai_dimension_response.json
    """
    out_dir.mkdir(parents=True, exist_ok=True)

    measurements_path = out_dir / "dimension_measurements.json"
    request_path = out_dir / "ai_dimension_request.md"
    response_path = out_dir / "ai_dimension_response.json"

    payload: Dict[str, Any] = {
        "measurements": {
            "structure": measure_structure_metrics(spec, config),
            "readability": measure_readability_metrics(spec, config, png_path=png_path),
        }
    }
    if palette is not None:
        payload["measurements"]["visual"] = measure_visual_metrics(spec, config, palette=palette, png_path=png_path)
    else:
        payload["measurements"]["visual"] = None

    measurements_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if not request_path.exists():
        request_lines = [
            "# AI Dimension Critique Request (nsfc-schematic)",
            "",
            "你是严格的多维度图稿评审员。请基于 `dimension_measurements.json`（必要时结合 PNG）输出三个维度的缺陷清单。",
            "",
            "## 输入证据",
            "",
            f"- dimension_measurements: `{measurements_path.name}`",
            f"- png: `{png_path.name}`" if isinstance(png_path, Path) else "- png: N/A",
            "",
            "## 输出（写入 ai_dimension_response.json）",
            "",
            "```json",
            "{",
            "  \"structure\": {\"dimension\": \"structure\", \"score\": 100, \"metrics\": {}, \"defects\": []},",
            "  \"visual\": {\"dimension\": \"visual\", \"score\": 100, \"metrics\": {}, \"defects\": []},",
            "  \"readability\": {\"dimension\": \"readability\", \"score\": 100, \"metrics\": {}, \"defects\": []}",
            "}",
            "```",
            "",
            "说明：",
            "- 每个维度的 `defects[]` 项必须包含：severity(P0/P1/P2)、where、message、dimension。",
            "- `score` 可选（不填也可），脚本会按缺陷线性扣分计算 penalty。",
            "",
        ]
        request_path.write_text("\n".join(request_lines), encoding="utf-8")

    if not response_path.exists():
        response_path.write_text(
            json.dumps(
                {
                    "structure": {"dimension": "structure", "score": 100, "metrics": {}, "defects": []},
                    "visual": {"dimension": "visual", "score": 100, "metrics": {}, "defects": []},
                    "readability": {"dimension": "readability", "score": 100, "metrics": {}, "defects": []},
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

    return measurements_path, request_path, response_path


def main() -> None:
    import argparse

    p = argparse.ArgumentParser(description="Evaluate a single critique dimension for nsfc-schematic.")
    p.add_argument("--dimension", required=True, type=str, help="structure|visual|readability")
    p.add_argument("--spec", required=True, type=Path)
    p.add_argument("--config", required=True, type=Path)
    p.add_argument("--png", required=False, type=Path, default=None)
    p.add_argument("--out", required=False, type=Path, default=None)
    args = p.parse_args()

    dim = str(args.dimension).strip()
    if dim == "structure":
        result = evaluate_structure_from_files(args.spec, args.config)
    elif dim == "visual":
        result = evaluate_visual_from_files(args.spec, args.config, png_path=args.png)
    elif dim == "readability":
        result = evaluate_readability_from_files(args.spec, args.config, png_path=args.png)
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
