from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import datetime
import hashlib
import json
from pathlib import Path
from pathlib import PureWindowsPath
import random
import re
import shutil
from typing import Any, Dict, List, Optional
import xml.etree.ElementTree as ET

from evaluate_roadmap import evaluate
from evaluate_dimension import run_critiques
from measure_dimension import measure_all as measure_dimensions
from measure_roadmap import measure as measure_roadmap
from extract_from_tex import extract_item_titles, extract_research_content_section, find_candidate_tex
from render_roadmap import drawio_install_hints, ensure_drawio_cli, render
from spec import default_spec_for_nsfc_young_2026
from template_library import load_template_db, resolve_layout_template
from utils import dump_yaml, fatal, info, load_yaml, skill_root, warn, write_text


def _make_run_dir(out_dir: Path) -> Path:
    ts = datetime.now().strftime("%Y%m%d%H%M%S")
    base = out_dir / f"run_{ts}"
    if not base.exists():
        base.mkdir(parents=True, exist_ok=False)
        return base

    # Very unlikely, but keep it deterministic and safe.
    for i in range(1, 1000):
        p = out_dir / f"run_{ts}_{i:02d}"
        if not p.exists():
            p.mkdir(parents=True, exist_ok=False)
            return p
    fatal(f"无法创建 run 目录（疑似同秒并发/残留冲突）：{out_dir}")


def _is_safe_relative_path(p: str) -> bool:
    """
    Ensure a config-controlled path is:
    - relative (no absolute / drive / UNC)
    - does not contain '..'
    """
    s = str(p).strip()
    if not s:
        return False
    if Path(s).is_absolute():
        return False
    win = PureWindowsPath(s)
    if win.is_absolute() or win.drive:
        return False
    if s.startswith("\\\\"):
        return False
    parts = [part for part in Path(s).parts if part not in {"", "."}]
    return all(part != ".." for part in parts)


def _ensure_intermediate_gitignore(intermediate_dir: Path) -> None:
    """
    Create a conservative .gitignore for intermediate dir.
    Don't overwrite if user already has one.
    """
    p = intermediate_dir / ".gitignore"
    if p.exists():
        return
    dirname = intermediate_dir.name or ".nsfc-roadmap"
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


def _resolve_output_dirs(out_dir: Path, config: Dict[str, Any]) -> tuple[Path, Path, bool]:
    """
    Resolve output dirs.

    Returns:
        (work_dir, intermediate_dir, hide_intermediate)
    """
    output_cfg = config.get("output", {}) if isinstance(config.get("output", {}), dict) else {}
    hide = bool(output_cfg.get("hide_intermediate", True))
    intermediate_name = str(output_cfg.get("intermediate_dir", ".nsfc-roadmap")).strip() or ".nsfc-roadmap"
    if not _is_safe_relative_path(intermediate_name):
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


def _safe_move_to_dir(src: Path, dst_dir: Path) -> Optional[Path]:
    if not src.exists():
        return None
    dst_dir.mkdir(parents=True, exist_ok=True)
    dst = dst_dir / src.name
    if not dst.exists():
        shutil.move(str(src), str(dst))
        return dst
    stem = src.stem
    suffix = src.suffix
    for i in range(1, 1000):
        cand = dst_dir / f"{stem}_{i:02d}{suffix}"
        if not cand.exists():
            shutil.move(str(src), str(cand))
            return cand
    fatal(f"无法移动到 legacy（目标冲突过多）：{src}")
    return None


def _cleanup_work_dir(
    work_dir: Path,
    intermediate_dir: Path,
    artifacts: Dict[str, Any],
    hide: bool,
    plan_filename: str,
) -> None:
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
        plan_filename,
        str(artifacts.get("drawio", "roadmap.drawio")),
        str(artifacts.get("svg", "roadmap.svg")),
        str(artifacts.get("png", "roadmap.png")),
        str(artifacts.get("pdf", "roadmap.pdf")),
    }
    known_intermediate = {
        "optimization_report.md",
        "spec.yaml",
        "spec_latest.yaml",
        "spec_draft.yaml",
        "config_used_best.yaml",
        "evaluation_best.json",
        "config_used_*.yaml",
        "evaluation_*.json",
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
            if p.name in known_intermediate or p.name.startswith("spec_") or p.name.startswith("evaluation_") or p.name.startswith("config_used_"):
                _safe_move_to_dir(p, legacy_files)
                continue


def _prune_history_runs(intermediate_dir: Path, max_runs: int) -> None:
    if max_runs <= 0:
        return
    runs_dir = intermediate_dir / "runs"
    if not runs_dir.exists() or not runs_dir.is_dir():
        return

    runs = [p for p in runs_dir.iterdir() if p.is_dir() and p.name.startswith("run_")]
    runs.sort(key=lambda p: p.name)
    if len(runs) <= max_runs:
        return
    for p in runs[: len(runs) - max_runs]:
        shutil.rmtree(p, ignore_errors=True)


def _report_filename(config: Dict[str, Any]) -> str:
    output_cfg = config.get("output", {}) if isinstance(config.get("output", {}), dict) else {}
    artifacts = output_cfg.get("artifacts", {}) if isinstance(output_cfg.get("artifacts", {}), dict) else {}
    v = artifacts.get("report") or output_cfg.get("report_filename") or "optimization_report.md"
    return str(v)


def _spec_latest_filename(config: Dict[str, Any]) -> str:
    output_cfg = config.get("output", {}) if isinstance(config.get("output", {}), dict) else {}
    artifacts = output_cfg.get("artifacts", {}) if isinstance(output_cfg.get("artifacts", {}), dict) else {}
    return str(artifacts.get("spec_latest") or "spec_latest.yaml")


def _plan_filename(config: Dict[str, Any]) -> str:
    planning_cfg = config.get("planning", {}) if isinstance(config.get("planning", {}), dict) else {}
    output_cfg = planning_cfg.get("output", {}) if isinstance(planning_cfg.get("output", {}), dict) else {}
    return str(output_cfg.get("plan_filename") or "roadmap-plan.md")


def _ensure_plan_file(work_dir: Path, plan_filename: str, spec_data: Dict[str, Any], spec_latest_path: Path) -> None:
    """
    Ensure deliverable roadmap-plan.md exists.

    If the user already wrote one, don't overwrite it.
    """
    p = work_dir / plan_filename
    if p.exists():
        return
    phases = spec_data.get("phases", [])
    phase_labels: List[str] = []
    if isinstance(phases, list):
        for ph in phases:
            if isinstance(ph, dict) and isinstance(ph.get("label"), str):
                phase_labels.append(ph["label"].strip())

    lines: List[str] = []
    lines.append("# roadmap-plan（自动生成草案）")
    lines.append("")
    lines.append("此文件用于“先规划、后落图”的工作流：你可以先审阅/修改本计划，再运行生成脚本。")
    lines.append("")
    lines.append("## 版式约束（默认）")
    lines.append("")
    lines.append("- A4 宽度不变，高度约 2/3 A4（具体像素见 config.yaml:renderer.canvas）")
    lines.append("- 标题/备注默认不落图（如需落图，请启用 config.yaml:layout.title.enabled / layout.notes.enabled）")
    lines.append("")
    lines.append("## 阶段（phases）")
    lines.append("")
    if phase_labels:
        for i, lab in enumerate(phase_labels, start=1):
            lines.append(f"- Phase {i}: {lab}")
    else:
        lines.append("- （未解析到 phases；请检查 spec_draft/spec_latest）")
    lines.append("")
    lines.append("## 不落图但需要强调的内容（建议写在这里）")
    lines.append("")
    lines.append("- 评估指标口径/缩印可读性要求/风险与替代方案等")
    lines.append("")
    lines.append("## 可复现输入")
    lines.append("")
    lines.append(f"- spec_latest（隐藏目录）：`{spec_latest_path.as_posix()}`")
    lines.append("")
    write_text(p, "\n".join(lines) + "\n")


def _validate_drawio_xml(drawio_path: Path) -> None:
    try:
        ET.parse(drawio_path)
    except ET.ParseError as exc:
        line, col = getattr(exc, "position", (None, None))
        pos = f"（line={line}, col={col}）" if line is not None and col is not None else ""
        raise ValueError(
            "生成的 .drawio 不是合法 XML，已阻断后续渲染/评估。"
            f"{pos}\n"
            f"- file: {drawio_path}\n"
            "- 常见原因：节点文本包含未转义的 `<`/`>`/`&` 等字符，或直接写入了 `<br>` 但未做 XML escape。\n"
            "- 建议：检查 drawio_writer 的 XML 转义逻辑，或在 label 中用 `\\n` 并确保写入 XML 时已正确转义。"
        ) from exc


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


def _deep_merge_dict(base: Dict[str, Any], patch: Dict[str, Any]) -> Dict[str, Any]:
    """
    Deep-merge patch into base (dict-only). Lists/scalars are replaced.
    Returns a new dict; does not mutate inputs.
    """
    out: Dict[str, Any] = deepcopy(base)
    for k, v in (patch or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge_dict(out[k], v)  # type: ignore[arg-type]
        else:
            out[k] = deepcopy(v)
    return out


def _is_hex_color(s: str) -> bool:
    ss = str(s or "").strip()
    if not ss:
        return False
    if ss.startswith("#"):
        ss = ss[1:]
    return bool(re.fullmatch(r"[0-9a-fA-F]{6}", ss))


def _load_config_local(config_local_path: Path) -> Optional[Dict[str, Any]]:
    if not config_local_path.exists():
        return None
    if not config_local_path.is_file():
        fatal(f"config_local 不是文件：{config_local_path}")
    return load_yaml(config_local_path)


def _sanitize_config_local(local_cfg: Dict[str, Any]) -> Dict[str, Any]:
    """
    Only allow a conservative whitelist of overrides for instance-local tuning.
    This prevents surprising behavior and blocks path/IO related knobs.
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

    def as_bool(v: Any, where: str) -> bool:
        if not isinstance(v, bool):
            fatal(f"config_local.{where} 必须是布尔值 true/false")
        return bool(v)

    def as_str(v: Any, where: str) -> str:
        if not isinstance(v, str) or not v.strip():
            fatal(f"config_local.{where} 必须是非空字符串")
        return v.strip()

    def as_opt_str(v: Any, where: str) -> Optional[str]:
        if v is None:
            return None
        return as_str(v, where)

    def as_hex(v: Any, where: str) -> str:
        s = as_str(v, where)
        if not _is_hex_color(s):
            fatal(f"config_local.{where} 必须是 6 位 hex 颜色（如 #2F5597）：{s!r}")
        return s

    out: Dict[str, Any] = {}
    disallowed: List[str] = []

    def reject(path: str) -> None:
        disallowed.append(path)

    for k in local_cfg.keys():
        if k not in {"renderer", "layout", "color_scheme", "evaluation"}:
            reject(k)

    if disallowed:
        fatal(
            "config_local.yaml 包含未允许的顶层字段（为安全起见已拒绝）："
            + ", ".join(disallowed[:20])
            + (" ..." if len(disallowed) > 20 else "")
        )

    renderer = local_cfg.get("renderer")
    if isinstance(renderer, dict):
        r_out: Dict[str, Any] = {}
        canvas = renderer.get("canvas")
        if isinstance(canvas, dict):
            c_out: Dict[str, Any] = {}
            if "width_px" in canvas:
                c_out["width_px"] = as_int(canvas.get("width_px"), "renderer.canvas.width_px", 1200, 12000)
            if "height_px" in canvas:
                c_out["height_px"] = as_int(canvas.get("height_px"), "renderer.canvas.height_px", 900, 20000)
            if "margin_px" in canvas:
                c_out["margin_px"] = as_int(canvas.get("margin_px"), "renderer.canvas.margin_px", 0, 600)
            if c_out:
                r_out["canvas"] = c_out

        fonts = renderer.get("fonts")
        if isinstance(fonts, dict):
            f_out: Dict[str, Any] = {}
            if "default_size" in fonts:
                f_out["default_size"] = as_int(fonts.get("default_size"), "renderer.fonts.default_size", 10, 120)
            if "title_size" in fonts:
                f_out["title_size"] = as_int(fonts.get("title_size"), "renderer.fonts.title_size", 10, 160)
            if "min_size" in fonts:
                f_out["min_size"] = as_int(fonts.get("min_size"), "renderer.fonts.min_size", 8, 120)
            if f_out:
                r_out["fonts"] = f_out

        stroke = renderer.get("stroke")
        if isinstance(stroke, dict):
            s_out: Dict[str, Any] = {}
            if "width_px" in stroke:
                s_out["width_px"] = as_int(stroke.get("width_px"), "renderer.stroke.width_px", 1, 20)
            if "color" in stroke:
                s_out["color"] = as_hex(stroke.get("color"), "renderer.stroke.color")
            if s_out:
                r_out["stroke"] = s_out

        if "background" in renderer:
            r_out["background"] = as_hex(renderer.get("background"), "renderer.background")

        out["renderer"] = r_out if r_out else out.get("renderer", {})

    layout = local_cfg.get("layout")
    if isinstance(layout, dict):
        l_out: Dict[str, Any] = {}
        if "template" in layout:
            t = as_str(layout.get("template"), "layout.template")
            if t not in {"auto", "classic", "three-column", "layered-pipeline"}:
                fatal("config_local.layout.template 不合法（允许 auto|classic|three-column|layered-pipeline）")
            l_out["template"] = t
        if "template_ref" in layout:
            l_out["template_ref"] = as_opt_str(layout.get("template_ref"), "layout.template_ref")
        if "direction" in layout:
            l_out["direction"] = as_str(layout.get("direction"), "layout.direction")
        if "spacing_px" in layout:
            l_out["spacing_px"] = as_int(layout.get("spacing_px"), "layout.spacing_px", 8, 120)
        pb = layout.get("phase_bar")
        if isinstance(pb, dict):
            pb_out: Dict[str, Any] = {}
            if "width_px" in pb:
                pb_out["width_px"] = as_int(pb.get("width_px"), "layout.phase_bar.width_px", 20, 240)
            if "fill" in pb:
                pb_out["fill"] = as_hex(pb.get("fill"), "layout.phase_bar.fill")
            if "text_color" in pb:
                pb_out["text_color"] = as_hex(pb.get("text_color"), "layout.phase_bar.text_color")
            if pb_out:
                l_out["phase_bar"] = pb_out
        box = layout.get("box")
        if isinstance(box, dict):
            b_out: Dict[str, Any] = {}
            if "radius_px" in box:
                b_out["radius_px"] = as_int(box.get("radius_px"), "layout.box.radius_px", 0, 60)
            if "padding_px" in box:
                b_out["padding_px"] = as_int(box.get("padding_px"), "layout.box.padding_px", 0, 80)
            if "min_height_px" in box:
                b_out["min_height_px"] = as_int(box.get("min_height_px"), "layout.box.min_height_px", 40, 400)
            if b_out:
                l_out["box"] = b_out
        title = layout.get("title")
        if isinstance(title, dict) and "enabled" in title:
            l_out["title"] = {"enabled": as_bool(title.get("enabled"), "layout.title.enabled")}
        notes = layout.get("notes")
        if isinstance(notes, dict) and "enabled" in notes:
            l_out["notes"] = {"enabled": as_bool(notes.get("enabled"), "layout.notes.enabled")}
        if l_out:
            out["layout"] = l_out

    cs = local_cfg.get("color_scheme")
    if isinstance(cs, dict) and "name" in cs:
        out["color_scheme"] = {"name": as_str(cs.get("name"), "color_scheme.name")}

    ev = local_cfg.get("evaluation")
    if isinstance(ev, dict) and "stop_strategy" in ev:
        s = as_str(ev.get("stop_strategy"), "evaluation.stop_strategy")
        if s not in {"none", "plateau", "ai_critic"}:
            fatal("config_local.evaluation.stop_strategy 不合法（允许 none|plateau|ai_critic）")
        out["evaluation"] = {"stop_strategy": s}

    return out


def _apply_config_local(base_cfg: Dict[str, Any], local_cfg: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not local_cfg:
        return deepcopy(base_cfg)
    sanitized = _sanitize_config_local(local_cfg)
    merged = _deep_merge_dict(base_cfg, sanitized)

    # Post-merge invariants (clamp with warnings instead of silently breaking rendering).
    try:
        presets = (merged.get("color_scheme", {}) or {}).get("presets", {})
        name = (merged.get("color_scheme", {}) or {}).get("name")
        if isinstance(presets, dict) and isinstance(name, str) and name and name not in presets:
            fatal(f"color_scheme.name 不存在于 presets：{name!r}")
    except Exception:
        pass

    fonts = (merged.get("renderer", {}) or {}).get("fonts", {})
    thresholds = (merged.get("evaluation", {}) or {}).get("thresholds", {})
    min_font_px = thresholds.get("min_font_px")
    try:
        min_font_px = int(min_font_px) if min_font_px is not None else None
    except Exception:
        min_font_px = None

    if isinstance(fonts, dict):
        try:
            fmin = int(fonts.get("min_size"))
            fdef = int(fonts.get("default_size"))
            ftitle = int(fonts.get("title_size"))
            if min_font_px is not None and fmin < min_font_px:
                warn(f"renderer.fonts.min_size={fmin} < thresholds.min_font_px={min_font_px}，已提升到阈值下限")
                fmin = int(min_font_px)
            if fdef < fmin:
                warn("renderer.fonts.default_size < min_size，已提升到 min_size")
                fdef = fmin
            if ftitle < fdef:
                warn("renderer.fonts.title_size < default_size，已提升到 default_size+2")
                ftitle = fdef + 2
            fonts["min_size"] = fmin
            fonts["default_size"] = fdef
            fonts["title_size"] = ftitle
        except Exception:
            pass

    return merged


def _strip_latex_to_excerpt(tex: str, max_chars: int = 4000) -> str:
    """
    Best-effort LaTeX -> readable excerpt (deterministic, no external tools).
    """
    # Remove comments
    lines = []
    for line in (tex or "").splitlines():
        if "%" in line:
            line = line.split("%", 1)[0]
        lines.append(line)
    s = "\n".join(lines)
    # Common cleanups
    s = s.replace("\\item", "\n- ")
    s = re.sub(r"\\itemtitlefont\{([^}]*)\}", r"\\1", s)
    s = re.sub(r"\\(sub)*section\*?\{([^}]*)\}", r"\n\\2\n", s)
    s = re.sub(r"\\label\{[^}]*\}", "", s)
    s = re.sub(r"\\ref\{[^}]*\}", "", s)
    s = re.sub(r"\\cite\{[^}]*\}", "", s)
    s = re.sub(r"\\textbf\{([^}]*)\}", r"\\1", s)
    s = re.sub(r"\\emph\{([^}]*)\}", r"\\1", s)
    # Remove simple commands like \\foo or \\foo* or \\foo[opt] (best-effort).
    s = re.sub(r"\\[a-zA-Z]+\*?(?:\[[^\]]*\])?", "", s)
    s = s.replace("{", "").replace("}", "")
    s = re.sub(r"\n{3,}", "\n\n", s).strip()
    if len(s) > max_chars:
        s = s[: max_chars].rstrip() + "\n\n…（已截断）"
    return s


def _ai_root(intermediate_dir: Path) -> Path:
    p = intermediate_dir / "ai"
    p.mkdir(parents=True, exist_ok=True)
    return p


def _ai_active_run_file(ai_root: Path) -> Path:
    return ai_root / "ACTIVE_RUN.txt"


def _read_active_run(ai_root: Path, run_base: Path) -> Optional[Path]:
    p = _ai_active_run_file(ai_root)
    if not p.exists():
        return None
    name = p.read_text(encoding="utf-8").strip().splitlines()[0].strip()
    if not name:
        return None
    if not re.fullmatch(r"run_[0-9]{14}(?:_[0-9]{2})?", name):
        return None
    cand = run_base / name
    if cand.exists() and cand.is_dir():
        return cand
    return None


def _set_active_run(ai_root: Path, run_dir: Path) -> None:
    _ai_active_run_file(ai_root).write_text(run_dir.name + "\n", encoding="utf-8")


def _clear_active_run(ai_root: Path) -> None:
    p = _ai_active_run_file(ai_root)
    try:
        if p.exists():
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


def _write_ai_pack(
    ai_run_root: Path,
    round_idx: int,
    input_excerpt_path: Optional[Path],
    templates_selected_path: Optional[Path],
    round_spec: Path,
    round_cfg: Path,
    out_png: Path,
    round_dir: Path,
) -> Path:
    pack = _ai_pack_dir(ai_run_root, round_idx)
    pack.mkdir(parents=True, exist_ok=True)
    if input_excerpt_path and input_excerpt_path.exists():
        _copy_if_exists(input_excerpt_path, pack / "input_excerpt.md")
    if templates_selected_path and templates_selected_path.exists():
        _copy_if_exists(templates_selected_path, pack / "templates_selected.yaml")
    _copy_if_exists(round_spec, pack / "spec_latest.yaml")
    _copy_if_exists(round_cfg, pack / "config_used.yaml")
    _copy_if_exists(out_png, pack / "roadmap.png")
    _copy_if_exists(round_dir / "evaluation.json", pack / "evaluation.json")
    _copy_if_exists(round_dir / "measurements.json", pack / "measurements.json")
    _copy_if_exists(round_dir / "dimension_measurements.json", pack / "dimension_measurements.json")
    for dim in ("structure", "visual", "readability"):
        _copy_if_exists(round_dir / f"critique_{dim}.json", pack / f"critique_{dim}.json")
    return pack


def _write_ai_critic_request(
    ai_run_root: Path,
    round_idx: int,
    pack_dir: Path,
    response_path: Path,
) -> None:
    lines: List[str] = []
    lines.append("# nsfc-roadmap ai_critic request")
    lines.append("")
    lines.append(f"- based_on_round: {round_idx}")
    lines.append(f"- evidence_pack: `{pack_dir.as_posix()}`")
    lines.append(f"- write_response_to: `{response_path.as_posix()}`")
    lines.append("")
    lines.append("## 任务")
    lines.append("")
    lines.append(
        "请基于 `roadmap.png` 的读图批判 + `evaluation.json/critique_*.json` 的证据，输出“可执行变更”。"
        "此外请参考 `measurements.json`（纯度量，无阈值判定）与 `dimension_measurements.json`（结构/视觉/可读性度量）。"
    )
    lines.append("")
    lines.append("## 输出约束（必须满足）")
    lines.append("")
    lines.append("你的输出必须是一个 YAML 文件（写到上面的 `ai_critic_response.yaml`），格式如下：")
    lines.append("")
    lines.append("```yaml")
    lines.append("version: 1")
    lines.append("based_on_round: 1")
    lines.append("action: both  # spec_only|config_only|both|stop")
    lines.append("reason: \"一句话说明本轮行动与停止/继续依据\"")
    lines.append("# 可选：提供完整 spec（推荐直接给全量，避免 patch 合并歧义）")
    lines.append("# spec:")
    lines.append("#   title: ...")
    lines.append("#   phases: ...")
    lines.append("# 可选：提供 config_local patch（只允许 renderer/layout/color_scheme/evaluation.stop_strategy 的安全子集）")
    lines.append("# config_local:")
    lines.append("#   layout:")
    lines.append("#     template: three-column")
    lines.append("```")
    lines.append("")
    lines.append("### 缺陷分级口径")
    lines.append("")
    lines.append("- P0：主线不成路 / 缺关键闭环 / 不可读（A4 缩印必须可读）")
    lines.append("- P1：结构不清 / 分区不显式 / 对齐混乱 / 配色干扰")
    lines.append("- P2：间距、文案密度、局部微调")
    lines.append("")
    lines.append("### 停止口径（action=stop）")
    lines.append("")
    lines.append("- 停止必须说明：当前图已满足交付自检；P0=0；主线清晰；A4 可读；颜色主色 <=3。")
    lines.append("")
    write_text(_ai_request_path(ai_run_root), "\n".join(lines) + "\n")


def _maybe_apply_ai_response(
    ai_run_root: Path,
    spec_data: Dict[str, Any],
    spec_latest_path: Path,
) -> tuple[Dict[str, Any], Optional[Dict[str, Any]], Optional[str]]:
    """
    Returns: (updated_spec_data, config_local_patch, action)
    """
    resp_path = _ai_response_path(ai_run_root)
    if not resp_path.exists():
        return spec_data, None, None
    resp = load_yaml(resp_path)
    if int(resp.get("version", 1) or 1) != 1:
        fatal(f"ai_critic_response.version 不支持：{resp.get('version')}")
    action = str(resp.get("action", "") or "").strip()
    if action not in {"spec_only", "config_only", "both", "stop"}:
        fatal("ai_critic_response.action 必须是 spec_only|config_only|both|stop")

    # Archive the response first (avoid repeated application on crash/retry).
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
        # Validate spec shape early (will raise with helpful messages).
        from spec import load_spec as _load_spec  # local import to avoid cycles

        _load_spec(new_spec)
        spec_data = new_spec
        write_text(spec_latest_path, dump_yaml(spec_data))

    config_local_patch = resp.get("config_local")
    if action in {"config_only", "both"} and config_local_patch is not None:
        if not isinstance(config_local_patch, dict):
            fatal("ai_critic_response.config_local 必须是 mapping")
        return spec_data, config_local_patch, action

    return spec_data, None, action


def _apply_exploration(cfg: Dict[str, Any], round_idx: int, exploration: Dict[str, Any]) -> Dict[str, Any]:
    """
    Deterministic light exploration to escape local minima.
    This should never make the layout degenerate (bounded jitter + conservative minima).
    """
    if not bool(exploration.get("enabled", False)):
        return deepcopy(cfg)

    seed = int(exploration.get("seed", 1337))
    rng = random.Random(seed + round_idx)
    out = deepcopy(cfg)

    jitter_px = exploration.get("jitter_px", {})
    if not isinstance(jitter_px, dict):
        jitter_px = {}

    # Supported knobs (roadmap has fewer layout degrees of freedom than schematic).
    knobs: List[tuple[tuple[str, ...], int]] = [
        (("renderer", "canvas", "margin_px"), 20),
        (("layout", "spacing_px"), 8),
        (("layout", "phase_bar", "width_px"), 18),
        (("renderer", "canvas", "height_px"), 120),
    ]
    mins: Dict[tuple[str, ...], int] = {
        ("renderer", "canvas", "margin_px"): 30,
        ("layout", "spacing_px"): 12,
        ("layout", "phase_bar", "width_px"): 48,
        ("renderer", "canvas", "height_px"): 900,
    }

    def get_path(d: Dict[str, Any], path: tuple[str, ...]) -> Optional[int]:
        cur: Any = d
        for k in path[:-1]:
            if not isinstance(cur, dict) or k not in cur:
                return None
            cur = cur[k]
        leaf = path[-1]
        if not isinstance(cur, dict) or leaf not in cur:
            return None
        try:
            return int(cur[leaf])
        except Exception:
            return None

    def set_path(d: Dict[str, Any], path: tuple[str, ...], v: int) -> None:
        cur: Any = d
        for k in path[:-1]:
            if not isinstance(cur, dict):
                return
            cur = cur.setdefault(k, {})
        if isinstance(cur, dict):
            cur[path[-1]] = int(v)

    for path, default_delta in knobs:
        delta = jitter_px.get(path[-1], default_delta)
        try:
            d = int(delta)
        except Exception:
            continue
        base = get_path(out, path)
        if base is None:
            continue
        new_v = base + rng.randint(-d, d)
        new_v = max(int(mins.get(path, 0)), new_v)
        set_path(out, path, new_v)

    return out


def _apply_tex_hints(spec: Dict[str, Any], tex_path: Path, effective_layout: Optional[str] = None) -> Dict[str, Any]:
    # 轻量抽取：把研究内容的条目标题用于“阶段标题条/证据链”，避免完全模板化。
    titles = extract_item_titles(tex_path, max_items=4)
    if not titles:
        return spec

    def summarize_title(t: str) -> str:
        t = t.replace("$", "").strip()
        t = t.split("：")[0].split(":")[0].strip()
        for sep in ("（", "(", "["):
            if sep in t:
                t = t.split(sep)[0].strip()
        t = t.strip(" ：:;，,")
        # Keep it single-line friendly for phase header bars.
        if len(t) > 24:
            t = t[:24] + "…"
        return t

    key_boxes = [summarize_title(t) for t in titles]

    # Put key items into phases for stronger “内容对应”.
    # For three-column/layered-pipeline, avoid injecting a short "critical title box" into rows,
    # because mainline box selection may stretch it to the whole phase (huge blanks).
    phase_order = ["数据准备", "模型构建", "机制研究", "临床验证"]
    for i, label in enumerate(phase_order):
        if i >= len(key_boxes):
            break
        for ph in spec.get("phases", []):
            if not (isinstance(ph, dict) and ph.get("label") == label):
                continue
            if (effective_layout or "").strip() in {"three-column", "layered-pipeline"}:
                existing = ph.get("phase_header_override")
                if isinstance(existing, str) and existing.strip() == key_boxes[i].strip():
                    break
                ph["phase_header_override"] = key_boxes[i]
                break

            rows = ph.get("rows")
            if not isinstance(rows, list) or not rows:
                continue
            top = [{"text": key_boxes[i], "kind": "critical", "weight": 3}]
            # Avoid duplicating if already injected in previous run.
            if isinstance(rows[0], list) and rows[0] and isinstance(rows[0][0], dict):
                first_text = rows[0][0].get("text")
                if isinstance(first_text, str) and first_text.strip() == key_boxes[i].strip():
                    break
            rows.insert(0, top)
            break
    return spec


def _apply_auto_fixes(cfg: Dict[str, Any], evaluation: Dict[str, Any]) -> Dict[str, Any]:
    out = deepcopy(cfg)
    counts = evaluation.get("counts", {})
    p0 = int(counts.get("p0", 0))
    p1 = int(counts.get("p1", 0))

    renderer = out["renderer"]
    layout = out["layout"]
    thresholds = (out.get("evaluation", {}) or {}).get("thresholds", {})
    min_font_px = int(thresholds.get("min_font_px", layout.get("min_font_size", renderer["fonts"]["min_size"])))

    if p0 > 0:
        renderer["canvas"]["height_px"] = int(renderer["canvas"]["height_px"]) + 220
        renderer["fonts"]["default_size"] = max(
            max(int(renderer["fonts"]["min_size"]), min_font_px),
            int(renderer["fonts"]["default_size"]) - 2,
        )
        layout["spacing_px"] = max(14, int(layout["spacing_px"]) - 2)
        return out

    if p1 > 0:
        renderer["fonts"]["default_size"] = max(
            max(int(renderer["fonts"]["min_size"]), min_font_px),
            int(renderer["fonts"]["default_size"]) - 2,
        )
        renderer["canvas"]["height_px"] = int(renderer["canvas"]["height_px"]) + 200
        return out

    current = int(renderer["fonts"]["default_size"])
    target_max = int(renderer["fonts"]["title_size"]) - 2
    if current < target_max:
        renderer["fonts"]["default_size"] = current + 1
    return out


def _merge_critiques_into_evaluation(
    evaluation: Dict[str, Any],
    critiques: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Merge critique defects into the main evaluation dict, with a conservative scoring rule:
    - Keep base evaluator's structure, but apply an additional penalty for critique defects.
    - Update evaluation.defects and evaluation.counts.p0/p1/p2 to reflect the merged defect list.
    """
    if not critiques:
        return evaluation

    out = dict(evaluation)
    out["critiques"] = critiques

    base_score = int(out.get("score", 0) or 0)
    out["score_base"] = base_score

    base_defects = out.get("defects", [])
    if not isinstance(base_defects, list):
        base_defects = []

    critique_defects: List[Dict[str, Any]] = []
    p0c = p1c = p2c = 0
    for dim, res in critiques.items():
        if not isinstance(res, dict):
            continue
        for d in res.get("defects", []) if isinstance(res.get("defects", []), list) else []:
            if not isinstance(d, dict):
                continue
            critique_defects.append(d)
            sev = str(d.get("severity", "")).strip()
            if sev == "P0":
                p0c += 1
            elif sev == "P1":
                p1c += 1
            elif sev == "P2":
                p2c += 1

    out["defects"] = base_defects + critique_defects
    out["critique_counts"] = {"p0": p0c, "p1": p1c, "p2": p2c}

    # Additional penalty only for critique defects (avoid double-counting base evaluator signal).
    penalty = p0c * 25 + p1c * 10 + p2c * 3
    out["critique_penalty"] = penalty
    out["score"] = max(0, min(100, base_score - penalty))

    # Refresh p0/p1/p2 totals for early-stop and reporting.
    p0 = sum(1 for d in out["defects"] if isinstance(d, dict) and d.get("severity") == "P0")
    p1 = sum(1 for d in out["defects"] if isinstance(d, dict) and d.get("severity") == "P1")
    p2 = sum(1 for d in out["defects"] if isinstance(d, dict) and d.get("severity") == "P2")

    counts = dict(out.get("counts", {}) if isinstance(out.get("counts", {}), dict) else {})
    counts["p0"] = p0
    counts["p1"] = p1
    counts["p2"] = p2
    out["counts"] = counts

    return out


def main() -> None:
    p = argparse.ArgumentParser(description="Generate NSFC roadmap artifacts from proposal or spec.")
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
    config = load_yaml(config_path)

    max_rounds = int(config["evaluation"]["max_rounds"])
    rounds = int(args.rounds) if args.rounds is not None else max_rounds
    rounds = max(1, min(50, rounds))

    out_dir = args.output_dir if args.output_dir is not None else Path(config["output"]["dirname"])
    if args.output_dir is None:
        info(f"未指定 output_dir，使用默认输出目录：{out_dir}")
    if out_dir.exists() and not out_dir.is_dir():
        fatal(f"output_dir 不是目录：{out_dir}")
    out_dir.mkdir(parents=True, exist_ok=True)

    artifacts = config.get("output", {}).get("artifacts", {})
    if not isinstance(artifacts, dict):
        fatal("config.yaml:output.artifacts 必须是 dict")
    for k in ("drawio", "svg", "png", "pdf", "spec", "spec_latest", "report", "config_best", "evaluation_best"):
        v = artifacts.get(k)
        if v is None:
            continue
        if not isinstance(v, str):
            fatal(f"config.yaml:output.artifacts.{k} 必须是字符串（相对路径）")
        if not _is_safe_relative_path(v):
            fatal(f"config.yaml:output.artifacts.{k} 必须是安全的相对路径（不得包含 `..` 或绝对/盘符路径）：{v!r}")

    work_dir, intermediate_dir, hide_intermediate = _resolve_output_dirs(out_dir, config)
    plan_filename = _plan_filename(config)
    _cleanup_work_dir(work_dir, intermediate_dir, artifacts, hide_intermediate, plan_filename)

    # Instance-local overrides (safe whitelist).
    config_local_path = intermediate_dir / "config_local.yaml"
    local_cfg = _load_config_local(config_local_path)
    cfg_round_base: Dict[str, Any] = _apply_config_local(config, local_cfg)

    # Keep per-run rounds isolated to avoid mixing historical round_* residues.
    run_base = (intermediate_dir / "runs") if hide_intermediate else intermediate_dir
    stop_strategy_effective = str((cfg_round_base.get("evaluation", {}) or {}).get("stop_strategy", "none") or "none").strip()
    ai_mode = stop_strategy_effective == "ai_critic"

    ai_root: Optional[Path] = None
    ai_run_root: Optional[Path] = None

    if ai_mode:
        ai_root = _ai_root(intermediate_dir)
        active = _read_active_run(ai_root, run_base)
        if active is None:
            run_dir = _make_run_dir(run_base)
            _set_active_run(ai_root, run_dir)
        else:
            run_dir = active
        ai_run_root = _ai_run_root(ai_root, run_dir)
    else:
        run_dir = _make_run_dir(run_base)

    spec_latest = intermediate_dir / _spec_latest_filename(config)
    spec_name = str(artifacts.get("spec", "spec.yaml"))

    # In ai_critic mode, resume from spec_latest.yaml if the run already has rounds.
    existing_round_dirs = sorted(
        [p for p in run_dir.iterdir() if p.is_dir() and re.fullmatch(r"round_[0-9]{2}", p.name)]
    )
    if ai_mode and existing_round_dirs and spec_latest.exists():
        spec_data = load_yaml(spec_latest)
        tex_path = None
        if args.spec_file or args.proposal_file or args.proposal_path:
            warn("ai_critic 模式检测到已有历史 round_*；为避免混淆，本次忽略新的输入参数，继续使用 spec_latest.yaml")
    else:
        tex_path: Optional[Path] = None
        if args.spec_file:
            if not args.spec_file.exists() or not args.spec_file.is_file():
                fatal(f"spec_file 不存在或不是文件：{args.spec_file}")
            info(f"使用用户 spec：{args.spec_file}")
            spec_data = load_yaml(args.spec_file)
        else:
            spec_data = default_spec_for_nsfc_young_2026()
            if args.proposal_file:
                if not args.proposal_file.exists() or not args.proposal_file.is_file():
                    fatal(f"proposal_file 不存在或不是文件：{args.proposal_file}")
                tex_path = args.proposal_file
            elif args.proposal_path:
                if not args.proposal_path.exists():
                    fatal(f"proposal_path 不存在：{args.proposal_path}")
                tex_path = find_candidate_tex(args.proposal_path)
            if tex_path and tex_path.exists():
                info(f"从 tex 抽取提示：{tex_path}")
                layout_cfg = cfg_round_base.get("layout", {}) if isinstance(cfg_round_base.get("layout", {}), dict) else {}
                cfg_lt = layout_cfg.get("template")
                cfg_ref = layout_cfg.get("template_ref")
                lt = spec_data.get("layout_template") or (str(cfg_lt).strip() if isinstance(cfg_lt, str) else None)
                ref = spec_data.get("template_ref") or (str(cfg_ref).strip() if isinstance(cfg_ref, str) else None)
                effective, _ = resolve_layout_template(layout_template=lt, template_ref=ref, root=root)
                spec_data = _apply_tex_hints(spec_data, tex_path, effective_layout=effective)
                spec_data["title"] = "技术路线图（自动生成）"
            else:
                info("未提供可用 tex；使用默认示例 spec。")

    write_text(spec_latest, dump_yaml(spec_data))
    write_text(run_dir / spec_name, dump_yaml(spec_data))
    _ensure_plan_file(work_dir, plan_filename, spec_data, spec_latest)

    # ai_critic: apply response patches (spec/config_local) before rendering the next round.
    ai_action: Optional[str] = None
    if ai_mode and ai_run_root is not None:
        spec_data, config_local_patch, ai_action = _maybe_apply_ai_response(ai_run_root, spec_data, spec_latest)
        if config_local_patch is not None:
            base_local = local_cfg if isinstance(local_cfg, dict) else {}
            merged_local = _deep_merge_dict(base_local, config_local_patch)
            write_text(config_local_path, dump_yaml(merged_local))
            local_cfg = merged_local
            cfg_round_base = _apply_config_local(config, local_cfg)
            stop_strategy_effective = str((cfg_round_base.get("evaluation", {}) or {}).get("stop_strategy", "none") or "none").strip()
            ai_mode = stop_strategy_effective == "ai_critic"

        # Persist updated snapshots after applying response (if any).
        write_text(spec_latest, dump_yaml(spec_data))
        write_text(run_dir / spec_name, dump_yaml(spec_data))

        if ai_action == "stop":
            info("ai_critic: 收到 stop 指令，将导出当前 best 并清理 ACTIVE_RUN。")
            _clear_active_run(_ai_root(intermediate_dir))

    input_excerpt_path: Optional[Path] = None
    if ai_mode and ai_run_root is not None:
        input_excerpt_path = ai_run_root / "input_excerpt.md"
        if not input_excerpt_path.exists():
            src = f"- source: {tex_path.as_posix()}" if (tex_path is not None and tex_path.exists()) else "- source: (no tex input)"
            body = ""
            if tex_path is not None and tex_path.exists():
                try:
                    body = _strip_latex_to_excerpt(extract_research_content_section(tex_path))
                except Exception:
                    body = _strip_latex_to_excerpt(tex_path.read_text(encoding="utf-8", errors="ignore"))
            else:
                body = "（无 tex 输入；请基于 spec_latest.yaml 自行补充关键叙事与证据链。）"
            write_text(
                input_excerpt_path,
                "\n".join(
                    [
                        "# input_excerpt（自动裁剪/清洗）",
                        "",
                        src,
                        "",
                        body.strip(),
                        "",
                    ]
                ),
            )

    report_path = run_dir / _report_filename(config)
    drawio_cmd = ensure_drawio_cli(cfg_round_base)
    drawio_mode = "drawio_cli" if drawio_cmd else "internal_renderer"
    report_lines: List[str] = [
        "# 技术路线图优化记录",
        "",
        f"- run_dir: {run_dir.name}",
        f"- work_dir: {work_dir}",
        f"- intermediate_dir: {intermediate_dir}",
        f"- rounds: {rounds}",
        f"- spec_latest: {spec_latest}",
        f"- plan: {work_dir / plan_filename}",
        f"- renderer_mode: {drawio_mode}",
        "",
    ]

    best_round = 0
    best_score = -1
    best_round_dir: Optional[Path] = None

    # If resuming (ai_critic), pick current best from existing rounds first.
    for rd in existing_round_dirs if "existing_round_dirs" in locals() else []:
        evp = rd / "evaluation.json"
        if not evp.exists():
            continue
        try:
            ev = json.loads(evp.read_text(encoding="utf-8"))
            score = int(ev.get("score", 0) or 0) if isinstance(ev, dict) else 0
        except Exception:
            continue
        if score > best_score:
            best_score = score
            try:
                best_round = int(rd.name.split("_", 1)[1])
            except Exception:
                best_round = best_round
            best_round_dir = rd

    if drawio_cmd:
        report_lines.extend(
            [
                f"- drawio_cli: {drawio_cmd}",
                "",
            ]
        )
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

    cfg_round: Dict[str, Any] = deepcopy(cfg_round_base)
    early_stop = (cfg_round.get("evaluation", {}) or {}).get("early_stop", {})
    early_stop_enabled = bool(early_stop.get("enabled", False))
    min_rounds = int(early_stop.get("min_rounds", 1))
    consecutive_pass = int(early_stop.get("consecutive_pass", 2))
    allow_p1 = int(early_stop.get("allow_p1", 0))
    pass_streak = 0

    stop_strategy = str((cfg_round.get("evaluation", {}) or {}).get("stop_strategy", "none"))
    plateau = (cfg_round.get("evaluation", {}) or {}).get("plateau", {})
    min_explore_rounds = int(plateau.get("min_explore_rounds", 4))
    same_image_rounds = int(plateau.get("same_image_rounds", 2))
    no_improve_rounds = int(plateau.get("no_improve_rounds", 3))
    min_delta = float(plateau.get("min_delta", 1))

    exploration = (cfg_round.get("evaluation", {}) or {}).get("exploration", {})
    self_check = (cfg_round.get("evaluation", {}) or {}).get("multi_round_self_check", {})
    self_check_enabled = bool((self_check or {}).get("enabled", True))
    critique_dimensions = (self_check or {}).get("critique_dimensions", ["structure", "visual", "readability"])
    if not isinstance(critique_dimensions, list):
        critique_dimensions = ["structure", "visual", "readability"]
    max_workers = int((self_check or {}).get("max_workers", 3) or 3)

    score_hist: List[int] = []
    hash_hist: List[Optional[str]] = []

    rounds_iter: Any
    if ai_mode:
        if ai_action == "stop":
            rounds_iter = []
        else:
            if existing_round_dirs and ai_action is None:
                if ai_run_root is not None:
                    last_round = len(existing_round_dirs)
                    pack_dir = _ai_pack_dir(ai_run_root, last_round)
                    if not pack_dir.exists():
                        pack_dir = existing_round_dirs[-1]
                    _write_ai_critic_request(
                        ai_run_root,
                        round_idx=last_round,
                        pack_dir=pack_dir,
                        response_path=_ai_response_path(ai_run_root),
                    )
                    info(f"ai_critic: 等待响应文件：{_ai_response_path(ai_run_root)}")
                    info(f"ai_critic: request：{_ai_request_path(ai_run_root)}")
                else:
                    info("ai_critic: 等待响应文件（ai_run_root 缺失）")
                write_text(report_path, "\n".join(report_lines) + "\n")
                return

            next_r = len(existing_round_dirs) + 1
            if next_r > rounds:
                report_lines.extend(
                    [
                        "## Stop (ai_critic)",
                        "",
                        f"- reason: reached max rounds ({rounds})",
                        "",
                    ]
                )
                if ai_root is not None:
                    _clear_active_run(ai_root)
                rounds_iter = []
            else:
                rounds_iter = [next_r]
    else:
        rounds_iter = range(1, rounds + 1)

    for r in rounds_iter:
        round_dir = run_dir / f"round_{r:02d}"
        round_dir.mkdir(parents=True, exist_ok=True)
        round_spec = round_dir / spec_name
        round_cfg = round_dir / "config_used.yaml"
        cfg_used = (
            deepcopy(cfg_round)
            if ai_mode
            else _apply_exploration(cfg_round, r, exploration if isinstance(exploration, dict) else {})
        )
        write_text(round_spec, dump_yaml(spec_data))
        write_text(round_cfg, dump_yaml(cfg_used))

        templates_selected_path: Optional[Path] = None
        if ai_mode and ai_run_root is not None:
            try:
                layout_cfg = cfg_used.get("layout", {}) if isinstance(cfg_used.get("layout", {}), dict) else {}
                lt = spec_data.get("layout_template") or (
                    layout_cfg.get("template") if isinstance(layout_cfg.get("template"), str) else None
                )
                ref = spec_data.get("template_ref") or (
                    layout_cfg.get("template_ref") if isinstance(layout_cfg.get("template_ref"), str) else None
                )
                effective, tmpl = resolve_layout_template(layout_template=lt, template_ref=ref, root=root)
                db = load_template_db(root=root)
                fam = db.families.get(effective, {}) if isinstance(db.families, dict) else {}
                selected = {
                    "effective_layout": effective,
                    "template_ref": ref,
                    "template": {
                        "id": tmpl.id,
                        "file": tmpl.file,
                        "family": tmpl.family,
                        "use_when": tmpl.use_when,
                        "avoid": tmpl.avoid,
                    }
                    if tmpl is not None
                    else None,
                    "family_description": fam.get("description") if isinstance(fam, dict) else None,
                    "family_tokens": fam.get("tokens") if isinstance(fam, dict) else None,
                }
                templates_selected_path = round_dir / "templates_selected.yaml"
                write_text(templates_selected_path, dump_yaml(selected))  # type: ignore[arg-type]
            except Exception as exc:
                warn(f"templates_selected 生成失败（已跳过）：{exc}")

        out_png, out_svg, out_drawio = render(round_spec, round_cfg, round_dir)
        try:
            _validate_drawio_xml(out_drawio)
        except Exception as exc:
            report_lines.extend(
                [
                    f"## Round {r}",
                    "",
                    "- preflight: FAILED",
                    f"- error: {exc}",
                    "",
                    "## Stop (preflight)",
                    "",
                    "- reason: drawio XML 非法，已阻断后续评估",
                    "",
                ]
            )
            write_text(report_path, "\n".join(report_lines) + "\n")
            fatal(str(exc))

        # Measurement export: script-only evidence (no grading). Useful for ai_critic and for debugging.
        evaluation_mode = str((cfg_used.get("evaluation", {}) or {}).get("evaluation_mode", "heuristic") or "heuristic").strip().lower()
        if ai_mode:
            evaluation_mode = "ai"
        if evaluation_mode == "ai":
            try:
                m = measure_roadmap(round_spec, round_cfg, png_path=out_png, drawio_path=out_drawio)
                (round_dir / "measurements.json").write_text(
                    json.dumps(m, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
                )
            except Exception as exc:
                warn(f"measurements.json 生成失败（已跳过）：{exc}")
            try:
                dm = measure_dimensions(round_spec, round_cfg, png_path=out_png)
                (round_dir / "dimension_measurements.json").write_text(
                    json.dumps(dm, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
                )
            except Exception as exc:
                warn(f"dimension_measurements.json 生成失败（已跳过）：{exc}")

        evaluation = evaluate(round_spec, round_cfg, png_path=out_png, drawio_path=out_drawio)

        critiques: Dict[str, Dict[str, Any]] = {}
        if self_check_enabled:
            try:
                critiques = run_critiques(
                    round_spec,
                    round_cfg,
                    png_path=out_png,
                    drawio_path=out_drawio,
                    dimensions=[str(x) for x in critique_dimensions],
                    max_workers=max_workers,
                )
            except Exception as exc:
                # Self-check is "nice to have": never break the main deliverable pipeline.
                warn(f"multi_round_self_check 运行失败（已跳过）：{exc}")
                critiques = {}

        # Persist per-dimension critique results for traceability.
        for dim, res in critiques.items():
            try:
                (round_dir / f"critique_{dim}.json").write_text(
                    json.dumps(res, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
                )
            except Exception:
                pass

        evaluation = _merge_critiques_into_evaluation(evaluation, critiques)

        (round_dir / "evaluation.json").write_text(json.dumps(evaluation, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        if ai_mode and ai_run_root is not None:
            pack = _write_ai_pack(
                ai_run_root,
                round_idx=r,
                input_excerpt_path=input_excerpt_path,
                templates_selected_path=templates_selected_path,
                round_spec=round_spec,
                round_cfg=round_cfg,
                out_png=out_png,
                round_dir=round_dir,
            )
            _write_ai_critic_request(
                ai_run_root,
                round_idx=r,
                pack_dir=pack,
                response_path=_ai_response_path(ai_run_root),
            )

        score = int(evaluation.get("score", 0) or 0)
        if score > best_score:
            best_score = score
            best_round = r
            best_round_dir = round_dir

        png_hash = _sha256_file(out_png)
        score_hist.append(score)
        hash_hist.append(png_hash)

        counts = evaluation.get("counts", {})
        p0 = int(counts.get("p0", 0))
        p1 = int(counts.get("p1", 0))
        if p0 == 0 and p1 <= allow_p1:
            pass_streak += 1
        else:
            pass_streak = 0

        if not ai_mode:
            cfg_round = _apply_auto_fixes(cfg_round, evaluation)

        report_lines.append(f"## Round {r}")
        report_lines.append("")
        report_lines.append(f"- artifacts: `{round_dir.name}/`")
        base_score = evaluation.get("score_base")
        if isinstance(base_score, int):
            report_lines.append(f"- score: {score} (base {base_score}, critique_penalty={evaluation.get('critique_penalty', 0)})")
        else:
            report_lines.append(f"- score: {score}")
        report_lines.append(f"- png_sha256: {png_hash or 'N/A'}")
        report_lines.append(
            f"- defects: P0={counts.get('p0', 0)} P1={counts.get('p1', 0)} P2={counts.get('p2', 0)}"
        )
        if isinstance(evaluation.get("critique_counts", {}), dict):
            cc = evaluation.get("critique_counts", {})
            report_lines.append(f"- critique_defects: P0={cc.get('p0', 0)} P1={cc.get('p1', 0)} P2={cc.get('p2', 0)}")
        report_lines.append(
            f"- font_size: {evaluation.get('font', {}).get('size', '?')} (min {evaluation.get('font', {}).get('min_required', '?')})"
        )
        report_lines.append("")

        if ai_mode:
            if ai_run_root is not None:
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

        if early_stop_enabled and r >= min_rounds and pass_streak >= consecutive_pass:
            report_lines.append("## Early Stop")
            report_lines.append("")
            report_lines.append(
                f"- reason: pass_streak={pass_streak} (P0==0 and P1<={allow_p1})"
            )
            report_lines.append("")
            break

        if early_stop_enabled:
            continue

        if stop_strategy not in ("none", "plateau", "ai_critic"):
            # Unknown value: behave like "none" to avoid surprise.
            continue
        if stop_strategy == "none":
            continue
        if stop_strategy == "ai_critic":
            # Placeholder: do nothing by default (no model/network usage).
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
        warn("未找到 best round；跳过最终导出。")
        _copy_if_exists(report_path, intermediate_dir / _report_filename(config))
        info(f"完成（无导出）：{run_dir}")
        return

    for key in ("drawio", "svg", "png", "pdf"):
        name = artifacts.get(key)
        if isinstance(name, str):
            _copy_if_exists(best_round_dir / name, run_dir / name)
            _copy_if_exists(best_round_dir / name, work_dir / name)

    # Export meta for reproducibility (keep them in intermediate, not deliverables root).
    config_best_name = str(artifacts.get("config_best", "config_used_best.yaml"))
    evaluation_best_name = str(artifacts.get("evaluation_best", "evaluation_best.json"))
    _copy_if_exists(best_round_dir / "config_used.yaml", run_dir / config_best_name)
    _copy_if_exists(best_round_dir / "evaluation.json", run_dir / evaluation_best_name)
    _copy_if_exists(best_round_dir / "config_used.yaml", intermediate_dir / config_best_name)
    _copy_if_exists(best_round_dir / "evaluation.json", intermediate_dir / evaluation_best_name)

    report_path.write_text(
        report_path.read_text(encoding="utf-8")
        + "\n"
        + "\n".join(
            [
                "## Final",
                "",
                f"- best_round: {best_round} (score {best_score})",
                f"- exported: `{str(artifacts.get('drawio', 'roadmap.drawio'))}`, `{str(artifacts.get('svg', 'roadmap.svg'))}`, `{str(artifacts.get('png', 'roadmap.png'))}`, `{str(artifacts.get('pdf', 'roadmap.pdf'))}`",
                f"- exported_meta: `{config_best_name}`, `{evaluation_best_name}`",
                "",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    # Convenience: keep the latest report at intermediate_dir root.
    _copy_if_exists(report_path, intermediate_dir / _report_filename(config))

    if hide_intermediate:
        max_runs = int(config.get("output", {}).get("max_history_runs", 10) or 0)
        _prune_history_runs(intermediate_dir, max_runs=max_runs)

    info(f"完成：{run_dir}（交付文件位于 {work_dir}；中间产物位于 {intermediate_dir}）")


if __name__ == "__main__":
    main()
