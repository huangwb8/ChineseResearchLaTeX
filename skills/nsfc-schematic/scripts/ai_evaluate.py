from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import json

from spec_parser import SchematicSpec
from utils import dump_yaml, write_text


AI_EVAL_REQUEST_MD = "ai_eval_request.md"
AI_EVAL_RESPONSE_JSON = "ai_eval_response.json"


def _json_load(path: Path) -> Optional[Dict[str, Any]]:
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
        dim = str(d.get("dimension", "")).strip() or "unknown"
        msg = str(d.get("message", "")).strip()
        if not msg:
            continue
        item: Dict[str, Any] = {"severity": sev, "where": where, "dimension": dim, "message": msg}
        sug = d.get("suggestion")
        if isinstance(sug, dict):
            item["suggestion"] = sug
        out.append(item)
    return out


def _summarize_spec(spec: SchematicSpec) -> Dict[str, Any]:
    return {
        "title": spec.title,
        "canvas": {"width": spec.canvas_width, "height": spec.canvas_height},
        "direction": spec.direction,
        "groups": [
            {
                "id": g.id,
                "label": g.label,
                "children": [{"id": n.id, "label": n.label, "kind": n.kind} for n in g.children],
            }
            for g in spec.groups
        ],
        "edges": [{"from": e.source, "to": e.target, "label": e.label, "style": e.style} for e in spec.edges],
    }


def _pick_config_key_params(config: Dict[str, Any]) -> Dict[str, Any]:
    layout = config.get("layout", {}) if isinstance(config.get("layout"), dict) else {}
    font = layout.get("font", {}) if isinstance(layout.get("font"), dict) else {}
    auto = layout.get("auto", {}) if isinstance(layout.get("auto"), dict) else {}
    canvas = (config.get("renderer", {}) or {}).get("canvas", {})
    canvas = canvas if isinstance(canvas, dict) else {}
    return {
        "canvas": {"width_px": canvas.get("width_px"), "height_px": canvas.get("height_px")},
        "font": {
            "title_size": font.get("title_size"),
            "group_label_size": font.get("group_label_size"),
            "node_label_size": font.get("node_label_size"),
            "edge_label_size": font.get("edge_label_size"),
        },
        "layout_gaps": {
            "margin_x": auto.get("margin_x"),
            "margin_y": auto.get("margin_y"),
            "group_gap_x": auto.get("group_gap_x"),
            "group_gap_y": auto.get("group_gap_y"),
            "node_gap_x": auto.get("node_gap_x"),
            "node_gap_y": auto.get("node_gap_y"),
            "max_cols": auto.get("max_cols"),
        },
        "routing": (config.get("renderer", {}) or {}).get("internal_routing", "orthogonal"),
        "color_scheme": (config.get("color_scheme", {}) or {}).get("name", ""),
    }


def prepare_ai_evaluation(
    spec: SchematicSpec,
    config: Dict[str, Any],
    png_path: Optional[Path],
    round_dir: Path,
) -> Tuple[Path, Path]:
    """
    Emit an offline AI evaluation protocol (NO external model calls).

    Files:
    - ai_eval_request.md: rich context (spec summary + key config + PNG path + schema)
    - ai_eval_response.json: response template for host AI to fill
    """
    round_dir.mkdir(parents=True, exist_ok=True)

    req = round_dir / AI_EVAL_REQUEST_MD
    resp = round_dir / AI_EVAL_RESPONSE_JSON

    # Always overwrite the request so it matches the current candidate spec/config.
    png_hint = str(png_path) if isinstance(png_path, Path) else "N/A"
    req_text = "\n".join(
        [
            "# 评估请求（nsfc-schematic）",
            "",
            "你是一个严格的图稿评审员。请结合：",
            "- spec 摘要（结构化 YAML）",
            "- config 关键参数（字号/画布/间距）",
            "- PNG 路径（如存在，请直接用 Read 工具查看）",
            "",
            "输出一个结构化 JSON 响应，写入 `ai_eval_response.json`。",
            "",
            "## 输入",
            "",
            "### spec 摘要（YAML）",
            "",
            "```yaml",
            dump_yaml(_summarize_spec(spec)).rstrip(),
            "```",
            "",
            "### config 关键参数（YAML）",
            "",
            "```yaml",
            dump_yaml(_pick_config_key_params(config)).rstrip(),
            "```",
            "",
            f"### PNG 路径\n\n- png: `{png_hint}`",
            "",
            "## 评估维度（请自主判定）",
            "",
            "1. text_readability：文字可读性（缩印/打印场景）",
            "2. layout：布局合理性（重叠/越界/平衡）",
            "3. edge：连线清晰度（交叉/穿越/端点有效）",
            "4. structure：结构完整性（分组/层次/密度）",
            "5. visual：视觉美观度（配色/对比度/拥挤度/打印友好）",
            "6. semantic：语义合理性（术语一致、连线体现正确流程/因果）",
            "",
            "## 输出 schema（写入 ai_eval_response.json）",
            "",
            "```json",
            "{",
            "  \"score\": 0,",
            "  \"score_rationale\": \"\",",
            "  \"defects\": [",
            "    {",
            "      \"severity\": \"P1\",",
            "      \"where\": \"node:xxx | edge:a->b | global\",",
            "      \"dimension\": \"text_readability|layout|edge|structure|visual|semantic\",",
            "      \"message\": \"具体问题描述\",",
            "      \"suggestion\": {\"action\": \"increase_gap\", \"parameter\": \"node_gap_x\", \"delta\": 10}",
            "    }",
            "  ]",
            "}",
            "```",
            "",
            "约束：",
            "- severity 仅允许 P0/P1/P2；suggestion 可省略。",
            "- 建议 action 仅使用：increase_canvas / increase_gap / increase_font。",
            "- delta 将被脚本做安全裁剪（避免参数溢出）。",
            "",
        ]
    )
    write_text(req, req_text + "\n")

    if not resp.exists():
        write_text(resp, json.dumps({"score": 0, "score_rationale": "", "defects": []}, ensure_ascii=False, indent=2) + "\n")

    return req, resp


def consume_ai_evaluation(resp_path: Path) -> Optional[Dict[str, Any]]:
    """
    Parse and normalize `ai_eval_response.json`.

    Returns None if the response is missing/invalid/template-like.
    """
    if not resp_path.exists() or not resp_path.is_file():
        return None

    payload = _json_load(resp_path)
    if payload is None:
        return None

    defects = _normalize_defects(payload.get("defects", []))
    try:
        score_i = int(payload.get("score", 0))
    except Exception:
        score_i = 0
    score_i = max(0, min(100, score_i))
    rationale = str(payload.get("score_rationale", "")).strip()

    # Treat a pure template as absent.
    if (not defects) and (not rationale) and (score_i == 0):
        return None

    p0 = sum(1 for d in defects if d["severity"] == "P0")
    p1 = sum(1 for d in defects if d["severity"] == "P1")
    p2 = sum(1 for d in defects if d["severity"] == "P2")
    return {
        "score": score_i,
        "score_rationale": rationale,
        "defects": defects,
        "counts_defects": {"p0": p0, "p1": p1, "p2": p2},
    }
