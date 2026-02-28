from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import json
import math
import random
import shutil
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import xml.etree.ElementTree as ET

from evaluate_dimension import (
    evaluate_readability,
    evaluate_structure,
    evaluate_visual,
    load_palette_from_assets,
    penalty_from_critiques,
)
from evaluate_schematic import evaluate_schematic
from extract_from_tex import apply_tex_hints, extract_research_terms, find_candidate_tex
from measure_schematic import measure_schematic
from render_schematic import drawio_install_hints, ensure_drawio_cli, render_artifacts
from schematic_writer import write_schematic_drawio
from spec_parser import default_schematic_spec, load_schematic_spec
from utils import dump_yaml, fatal, info, is_safe_relative_path, load_yaml, skill_root, warn, write_text


def _make_run_dir(base_dir: Path) -> Path:
    ts = datetime.now().strftime("%Y%m%d%H%M%S")
    base = base_dir / f"run_{ts}"
    if not base.exists():
        base.mkdir(parents=True, exist_ok=False)
        return base

    # Very unlikely, but keep it deterministic and safe.
    for i in range(1, 1000):
        p = base_dir / f"run_{ts}_{i:02d}"
        if not p.exists():
            p.mkdir(parents=True, exist_ok=False)
            return p
    fatal(f"无法创建 run 目录（疑似同秒并发/残留冲突）：{base_dir}")


def _resolve_output_dirs(out_dir: Path, config: Dict[str, Any]) -> Tuple[Path, Path, bool]:
    """
    Resolve output dirs.

    Returns:
        (work_dir, intermediate_dir, hide_intermediate)
    """
    output_cfg = config.get("output", {}) if isinstance(config.get("output", {}), dict) else {}
    hide = bool(output_cfg.get("hide_intermediate", True))
    intermediate_name = str(output_cfg.get("intermediate_dir", ".nsfc-schematic")).strip() or ".nsfc-schematic"
    if not is_safe_relative_path(intermediate_name):
        fatal(
            "output.intermediate_dir 必须是 output_dir 内的相对路径，且不得包含 `..` 或绝对/盘符路径："
            f"{intermediate_name!r}"
        )

    work_dir = out_dir
    if hide:
        intermediate_dir = work_dir / intermediate_name
        (intermediate_dir / "runs").mkdir(parents=True, exist_ok=True)
        (intermediate_dir / "legacy").mkdir(parents=True, exist_ok=True)
        _ensure_intermediate_gitignore(intermediate_dir)
    else:
        intermediate_dir = work_dir
    return work_dir, intermediate_dir, hide


def _ensure_intermediate_gitignore(intermediate_dir: Path) -> None:
    """
    Create a conservative .gitignore for intermediate dir.
    Don't overwrite if user already has one.
    """
    p = intermediate_dir / ".gitignore"
    if p.exists():
        return
    dirname = intermediate_dir.name or ".nsfc-schematic"
    p.write_text(
        f"# {dirname}/.gitignore\n"
        f"# 如需追踪版本历史，可删除此文件并 git add {dirname}/\n"
        "\n"
        "# 默认忽略运行历史\n"
        "/runs/\n"
        "\n"
        "# 但保留配置\n"
        "!config_local.yaml\n",
        encoding="utf-8",
    )


def _report_filename(config: Dict[str, Any]) -> str:
    output_cfg = config.get("output", {}) if isinstance(config.get("output", {}), dict) else {}
    artifacts = output_cfg.get("artifacts", {}) if isinstance(output_cfg.get("artifacts", {}), dict) else {}
    v = artifacts.get("report") or output_cfg.get("report_filename") or "optimization_report.md"
    return str(v)


def _spec_latest_filename(config: Dict[str, Any]) -> str:
    output_cfg = config.get("output", {}) if isinstance(config.get("output", {}), dict) else {}
    artifacts = output_cfg.get("artifacts", {}) if isinstance(output_cfg.get("artifacts", {}), dict) else {}
    return str(artifacts.get("spec_latest") or "spec_latest.yaml")


def _deep_merge_dict(base: Dict[str, Any], patch: Dict[str, Any]) -> Dict[str, Any]:
    out: Dict[str, Any] = deepcopy(base)
    for k, v in (patch or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge_dict(out[k], v)  # type: ignore[arg-type]
        else:
            out[k] = deepcopy(v)
    return out


def _load_config_local(config_local_path: Path) -> Optional[Dict[str, Any]]:
    if not config_local_path.exists():
        return None
    if not config_local_path.is_file():
        fatal(f"config_local 不是文件：{config_local_path}")
    return load_yaml(config_local_path)


def _sanitize_config_local(local_cfg: Dict[str, Any]) -> Dict[str, Any]:
    """
    仅允许实例级白名单覆盖，避免污染全局配置或引入不安全字段。
    """
    if not isinstance(local_cfg, dict):
        fatal("config_local.yaml 根必须是 mapping")

    def as_int(v: Any, where: str, low: int, high: int) -> int:
        try:
            n = int(v)
        except Exception:
            fatal(f"config_local.{where} 必须是整数")
        if n < low or n > high:
            fatal(f"config_local.{where} 超出范围：{n}（允许 {low}..{high}）")
        return n

    def as_str(v: Any, where: str) -> str:
        if not isinstance(v, str) or not v.strip():
            fatal(f"config_local.{where} 必须是非空字符串")
        return v.strip()

    allowed_tops = {"renderer", "layout", "color_scheme", "evaluation"}
    bad = [k for k in local_cfg.keys() if k not in allowed_tops]
    if bad:
        fatal(
            "config_local.yaml 包含未允许的顶层字段（为安全起见已拒绝）："
            + ", ".join(bad[:20])
            + (" ..." if len(bad) > 20 else "")
        )

    out: Dict[str, Any] = {}

    renderer = local_cfg.get("renderer")
    if isinstance(renderer, dict):
        r_out: Dict[str, Any] = {}
        canvas = renderer.get("canvas")
        if isinstance(canvas, dict):
            c_out: Dict[str, Any] = {}
            if "width_px" in canvas:
                c_out["width_px"] = as_int(canvas.get("width_px"), "renderer.canvas.width_px", 1200, 12000)
            if "height_px" in canvas:
                c_out["height_px"] = as_int(canvas.get("height_px"), "renderer.canvas.height_px", 900, 12000)
            if c_out:
                r_out["canvas"] = c_out
        stroke = renderer.get("stroke")
        if isinstance(stroke, dict):
            s_out: Dict[str, Any] = {}
            if "width_px" in stroke:
                s_out["width_px"] = as_int(stroke.get("width_px"), "renderer.stroke.width_px", 1, 20)
            if s_out:
                r_out["stroke"] = s_out
        if r_out:
            out["renderer"] = r_out

    layout = local_cfg.get("layout")
    if isinstance(layout, dict):
        l_out: Dict[str, Any] = {}
        if "direction" in layout:
            d = as_str(layout.get("direction"), "layout.direction")
            if d not in {"top-to-bottom", "left-to-right", "bottom-to-top"}:
                fatal("config_local.layout.direction 不合法（允许 top-to-bottom|left-to-right|bottom-to-top）")
            l_out["direction"] = d
        font = layout.get("font")
        if isinstance(font, dict):
            f_out: Dict[str, Any] = {}
            if "node_label_size" in font:
                f_out["node_label_size"] = as_int(font.get("node_label_size"), "layout.font.node_label_size", 14, 60)
            if "edge_label_size" in font:
                f_out["edge_label_size"] = as_int(font.get("edge_label_size"), "layout.font.edge_label_size", 14, 60)
            if f_out:
                l_out["font"] = f_out
        if "auto_edges" in layout:
            m = as_str(layout.get("auto_edges"), "layout.auto_edges").strip().lower()
            if m not in {"minimal", "off", "none"}:
                fatal("config_local.layout.auto_edges 不合法（允许 minimal|off）")
            l_out["auto_edges"] = "off" if m in {"off", "none"} else "minimal"
        if l_out:
            out["layout"] = l_out

    cs = local_cfg.get("color_scheme")
    if isinstance(cs, dict) and "name" in cs:
        name = as_str(cs.get("name"), "color_scheme.name")
        if name not in {"academic-blue", "tint-layered"}:
            fatal("config_local.color_scheme.name 仅允许 {academic-blue, tint-layered}。")
        out["color_scheme"] = {"name": name}

    ev = local_cfg.get("evaluation")
    if isinstance(ev, dict):
        e_out: Dict[str, Any] = {}
        if "stop_strategy" in ev:
            s = as_str(ev.get("stop_strategy"), "evaluation.stop_strategy")
            if s not in {"none", "plateau", "ai_critic"}:
                fatal("config_local.evaluation.stop_strategy 不合法（允许 none|plateau|ai_critic）")
            e_out["stop_strategy"] = s
        if "max_rounds" in ev:
            e_out["max_rounds"] = as_int(ev.get("max_rounds"), "evaluation.max_rounds", 1, 20)
        if e_out:
            out["evaluation"] = e_out

    return out


def _apply_config_local(base_cfg: Dict[str, Any], local_cfg: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not local_cfg:
        return deepcopy(base_cfg)
    sanitized = _sanitize_config_local(local_cfg)
    return _deep_merge_dict(base_cfg, sanitized)


def _ai_root(intermediate_dir: Path) -> Path:
    p = intermediate_dir / "ai"
    p.mkdir(parents=True, exist_ok=True)
    return p


def _ai_active_run_file(ai_root: Path) -> Path:
    return ai_root / "ACTIVE_RUN.txt"


def _read_active_run(ai_root: Path) -> Optional[str]:
    p = _ai_active_run_file(ai_root)
    if not p.exists() or not p.is_file():
        return None
    s = p.read_text(encoding="utf-8").strip()
    return s or None


def _set_active_run(ai_root: Path, run_dir: Path) -> None:
    _ai_active_run_file(ai_root).write_text(run_dir.name + "\n", encoding="utf-8")


def _clear_active_run(ai_root: Path) -> None:
    p = _ai_active_run_file(ai_root)
    if p.exists():
        try:
            p.unlink()
        except Exception:
            pass


def _ai_run_root(ai_root: Path, run_dir: Path) -> Path:
    p = ai_root / run_dir.name
    p.mkdir(parents=True, exist_ok=True)
    return p


def _ai_response_path(ai_run_root: Path) -> Path:
    return ai_run_root / "ai_critic_response.yaml"


def _ai_request_path(ai_run_root: Path) -> Path:
    return ai_run_root / "ai_critic_request.md"


def _ai_pack_dir(ai_run_root: Path, round_idx: int) -> Path:
    return ai_run_root / f"ai_pack_round_{round_idx:02d}"


def _safe_move_to_dir(src: Path, dst_dir: Path) -> Optional[Path]:
    if not src.exists():
        return None
    dst_dir.mkdir(parents=True, exist_ok=True)
    dst = dst_dir / src.name
    if not dst.exists():
        shutil.move(str(src), str(dst))
        return dst
    # Avoid overwriting: append a numeric suffix.
    stem = src.stem
    suffix = src.suffix
    for i in range(1, 1000):
        cand = dst_dir / f"{stem}_{i:02d}{suffix}"
        if not cand.exists():
            shutil.move(str(src), str(cand))
            return cand
    fatal(f"无法移动到 legacy（目标冲突过多）：{src}")
    return None


def _cleanup_work_dir(work_dir: Path, intermediate_dir: Path, artifacts: Dict[str, Any], hide: bool) -> None:
    """
    Cleanup known intermediate residues from work_dir root.

    When hide_intermediate=true, only keep deliverables in work_dir root and
    move known intermediate files/dirs into intermediate_dir/legacy/.
    """
    if not hide:
        return

    legacy_root = intermediate_dir / "legacy"
    legacy_runs = legacy_root / "runs"
    legacy_files = legacy_root / "files"

    keep = {
        str(artifacts.get("drawio", "schematic.drawio")),
        str(artifacts.get("svg", "schematic.svg")),
        str(artifacts.get("png", "schematic.png")),
        str(artifacts.get("pdf", "schematic.pdf")),
    }
    known_intermediate = {
        "optimization_report.md",
        "spec.yaml",
        "spec_latest.yaml",
        "spec_seqccs.yaml",
        "config_used_best.yaml",
        "config_used_latest.yaml",
        "evaluation_best.json",
        "evaluation_latest.json",
        "config_local.yaml",
        "schematic.drawio.unescaped",
    }

    for p in work_dir.iterdir():
        if p.name.startswith("."):
            continue
        if p.name in keep:
            continue

        if p.is_dir() and p.name.startswith("run_"):
            _safe_move_to_dir(p, legacy_runs)
            continue

        if p.is_file():
            if p.name in known_intermediate:
                _safe_move_to_dir(p, legacy_files)
                continue
            if p.suffix == ".unescaped":
                _safe_move_to_dir(p, legacy_files)
                continue


def _prune_history_runs(intermediate_dir: Path, max_runs: int) -> None:
    if max_runs <= 0:
        return
    runs_dir = intermediate_dir / "runs"
    if not runs_dir.exists() or not runs_dir.is_dir():
        return

    runs = [p for p in runs_dir.iterdir() if p.is_dir() and p.name.startswith("run_")]
    # Names are timestamped; lexical sort is good enough and stable.
    runs.sort(key=lambda p: p.name)
    if len(runs) <= max_runs:
        return
    for p in runs[: len(runs) - max_runs]:
        shutil.rmtree(p, ignore_errors=True)


def _validate_drawio_xml(drawio_path: Path) -> None:
    try:
        ET.parse(drawio_path)
    except ET.ParseError as exc:
        line, col = getattr(exc, "position", (None, None))
        pos = f"（line={line}, col={col}）" if line is not None and col is not None else ""
        raise ValueError(
            "生成的 .drawio 不是合法 XML，已阻断渲染与评估。"
            f"{pos}\n"
            f"- file: {drawio_path}\n"
            "- 常见原因：label 中包含未转义的 `<br>`/`<`/`>`（例如把换行直接替换成 `<br>` 但未做 XML escape）。\n"
            "- 建议：检查 `schematic_writer.py` 的 XML 转义逻辑，或在 label 中用 `\\n` 并确保最终写入的是 `&lt;br&gt;`。"
        ) from exc


def _load_input_spec(args: argparse.Namespace, config: Dict[str, Any], request_dir: Path) -> Dict[str, Any]:
    if args.spec_file:
        if not args.spec_file.exists() or not args.spec_file.is_file():
            fatal(f"spec_file 不存在或不是文件：{args.spec_file}")
        info(f"使用用户 spec: {args.spec_file}")
        return load_yaml(args.spec_file)

    spec = default_schematic_spec()

    tex_path: Optional[Path] = None
    if args.proposal_file:
        if not args.proposal_file.exists() or not args.proposal_file.is_file():
            fatal(f"proposal_file 不存在或不是文件：{args.proposal_file}")
        tex_path = args.proposal_file
    elif args.proposal_path:
        if not args.proposal_path.exists():
            fatal(f"proposal_path 不存在：{args.proposal_path}")
        tex_path = find_candidate_tex(args.proposal_path)

    if tex_path:
        eval_mode = str((config.get("evaluation", {}) or {}).get("evaluation_mode", "heuristic")).strip().lower()
        if eval_mode == "ai":
            try:
                from ai_extract_tex import AI_TEX_RESPONSE_JSON, consume_tex_extraction, prepare_tex_extraction_request

                req, resp = prepare_tex_extraction_request(tex_path, config=config, output_dir=request_dir)
                payload = consume_tex_extraction(resp)
                if payload and isinstance(payload.get("spec_draft"), dict) and payload.get("spec_draft"):
                    info(f"已检测到 AI TEX 提取响应：{resp.name}，将直接使用 spec_draft")
                    return payload["spec_draft"]
                info(f"AI TEX 提取协议已生成：{req.name} + {AI_TEX_RESPONSE_JSON}（未检测到有效响应，已降级为正则抽取）")
            except Exception as exc:
                warn(f"AI TEX 提取协议生成/消费失败，已降级为正则抽取（{exc}）")

        terms = extract_research_terms(tex_path, max_terms=8)
        spec = apply_tex_hints(spec, terms)
        root = spec.get("schematic", spec)
        if isinstance(root, dict):
            root["title"] = "NSFC 原理图（自动生成）"
        info(f"已从 TEX 抽取 {len(terms)} 个术语用于填充示例节点")
    else:
        info("未提供可用 TEX，使用默认示例 spec")

    return spec


def _apply_auto_fixes(cfg: Dict[str, Any], evaluation: Dict[str, Any]) -> Dict[str, Any]:
    out = deepcopy(cfg)
    counts = evaluation.get("counts", {}) if isinstance(evaluation.get("counts", {}), dict) else {}
    p0 = int(counts.get("p0", 0))
    p1 = int(counts.get("p1", 0))

    canvas = out["renderer"]["canvas"]
    layout_font = out["layout"]["font"]
    auto = out["layout"]["auto"]

    defects = evaluation.get("defects", [])
    if not isinstance(defects, list):
        defects = []

    layout_mode = evaluation.get("layout_mode", {}) if isinstance(evaluation.get("layout_mode", {}), dict) else {}
    explicit_layout = bool(layout_mode.get("explicit_layout", False))

    # AI-mode: apply host AI suggestions (if provided) with strict safety guards.
    if str(evaluation.get("evaluation_source", "")).strip().lower() == "ai":
        thresholds = out.get("evaluation", {}).get("thresholds", {})
        thresholds = thresholds if isinstance(thresholds, dict) else {}
        min_font = int(thresholds.get("min_font_px", 18) or 18)
        min_edge_font = int(thresholds.get("min_edge_font_px", min_font) or min_font)

        allowed_gaps = {"node_gap_x", "node_gap_y", "group_gap_x", "group_gap_y"}
        allowed_fonts = {"node_label_size", "edge_label_size"}

        changed = False
        applied = 0
        for d in defects:
            if not isinstance(d, dict):
                continue
            sug = d.get("suggestion")
            if not isinstance(sug, dict):
                continue
            action = str(sug.get("action", "")).strip()
            if not action:
                continue

            if applied >= 6:
                break

            if action == "increase_canvas":
                try:
                    dw = int(sug.get("delta_w", sug.get("delta", 0)) or 0)
                    dh = int(sug.get("delta_h", sug.get("delta", 0)) or 0)
                except Exception:
                    continue
                if dw:
                    dw = max(40, min(300, dw))
                    canvas["width_px"] = int(canvas["width_px"]) + dw
                    changed = True
                    applied += 1
                if dh:
                    dh = max(40, min(300, dh))
                    canvas["height_px"] = int(canvas["height_px"]) + dh
                    changed = True
                    applied += 1
                continue

            if action == "increase_gap":
                param = str(sug.get("parameter", "")).strip()
                if param not in allowed_gaps:
                    continue
                try:
                    delta = int(sug.get("delta", 0) or 0)
                except Exception:
                    continue
                if not delta:
                    continue
                delta = max(2, min(20, delta))
                auto[param] = int(auto.get(param, 0)) + delta
                changed = True
                applied += 1
                continue

            if action == "increase_font":
                param = str(sug.get("parameter", "")).strip()
                if param not in allowed_fonts:
                    continue
                if explicit_layout and param == "node_label_size":
                    # 显式布局模式下避免节点整体膨胀。
                    continue
                try:
                    delta = int(sug.get("delta", 0) or 0)
                except Exception:
                    continue
                if not delta:
                    continue
                delta = max(1, min(4, delta))
                layout_font[param] = int(layout_font.get(param, 0) or 0) + delta
                changed = True
                applied += 1
                continue

        if changed:
            layout_font["node_label_size"] = max(min_font, int(layout_font.get("node_label_size", min_font) or min_font))
            layout_font["edge_label_size"] = max(
                min_edge_font, int(layout_font.get("edge_label_size", min_edge_font) or min_edge_font)
            )
            return out

    dims_p0 = {str(d.get("dimension", "")) for d in defects if isinstance(d, dict) and str(d.get("severity")) == "P0"}
    dims_p1 = {str(d.get("dimension", "")) for d in defects if isinstance(d, dict) and str(d.get("severity")) == "P1"}
    dims_any = {str(d.get("dimension", "")) for d in defects if isinstance(d, dict)}

    thresholds = out.get("evaluation", {}).get("thresholds", {})
    if not isinstance(thresholds, dict):
        thresholds = {}

    min_font = int(thresholds.get("min_font_px", 18))
    min_edge_font = int(thresholds.get("min_edge_font_px", min_font))
    print_scale_check = bool(thresholds.get("print_scale_check", False))

    # Readability repair: prioritize edge labels, avoid inflating node font on explicit layout.
    if "print_readability" in dims_any or "text_readability" in dims_any:
        if print_scale_check:
            scale = float(thresholds.get("print_scale_ratio", 0.5))
            min_after_scale = int(thresholds.get("print_scale_min_font", 10))
            suggest = int(math.ceil(min_after_scale / max(1e-9, scale)))
        else:
            suggest = int(thresholds.get("warn_edge_font_px", thresholds.get("warn_font_px", 24)) or 24)

        cur_edge = int(layout_font.get("edge_label_size", min_edge_font))
        if cur_edge < suggest:
            step = 2 if (suggest - cur_edge) > 2 else 1
            layout_font["edge_label_size"] = cur_edge + step

        # 仅当节点字号本身低于硬下限时修复；不再跟随 edge 一起暴涨。
        cur_node = int(layout_font.get("node_label_size", min_font))
        if cur_node < min_font:
            layout_font["node_label_size"] = min_font

    hard_layout_dims = {"canvas_overflow", "node_overlap", "edge_integrity", "edge_crossings", "edge_node_intersection"}
    if bool(hard_layout_dims & (dims_p0 | dims_p1)) or p0 > 0:
        # 显式布局下保守处理，优先微调而不是大幅放大。
        if explicit_layout:
            canvas["width_px"] = int(canvas["width_px"]) + 60
            canvas["height_px"] = int(canvas["height_px"]) + 60
            auto["group_gap_y"] = int(auto.get("group_gap_y", 80)) + 4
        else:
            canvas["width_px"] = int(canvas["width_px"]) + 140
            canvas["height_px"] = int(canvas["height_px"]) + 140
            auto["node_gap_x"] = int(auto.get("node_gap_x", 40)) + 8
            auto["node_gap_y"] = int(auto.get("node_gap_y", 28)) + 8
            auto["group_gap_y"] = int(auto.get("group_gap_y", 80)) + 8
        return out

    if {"edge_label_occlusion", "edge_node_proximity"} & dims_any:
        auto["node_gap_x"] = int(auto.get("node_gap_x", 40)) + 6
        auto["node_gap_y"] = int(auto.get("node_gap_y", 28)) + 6
        auto["group_gap_y"] = int(auto.get("group_gap_y", 80)) + 6
        cur_edge = int(layout_font.get("edge_label_size", min_edge_font))
        layout_font["edge_label_size"] = max(cur_edge, min_edge_font) + 1
        return out

    if "space_usage" in dims_any:
        # 对自动布局收紧边距，提升画布利用率。
        auto["margin_x"] = max(40, int(auto.get("margin_x", 110)) - 10)
        auto["margin_y"] = max(40, int(auto.get("margin_y", 120)) - 10)
        if int(out.get("renderer", {}).get("drawio_border_px", 4)) > 0:
            out["renderer"]["drawio_border_px"] = max(0, int(out["renderer"]["drawio_border_px"]) - 1)
        return out

    if "title_layout_overlap" in dims_any:
        out.setdefault("layout", {}).setdefault("title", {})["enabled"] = False
        return out

    if p1 > 0 and {"visual_balance", "overall_aesthetics", "text_overflow"} & dims_p1:
        canvas["height_px"] = int(canvas["height_px"]) + 100
        auto["group_gap_y"] = int(auto.get("group_gap_y", 80)) + 8
        return out

    # 轻微恢复字号，让通过后的图观感更好（不强制推高）。
    current = int(layout_font.get("node_label_size", min_font))
    target = int(out["layout"]["font"].get("node_label_size_target", current))
    if current < target and "text_overflow" not in dims_any and not explicit_layout:
        layout_font["node_label_size"] = current + 1

    layout_font["edge_label_size"] = max(min_edge_font, int(layout_font.get("edge_label_size", min_edge_font)))
    layout_font["node_label_size"] = max(min_font, int(layout_font.get("node_label_size", min_font)))
    return out


def _load_json_if_exists(path: Path) -> Optional[Dict[str, Any]]:
    if not path.exists() or not path.is_file():
        return None
    try:
        raw = path.read_text(encoding="utf-8")
    except Exception:
        return None
    try:
        data = json.loads(raw)
    except Exception:
        return None
    return data if isinstance(data, dict) else None


def _copy_if_exists(src: Path, dst: Path) -> None:
    if not src.exists() or not src.is_file():
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_bytes(src.read_bytes())


def _sha256_file(path: Path) -> Optional[str]:
    if not path.exists() or not path.is_file():
        return None
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            chunk = f.read(1024 * 1024)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def _severity_rank(s: str) -> int:
    return {"P0": 0, "P1": 1, "P2": 2}.get(str(s).upper(), 9)


def _top_defects(defects: Any, *, limit: int = 6) -> List[Dict[str, str]]:
    if not isinstance(defects, list):
        return []
    items: List[Dict[str, str]] = []
    for d in defects:
        if not isinstance(d, dict):
            continue
        sev = str(d.get("severity", "")).strip().upper() or "P2"
        where = str(d.get("where", "")).strip() or "global"
        msg = str(d.get("message", "")).strip()
        dim = str(d.get("dimension", "")).strip() or "unknown"
        if not msg:
            continue
        items.append({"severity": sev, "where": where, "message": msg, "dimension": dim})
    items.sort(key=lambda x: (_severity_rank(x["severity"]), x["dimension"], x["where"], x["message"]))
    return items[: max(0, int(limit))]


def _write_ai_pack(
    ai_run_root: Path,
    *,
    round_idx: int,
    round_dir: Path,
    spec_dict: Dict[str, Any],
    cfg_used: Dict[str, Any],
    evaluation: Dict[str, Any],
    png_path: Optional[Path],
) -> Path:
    pack = _ai_pack_dir(ai_run_root, round_idx)
    pack.mkdir(parents=True, exist_ok=True)

    write_text(pack / "spec.yaml", dump_yaml(spec_dict))
    write_text(pack / "config_used.yaml", dump_yaml(cfg_used))
    (pack / "evaluation.json").write_text(json.dumps(evaluation, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    for name in ["layout_debug.json", "edge_debug.json", "measurements.json", "dimension_measurements.json"]:
        _copy_if_exists(round_dir / name, pack / name)
    if png_path is not None:
        _copy_if_exists(png_path, pack / "schematic.png")
    return pack


def _write_ai_critic_request(
    ai_run_root: Path,
    *,
    round_idx: int,
    pack_dir: Path,
    response_path: Path,
) -> None:
    lines: List[str] = []
    lines.append("# nsfc-schematic ai_critic request")
    lines.append("")
    lines.append(f"- based_on_round: {round_idx}")
    lines.append(f"- evidence_pack: `{pack_dir.as_posix()}`")
    lines.append(f"- write_response_to: `{response_path.as_posix()}`")
    lines.append("")
    lines.append("## 任务")
    lines.append("")
    lines.append("请基于 `schematic.png` 的读图批判，以及 `evaluation.json / layout_debug.json / edge_debug.json` 输出下一步行动。")
    lines.append("支持 spec 重写、config_local patch，或明确 stop。")
    lines.append("")
    lines.append("## 输出约束（必须满足）")
    lines.append("")
    lines.append("请写入 YAML 到 `ai_critic_response.yaml`，结构如下：")
    lines.append("")
    lines.append("```yaml")
    lines.append("version: 1")
    lines.append("based_on_round: 1")
    lines.append("action: both  # spec_only|config_only|both|stop")
    lines.append("reason: \"一句话说明本轮行动与停止/继续依据\"")
    lines.append("# 可选：完整 spec（建议给全量）")
    lines.append("# spec:")
    lines.append("#   schematic:")
    lines.append("#     title: ...")
    lines.append("#     groups: ...")
    lines.append("# 可选：config_local patch（仅白名单字段）")
    lines.append("# config_local:")
    lines.append("#   layout:")
    lines.append("#     direction: top-to-bottom")
    lines.append("#     font:")
    lines.append("#       node_label_size: 28")
    lines.append("#   color_scheme:")
    lines.append("#     name: tint-layered")
    lines.append("```")
    lines.append("")
    lines.append("### 纠偏原则（必须遵守）")
    lines.append("")
    lines.append("- density 拥挤优先改 spec（缩短文案/合并节点），不要靠缩字号硬过阈值。")
    lines.append("- 只有 overflow 风险时才减字号；若字号偏小且无 overflow，应增字号。")
    lines.append("- 配色干扰优先改 kind 分配；不要靠黑白方案掩盖结构问题。")
    lines.append("- config_local.color_scheme.name 仅允许 {academic-blue, tint-layered}。")
    lines.append("")
    write_text(_ai_request_path(ai_run_root), "\n".join(lines) + "\n")

    if not response_path.exists():
        write_text(
            response_path,
            dump_yaml(
                {
                    "version": 1,
                    "based_on_round": int(round_idx),
                    "action": "stop",
                    "reason": "",
                }
            ),
        )


def _maybe_apply_ai_response(
    ai_run_root: Path,
    spec_data: Dict[str, Any],
    spec_latest_path: Path,
    base_config: Dict[str, Any],
) -> Tuple[Dict[str, Any], Optional[Dict[str, Any]], Optional[str]]:
    """
    Returns: (updated_spec_data, config_local_patch, action)
    """
    resp_path = _ai_response_path(ai_run_root)
    if not resp_path.exists():
        return spec_data, None, None

    resp = load_yaml(resp_path)
    if int(resp.get("version", 1) or 1) != 1:
        fatal(f"ai_critic_response.version 不支持：{resp.get(version)}")

    action = str(resp.get("action", "") or "").strip()
    if action not in {"spec_only", "config_only", "both", "stop"}:
        fatal("ai_critic_response.action 必须是 spec_only|config_only|both|stop")

    based = resp.get("based_on_round")
    try:
        based_i = int(based) if based is not None else 0
    except Exception:
        based_i = 0
    archive = ai_run_root / f"ai_critic_response_applied_round_{based_i:02d}.yaml"
    if not archive.exists():
        _copy_if_exists(resp_path, archive)
    try:
        resp_path.unlink()
    except Exception:
        pass

    new_spec = resp.get("spec")
    if action in {"spec_only", "both", "stop"} and new_spec is not None:
        if not isinstance(new_spec, dict):
            fatal("ai_critic_response.spec 必须是 mapping（完整 spec）")
        load_schematic_spec(new_spec, base_config)
        spec_data = new_spec
        write_text(spec_latest_path, dump_yaml(spec_data))

    config_local_patch = resp.get("config_local")
    if action in {"config_only", "both"} and config_local_patch is not None:
        if not isinstance(config_local_patch, dict):
            fatal("ai_critic_response.config_local 必须是 mapping")
        return spec_data, config_local_patch, action

    return spec_data, None, action


def _apply_exploration(
    cfg: Dict[str, Any],
    round_idx: int,
    exploration: Dict[str, Any],
    *,
    cand_idx: int = 0,
) -> Dict[str, Any]:
    if not bool(exploration.get("enabled", False)):
        return deepcopy(cfg)

    seed = int(exploration.get("seed", 1337))
    # Make branching reproducible: (round, candidate) -> deterministic jitter.
    rng = random.Random(seed + round_idx * 100 + int(cand_idx))
    out = deepcopy(cfg)

    auto = out.get("layout", {}).get("auto", {})
    jitter_px = exploration.get("jitter_px", {})
    if not isinstance(jitter_px, dict):
        jitter_px = {}

    # Reasonable lower bounds to avoid degenerate layouts.
    mins = {
        "margin_x": 40,
        "margin_y": 40,
        "node_gap_x": 10,
        "node_gap_y": 10,
        "group_gap_x": 40,
        "group_gap_y": 40,
    }

    for k, delta in jitter_px.items():
        if k not in auto:
            continue
        try:
            d = int(delta)
        except Exception:
            continue
        base = int(auto.get(k, 0))
        new_v = base + rng.randint(-d, d)
        auto[k] = max(int(mins.get(k, 0)), new_v)

    opts = exploration.get("max_cols_options")
    if isinstance(opts, list) and opts:
        parsed = []
        for v in opts:
            try:
                vi = int(v)
            except Exception:
                continue
            if vi > 0:
                parsed.append(vi)
        if parsed:
            auto["max_cols"] = rng.choice(parsed)

    return out


def main() -> None:
    p = argparse.ArgumentParser(description="Generate NSFC schematic artifacts from spec or TEX.")
    p.add_argument("--proposal-path", type=Path, default=None)
    p.add_argument("--proposal-file", type=Path, default=None)
    p.add_argument("--spec-file", type=Path, default=None)
    p.add_argument("--output-dir", type=Path, required=False, default=None)
    p.add_argument("--config", type=Path, required=False, default=None)
    p.add_argument("--rounds", type=int, default=None)
    args = p.parse_args()

    root = skill_root()
    config_path = args.config if args.config is not None else (root / "config.yaml")
    if not config_path.exists() or not config_path.is_file():
        fatal(f"config 不存在或不是文件：{config_path}")
    base_config = load_yaml(config_path)

    out_dir = args.output_dir if args.output_dir is not None else Path(base_config["output"]["dirname"])
    if args.output_dir is None:
        info(f"未指定 output_dir，使用默认输出目录：{out_dir}")
    if out_dir.exists() and not out_dir.is_dir():
        fatal(f"output_dir 不是目录：{out_dir}")
    out_dir.mkdir(parents=True, exist_ok=True)

    artifacts = base_config.get("output", {}).get("artifacts", {})
    if not isinstance(artifacts, dict):
        fatal("config.yaml:output.artifacts 必须是 dict")
    for k in ("drawio", "svg", "png", "pdf", "spec", "spec_latest", "report", "config_best", "evaluation_best"):
        v = artifacts.get(k)
        if v is None:
            continue
        if not isinstance(v, str):
            fatal(f"config.yaml:output.artifacts.{k} 必须是字符串（相对路径）")
        if not is_safe_relative_path(v):
            fatal(f"config.yaml:output.artifacts.{k} 必须是安全的相对路径（不得包含 `..` 或绝对/盘符路径）：{v!r}")

    work_dir, intermediate_dir, hide_intermediate = _resolve_output_dirs(out_dir, base_config)

    # Instance-local overrides (safe whitelist).
    config_local_path = intermediate_dir / "config_local.yaml"
    local_cfg = _load_config_local(config_local_path)
    config = _apply_config_local(base_config, local_cfg)
    cfg_round_base = deepcopy(config)

    max_rounds = int(config["evaluation"]["max_rounds"])
    rounds = int(args.rounds) if args.rounds is not None else max_rounds
    rounds = max(1, min(20, rounds))

    _cleanup_work_dir(work_dir, intermediate_dir, artifacts, hide_intermediate)

    stop_strategy_effective = str(config.get("evaluation", {}).get("stop_strategy", "none") or "none")
    ai_mode = stop_strategy_effective == "ai_critic"

    # Keep per-run rounds isolated to avoid mixing historical round_* residues.
    run_base = (intermediate_dir / "runs") if hide_intermediate else intermediate_dir
    ai_run_root: Optional[Path] = None
    if ai_mode:
        ai_root = _ai_root(intermediate_dir)
        active = _read_active_run(ai_root)
        run_dir = (run_base / active) if active else _make_run_dir(run_base)
        run_dir.mkdir(parents=True, exist_ok=True)
        _set_active_run(ai_root, run_dir)
        ai_run_root = _ai_run_root(ai_root, run_dir)
        # ai_critic 闭环：每次运行只渲染一轮，等待宿主 AI 响应后继续。
        rounds = 1
    else:
        run_dir = _make_run_dir(run_base)

    spec_latest = intermediate_dir / _spec_latest_filename(config)
    input_spec_data = _load_input_spec(args, config=config, request_dir=run_dir)
    if ai_mode and spec_latest.exists():
        try:
            input_spec_data = load_yaml(spec_latest)
            info("ai_critic 模式：检测到 spec_latest.yaml，继续沿用上一轮最新 spec。")
        except Exception as exc:
            warn(f"spec_latest 读取失败，改用输入 spec：{exc}")

    write_text(spec_latest, dump_yaml(input_spec_data))
    write_text(run_dir / str(artifacts.get("spec", "spec.yaml")), dump_yaml(input_spec_data))

    ai_action: Optional[str] = None
    if ai_mode and ai_run_root is not None:
        input_spec_data, config_local_patch, ai_action = _maybe_apply_ai_response(
            ai_run_root,
            input_spec_data,
            spec_latest,
            base_config=config,
        )
        if config_local_patch is not None:
            base_local = local_cfg if isinstance(local_cfg, dict) else {}
            merged_local = _deep_merge_dict(base_local, config_local_patch)
            write_text(config_local_path, dump_yaml(merged_local))
            local_cfg = _load_config_local(config_local_path)
            config = _apply_config_local(base_config, local_cfg)
            cfg_round_base = deepcopy(config)

    report_path = run_dir / _report_filename(config)
    drawio_cmd = ensure_drawio_cli(config)
    drawio_mode = "drawio_cli" if drawio_cmd else "internal_fallback"

    report_lines: List[str] = [
        "# 原理图优化记录",
        "",
        f"- run_dir: {run_dir.name}",
        f"- work_dir: {work_dir}",
        f"- rounds: {rounds}",
        f"- spec_latest: {spec_latest}",
        f"- renderer_mode: {drawio_mode}",
        "",
    ]

    if drawio_cmd:
        report_lines.extend([f"- drawio_cli: {drawio_cmd}", ""])
    else:
        report_lines.extend(
            [
                "## 重要提示：未检测到 draw.io CLI",
                "",
                "当前将退回到内部渲染兜底：可用于迭代与预览，但最终交付质量通常不如 draw.io CLI 导出。",
                "建议安装 draw.io CLI（macOS/Windows/Linux 指引）：",
                "",
            ]
        )
        report_lines.extend([f"- {line}" for line in drawio_install_hints()])
        report_lines.append("")

    if ai_mode and ai_action == "stop":
        report_lines.extend(
            [
                "## AI Critic",
                "",
                "- action: stop（已收到宿主 AI 停止指令，本次仅导出历史最佳轮次）",
                "",
            ]
        )

    best_round = 0
    best_score = -1
    best_round_dir: Optional[Path] = None
    existing_round_dirs: List[Path] = []

    if ai_mode:
        existing_round_dirs = sorted(
            [p for p in run_dir.iterdir() if p.is_dir() and p.name.startswith("round_")],
            key=lambda p: p.name,
        )
        for rd in existing_round_dirs:
            ev = _load_json_if_exists(rd / "evaluation.json")
            if not isinstance(ev, dict):
                continue
            score = int(ev.get("score", 0) or 0)
            if score > best_score:
                best_score = score
                try:
                    best_round = int(rd.name.split("_")[-1])
                except Exception:
                    best_round = 0
                best_round_dir = rd

    start_round_idx = (len(existing_round_dirs) + 1) if ai_mode else 1

    early = config["evaluation"].get("early_stop", {})
    early_enabled = bool(early.get("enabled", False))
    min_rounds = int(early.get("min_rounds", 2))
    score_threshold = int(early.get("score_threshold", 85))
    allow_p1 = int(early.get("allow_p1", 1))
    pass_streak_need = int(early.get("consecutive_pass", 2))
    pass_streak = 0

    stop_strategy = str(config.get("evaluation", {}).get("stop_strategy", "none"))
    plateau = config.get("evaluation", {}).get("plateau", {})
    min_explore_rounds = int(plateau.get("min_explore_rounds", 4))
    same_image_rounds = int(plateau.get("same_image_rounds", 2))
    no_improve_rounds = int(plateau.get("no_improve_rounds", 3))
    min_delta = float(plateau.get("min_delta", 1))

    exploration = config.get("evaluation", {}).get("exploration", {})

    score_hist: List[int] = []
    hash_hist: List[Optional[str]] = []
    stop_reason: Optional[str] = None

    # Multi-dimensional critiques (evidence-first; optional via config).
    multi_cfg = config.get("evaluation", {}).get("multi_round_self_check", {})
    if not isinstance(multi_cfg, dict):
        multi_cfg = {}
    multi_enabled = bool(multi_cfg.get("enabled", False))
    critique_dims = multi_cfg.get("critique_dimensions", ["structure", "visual", "readability"])
    if not isinstance(critique_dims, list) or not critique_dims:
        critique_dims = ["structure", "visual", "readability"]
    critique_dims = [str(x).strip() for x in critique_dims if str(x).strip()]
    penalty_cfg = multi_cfg.get("penalty", {})
    if not isinstance(penalty_cfg, dict):
        penalty_cfg = {}

    palette: Optional[Dict[str, Any]] = None
    if multi_enabled and ("visual" in critique_dims):
        try:
            palette = load_palette_from_assets(config, skill_root_dir=root)
        except Exception as exc:
            warn(f"配色方案加载失败，已禁用 visual critique（{exc}）")
            palette = None

    if ai_action == "stop":
        rounds = 0

    for r in range(start_round_idx, start_round_idx + rounds):
        round_dir = run_dir / f"round_{r:02d}"
        round_dir.mkdir(parents=True, exist_ok=True)

        # Limited candidate branching: try N small config variations per round and pick the best.
        exploration_cfg = exploration if isinstance(exploration, dict) else {}
        if not bool(exploration_cfg.get("enabled", False)):
            cand_n = 1
        else:
            cand_n = int(exploration_cfg.get("candidates_per_round", 1) or 1)
            cand_n = max(1, min(5, cand_n))

        cand_root = round_dir / "_candidates"
        cand_root.mkdir(parents=True, exist_ok=True)

        cand_results: List[Dict[str, Any]] = []
        for ci in range(cand_n):
            cand_dir = cand_root / f"cand_{ci + 1:02d}"
            cand_dir.mkdir(parents=True, exist_ok=True)

            cfg_used = _apply_exploration(cfg_round_base, r, exploration_cfg, cand_idx=ci)
            spec = load_schematic_spec(input_spec_data, cfg_used)
            cfg_used = deepcopy(cfg_used)
            cfg_used.setdefault("renderer", {}).setdefault("canvas", {})
            cfg_used["renderer"]["canvas"]["width_px"] = int(spec.canvas_width)
            cfg_used["renderer"]["canvas"]["height_px"] = int(spec.canvas_height)

            cand_spec = cand_dir / str(artifacts.get("spec", "spec.yaml"))
            cand_cfg = cand_dir / "config_used.yaml"
            write_text(cand_spec, dump_yaml(spec.to_dict()))
            write_text(cand_cfg, dump_yaml(cfg_used))

            drawio_path = cand_dir / str(artifacts.get("drawio", "schematic.drawio"))
            try:
                write_schematic_drawio(spec, cfg_used, drawio_path)
                _validate_drawio_xml(drawio_path)
            except Exception as exc:
                warn(f"Round {r} cand {ci + 1} preflight 失败：{exc}")
                # Record as a failed candidate (but don't abort the whole run).
                ev = {
                    "score": 0,
                    "counts": {"p0": 1, "p1": 0, "p2": 0},
                    "defects": [],
                    "preflight_error": str(exc),
                }
                (cand_dir / "evaluation.json").write_text(json.dumps(ev, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
                cand_results.append({"idx": ci, "dir": cand_dir, "spec": spec, "cfg_used": cfg_used, "evaluation": ev})
                continue

            try:
                rendered = render_artifacts(spec, cfg_used, drawio_path, cand_dir)
                png_path = rendered.get("png")
            except Exception as exc:
                warn(f"Round {r} cand {ci + 1} 渲染失败：{exc}")
                png_path = None

            # evaluation_mode:
            # - heuristic (default): deterministic evaluator
            # - ai: emit offline protocol files (request/response); consume AI response if provided, else fallback
            evaluation_mode = str((cfg_used.get("evaluation", {}) or {}).get("evaluation_mode", "heuristic")).strip().lower()
            protocol_dir = cand_dir if evaluation_mode == "ai" else None
            evaluation = evaluate_schematic(
                spec,
                cfg_used,
                png_path=png_path if isinstance(png_path, Path) else None,
                protocol_dir=protocol_dir,
            )

            try:
                measurements = measure_schematic(spec, cfg_used, png_path=png_path if isinstance(png_path, Path) else None)
                (cand_dir / "measurements.json").write_text(
                    json.dumps(measurements, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8",
                )
            except Exception as exc:
                warn(f"Round {r} cand {ci + 1} measurements 生成失败（已忽略）：{exc}")

            # Multi-dimensional critiques (optional) -> penalty -> score_total.
            critiques: Dict[str, Dict[str, Any]] = {}
            critique_files: Dict[str, str] = {}
            if multi_enabled:
                try:
                    ai_used = str(evaluation.get("evaluation_source", "")).strip().lower() == "ai"
                    if ai_used:
                        # AI 主评估已覆盖多维度判定；避免二次扣分导致口径混乱。
                        critiques = {}
                        critique_files = {}
                    if ("structure" in critique_dims) and ("structure" not in critiques) and (not ai_used):
                        payload = evaluate_structure(spec, cfg_used)
                        critiques["structure"] = payload
                        critique_files["structure"] = "critique_structure.json"
                        (cand_dir / "critique_structure.json").write_text(
                            json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
                        )
                    if ("visual" in critique_dims) and ("visual" not in critiques) and palette is not None and (not ai_used):
                        payload = evaluate_visual(spec, cfg_used, palette=palette)
                        critiques["visual"] = payload
                        critique_files["visual"] = "critique_visual.json"
                        (cand_dir / "critique_visual.json").write_text(
                            json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
                        )
                    if ("readability" in critique_dims) and ("readability" not in critiques) and (not ai_used):
                        payload = evaluate_readability(
                            spec, cfg_used, png_path=png_path if isinstance(png_path, Path) else None
                        )
                        critiques["readability"] = payload
                        critique_files["readability"] = "critique_readability.json"
                        (cand_dir / "critique_readability.json").write_text(
                            json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
                        )
                except Exception as exc:
                    warn(f"Round {r} cand {ci + 1} critique 失败（已忽略）：{exc}")

            if critiques:
                try:
                    (cand_dir / "dimension_measurements.json").write_text(
                        json.dumps({"dimensions": critiques}, ensure_ascii=False, indent=2) + "\n",
                        encoding="utf-8",
                    )
                except Exception:
                    pass

            base_score = int(evaluation.get("score", 0))
            penalty, penalty_summary = (0, {})
            if critiques:
                penalty, penalty_summary = penalty_from_critiques(critiques, penalty_cfg=penalty_cfg)
            total_score = max(0, int(base_score) - int(penalty))

            evaluation = deepcopy(evaluation)
            evaluation["score_base"] = base_score
            evaluation["score_penalty"] = penalty
            evaluation["score_total"] = total_score
            evaluation["score"] = total_score
            evaluation["critique_files"] = critique_files
            evaluation["critique_summary"] = penalty_summary

            (cand_dir / "evaluation.json").write_text(
                json.dumps(evaluation, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
            )
            cand_results.append(
                {
                    "idx": ci,
                    "dir": cand_dir,
                    "spec": spec,
                    "cfg_used": cfg_used,
                    "png_path": png_path if isinstance(png_path, Path) else None,
                    "evaluation": evaluation,
                }
            )

        def _cand_key(item: Dict[str, Any]) -> Tuple[int, int, int, int]:
            ev = item.get("evaluation", {}) if isinstance(item.get("evaluation", {}), dict) else {}
            score = int(ev.get("score", 0) or 0)
            c = ev.get("counts", {}) if isinstance(ev.get("counts", {}), dict) else {}
            p0 = int(c.get("p0", 0) or 0)
            p1 = int(c.get("p1", 0) or 0)
            p2 = int(c.get("p2", 0) or 0)
            return (score, -p0, -p1, -p2)

        best_cand = max(cand_results, key=_cand_key)
        cand_dir = best_cand["dir"]
        spec = best_cand["spec"]
        cfg_used = best_cand["cfg_used"]
        evaluation = best_cand["evaluation"]

        # Promote best candidate artifacts into round_dir root for stable downstream exports.
        for name in (
            str(artifacts.get("spec", "spec.yaml")),
            "config_used.yaml",
            "evaluation.json",
            str(artifacts.get("drawio", "schematic.drawio")),
            str(artifacts.get("svg", "schematic.svg")),
            str(artifacts.get("png", "schematic.png")),
            str(artifacts.get("pdf", "schematic.pdf")),
            "layout_debug.json",
            "edge_debug.json",
            "measurements.json",
            "dimension_measurements.json",
            "critique_structure.json",
            "critique_visual.json",
            "critique_readability.json",
        ):
            _copy_if_exists(cand_dir / name, round_dir / name)

        promoted_png = round_dir / str(artifacts.get("png", "schematic.png"))
        png_path = promoted_png if promoted_png.exists() else None

        score = int(evaluation.get("score", 0))
        counts = evaluation.get("counts", {}) if isinstance(evaluation.get("counts", {}), dict) else {}
        p0 = int(counts.get("p0", 0))
        p1 = int(counts.get("p1", 0))

        if score > best_score:
            best_score = score
            best_round = r
            best_round_dir = round_dir

        png_hash = _sha256_file(png_path) if isinstance(png_path, Path) else None
        score_hist.append(score)
        hash_hist.append(png_hash)

        if p0 == 0 and p1 <= allow_p1 and score >= score_threshold:
            pass_streak += 1
        else:
            pass_streak = 0

        base_score = int(evaluation.get("score_base", score) or score)
        penalty = int(evaluation.get("score_penalty", 0) or 0)
        top = _top_defects(evaluation.get("defects", []), limit=6)
        report_lines.extend([f"## Round {r}", ""])
        if multi_enabled:
            report_lines.append(f"- score_total: {score} (base={base_score}, penalty={penalty})")
        else:
            report_lines.append(f"- score: {score}")
        report_lines.extend(
            [
                f"- defects: P0={p0} P1={p1} P2={counts.get('p2', 0)}",
                f"- png_sha256: {png_hash or 'N/A'}",
                f"- selected_candidate: `{cand_dir.relative_to(round_dir)}`",
                f"- output: `{round_dir.name}/`",
                "",
            ]
        )
        if top:
            report_lines.append("Top defects:")
            for d in top:
                report_lines.append(f"- [{d['severity']}] [{d['dimension']}] {d['message']} ({d['where']})")
            report_lines.append("")

        if ai_mode and ai_run_root is not None:
            pack = _write_ai_pack(
                ai_run_root,
                round_idx=r,
                round_dir=round_dir,
                spec_dict=spec.to_dict(),
                cfg_used=cfg_used,
                evaluation=evaluation,
                png_path=png_path if isinstance(png_path, Path) else None,
            )
            _write_ai_critic_request(
                ai_run_root,
                round_idx=r,
                pack_dir=pack,
                response_path=_ai_response_path(ai_run_root),
            )
            report_lines.extend(
                [
                    "## Stop (ai_critic)",
                    "",
                    f"- reason: waiting for `{_ai_response_path(ai_run_root).as_posix()}`",
                    f"- request: `{_ai_request_path(ai_run_root).as_posix()}`",
                    "",
                ]
            )
            break

        cfg_round_base = _apply_auto_fixes(cfg_round_base, evaluation)

        if early_enabled and r >= min_rounds and pass_streak >= pass_streak_need:
            report_lines.extend(
                [
                    "## Early Stop",
                    "",
                    (
                        f"- reason: 连续 {pass_streak} 轮满足 "
                        f"P0=0 且 P1<={allow_p1} 且 score>={score_threshold}"
                    ),
                    "",
                ]
            )
            break

        if early_enabled:
            continue

        # New stop strategy (default: plateau; no fixed score thresholds).
        if stop_strategy == "none":
            continue

        if stop_strategy != "plateau":
            # Unknown value: behave like "none" to avoid surprise.
            continue

        if r < min_explore_rounds:
            continue

        same_image_hit = False
        if same_image_rounds >= 2:
            recent = hash_hist[-same_image_rounds:]
            if recent and recent[-1] is not None and len(set(recent)) == 1:
                same_image_hit = True

        no_improve_hit = False
        if no_improve_rounds >= 2 and len(score_hist) >= (no_improve_rounds + 1):
            recent_scores = score_hist[-(no_improve_rounds + 1):]
            if (max(recent_scores) - min(recent_scores)) < float(min_delta):
                no_improve_hit = True

        if same_image_hit or no_improve_hit:
            parts = []
            if same_image_hit:
                parts.append(f"连续 {same_image_rounds} 轮 PNG 哈希不变")
            if no_improve_hit:
                parts.append(f"连续 {no_improve_rounds} 轮分数提升 < {min_delta}")
            stop_reason = "；".join(parts) if parts else "plateau"

            report_lines.extend(
                [
                    "## Stop (plateau)",
                    "",
                    f"- strategy: {stop_strategy}",
                    f"- reason: {stop_reason}",
                    "",
                ]
            )
            break

    write_text(report_path, "\n".join(report_lines) + "\n")

    if best_round_dir is None:
        warn("没有可导出的 best round")
        # Still surface the latest report/meta for debugging.
        _copy_if_exists(report_path, intermediate_dir / _report_filename(config))
        if ai_mode and ai_action == "stop":
            _clear_active_run(_ai_root(intermediate_dir))
        info(f"完成（无导出）：{run_dir}")
        return

    for key in ("drawio", "svg", "png", "pdf"):
        name = artifacts.get(key)
        if isinstance(name, str):
            _copy_if_exists(best_round_dir / name, run_dir / name)
            _copy_if_exists(best_round_dir / name, work_dir / name)

    config_best_name = str(artifacts.get("config_best", "config_used_best.yaml"))
    evaluation_best_name = str(artifacts.get("evaluation_best", "evaluation_best.json"))
    _copy_if_exists(best_round_dir / "config_used.yaml", run_dir / config_best_name)
    _copy_if_exists(best_round_dir / "evaluation.json", run_dir / evaluation_best_name)
    _copy_if_exists(best_round_dir / "config_used.yaml", intermediate_dir / config_best_name)
    _copy_if_exists(best_round_dir / "evaluation.json", intermediate_dir / evaluation_best_name)

    with report_path.open("a", encoding="utf-8") as f:
        f.write("\n## Final\n\n")
        f.write(f"- best_round: {best_round} (score {best_score})\n")
        drawio_name = str(artifacts.get("drawio", "schematic.drawio"))
        svg_name = str(artifacts.get("svg", "schematic.svg"))
        png_name = str(artifacts.get("png", "schematic.png"))
        f.write(
            "- exported: "
            f"`{drawio_name}`, `{svg_name}`, `{png_name}`"
            "\n"
        )
        f.write(
            "- exported_meta: "
            f"`{config_best_name}`, `{evaluation_best_name}`"
            "\n"
        )

    # Convenience: keep the latest report at intermediate_dir root.
    _copy_if_exists(report_path, intermediate_dir / _report_filename(config))

    if ai_mode and ai_action == "stop":
        _clear_active_run(_ai_root(intermediate_dir))

    if hide_intermediate:
        max_runs = int(config.get("output", {}).get("max_history_runs", 10) or 0)
        _prune_history_runs(intermediate_dir, max_runs=max_runs)

    info(f"完成：{run_dir}（交付文件位于 {work_dir}；中间产物位于 {intermediate_dir}）")


if __name__ == "__main__":
    main()
