from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path, PureWindowsPath
import shutil
from typing import Any, Dict, List, Optional

from extract_proposal import extract as extract_proposal
from extract_from_tex import extract_item_titles, find_candidate_tex
from generate_roadmap import _apply_tex_hints
from model_gallery import materialize_model_gallery
from spec import default_spec_for_nsfc_young_2026
from template_library import get_template, load_template_db, resolve_layout_template
from utils import dump_yaml, fatal, info, load_yaml, read_text, skill_root, warn, write_text


def _is_safe_relative_path(p: str) -> bool:
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


def _resolve_output_dirs(out_dir: Path, config: Dict[str, Any]) -> tuple[Path, Path, bool]:
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
        intermediate_dir.mkdir(parents=True, exist_ok=True)
        (intermediate_dir / "runs").mkdir(parents=True, exist_ok=True)
        (intermediate_dir / "legacy").mkdir(parents=True, exist_ok=True)
        (intermediate_dir / "legacy" / "files").mkdir(parents=True, exist_ok=True)
    else:
        intermediate_dir = work_dir
    return work_dir, intermediate_dir, hide


def _plan_filename(config: Dict[str, Any]) -> str:
    planning_cfg = config.get("planning", {}) if isinstance(config.get("planning", {}), dict) else {}
    output_cfg = planning_cfg.get("output", {}) if isinstance(planning_cfg.get("output", {}), dict) else {}
    return str(output_cfg.get("plan_filename") or "roadmap-plan.md")


def _spec_draft_filename(config: Dict[str, Any]) -> str:
    planning_cfg = config.get("planning", {}) if isinstance(config.get("planning", {}), dict) else {}
    output_cfg = planning_cfg.get("output", {}) if isinstance(planning_cfg.get("output", {}), dict) else {}
    return str(output_cfg.get("spec_filename") or "spec_draft.yaml")


def _summarize_phases(spec_data: Dict[str, Any]) -> List[str]:
    phases = spec_data.get("phases", [])
    out: List[str] = []
    if not isinstance(phases, list):
        return out
    for i, ph in enumerate(phases, start=1):
        if not isinstance(ph, dict):
            continue
        label = str(ph.get("label", f"Phase {i}")).strip() or f"Phase {i}"
        rows = ph.get("rows", [])
        box_count = 0
        if isinstance(rows, list):
            for row in rows:
                if isinstance(row, list):
                    box_count += len(row)
        out.append(f"- Phase {i}: {label}（{box_count} 节点）")
    return out


def _load_context_text(context: Optional[str], context_file: Optional[Path]) -> Optional[str]:
    if context and context.strip():
        return context.strip()
    if context_file is None:
        return None
    if not context_file.exists() or not context_file.is_file():
        fatal(f"context_file 不存在或不是文件：{context_file}")
    return read_text(context_file).strip()


def _backup_then_overwrite(dst: Path, intermediate_dir: Path) -> None:
    if not dst.exists():
        return
    if not dst.is_file():
        fatal(f"输出文件已存在但不是普通文件：{dst}")
    ts = datetime.now().strftime("%Y%m%d%H%M%S")
    legacy_dir = intermediate_dir / "legacy" / "files"
    legacy_dir.mkdir(parents=True, exist_ok=True)
    backup = legacy_dir / f"{dst.stem}.backup_{ts}{dst.suffix}"
    shutil.copy2(dst, backup)


def main() -> None:
    p = argparse.ArgumentParser(description="Plan NSFC roadmap (generate roadmap-plan.md + spec_draft.yaml).")
    p.add_argument(
        "--mode",
        type=str,
        default=None,
        help="template|ai（默认取 config.yaml:planning.planning_mode；若配置缺失则为 template）",
    )
    p.add_argument("--proposal-path", type=Path, default=None)
    p.add_argument("--proposal-file", type=Path, default=None)
    p.add_argument("--proposal", type=str, default=None, help="纯文本：研究内容/技术路线概述（可选）")
    p.add_argument("--context", type=str, default=None)
    p.add_argument("--context-file", type=Path, default=None)
    p.add_argument("--output-dir", type=Path, required=False, default=None)
    p.add_argument("--config", type=Path, required=False, default=None)
    p.add_argument(
        "--template",
        type=str,
        default=None,
        help="auto|classic|three-column|packed-three-column|layered-pipeline（可选；也可仅用 --template-ref）",
    )
    p.add_argument(
        "--template-ref",
        type=str,
        default=None,
        help="具体模板 id（例如 model-02；见 references/models/templates.yaml）",
    )
    args = p.parse_args()

    if args.mode is not None and str(args.mode).strip():
        m = str(args.mode).strip().lower()
        if m not in {"template", "ai"}:
            fatal("--mode 不合法：{!r}（允许：template|ai）".format(m))

    if args.template and str(args.template).strip():
        t = str(args.template).strip()
        if t not in ("auto", "classic", "three-column", "packed-three-column", "layered-pipeline"):
            fatal(f"--template 不合法：{t!r}（允许：auto|classic|three-column|packed-three-column|layered-pipeline）")

    if not (
        args.proposal_path
        or args.proposal_file
        or (args.proposal and str(args.proposal).strip())
        or (args.context and str(args.context).strip())
        or args.context_file
    ):
        fatal("至少提供其一：--proposal-path / --proposal-file / --proposal / --context / --context-file")

    root = skill_root()
    config_path = args.config if args.config is not None else (root / "config.yaml")
    if not config_path.exists() or not config_path.is_file():
        fatal(f"config 不存在或不是文件：{config_path}")
    config = load_yaml(config_path)

    planning_cfg = config.get("planning", {}) if isinstance(config.get("planning", {}), dict) else {}
    mode_cfg = str(planning_cfg.get("planning_mode", "template") or "template").strip().lower()
    mode_effective = (str(args.mode).strip().lower() if (args.mode and str(args.mode).strip()) else mode_cfg) or "template"
    if mode_effective not in {"template", "ai"}:
        fatal(f"config.yaml:planning.planning_mode 不合法：{mode_cfg!r}（允许 template|ai）")

    out_dir = args.output_dir if args.output_dir is not None else Path(config["output"]["dirname"])
    if args.output_dir is None:
        info(f"未指定 output_dir，使用默认输出目录：{out_dir}")
    if out_dir.exists() and not out_dir.is_dir():
        fatal(f"output_dir 不是目录：{out_dir}")
    out_dir.mkdir(parents=True, exist_ok=True)

    work_dir, intermediate_dir, hide_intermediate = _resolve_output_dirs(out_dir, config)
    plan_filename = _plan_filename(config)
    spec_filename = _spec_draft_filename(config)

    # In AI mode, planning is a 2-step protocol:
    # 1) script writes plan_request.json (+ optional markdown request)
    # 2) host AI writes roadmap-plan.md + spec_draft.yaml, then rerun to validate
    if mode_effective == "ai":
        # Resolve spec output root (keep consistent with template mode).
        spec_root = intermediate_dir if hide_intermediate else work_dir
        spec_path = spec_root / spec_filename
        plan_path = work_dir / plan_filename

        req_dir = intermediate_dir / "planning"
        req_dir.mkdir(parents=True, exist_ok=True)
        req_json = req_dir / "plan_request.json"
        req_md = req_dir / "plan_request.md"

        # Produce proposal extraction (deterministic).
        # In AI planning mode, allow "context-only" runs by treating context as inline proposal_text.
        context_text = _load_context_text(args.context, args.context_file)
        inline_text: Optional[str] = None
        if args.proposal and str(args.proposal).strip():
            inline_text = str(args.proposal).strip()
        if context_text:
            inline_text = (inline_text + "\n\n" + context_text).strip() if inline_text else context_text.strip()

        proposal_extract = extract_proposal(
            proposal_path=args.proposal_path,
            proposal_file=args.proposal_file,
            proposal_text=inline_text,
        )

        # Model gallery is for visual learning only in AI planning mode.
        # Host AI should not be forced to pick a single template_ref; keep the spec flexible.
        gallery: Dict[str, str] = {}
        try:
            db = load_template_db(root=root)
            # Visual picker evidence (contact sheet + copied images).
            fonts_cfg = (
                (config.get("renderer", {}) or {}).get("fonts", {})
                if isinstance((config.get("renderer", {}) or {}).get("fonts", {}), dict)
                else {}
            )
            candidates = (
                fonts_cfg.get("candidates", [])
                if isinstance(fonts_cfg.get("candidates", []), list)
                else []
            )
            gallery = materialize_model_gallery(
                list(db.templates.values()),
                src_dir=root / "references" / "models",
                out_dir=req_dir,
                font_candidates=[str(x) for x in candidates if isinstance(x, str)],
            )
        except Exception as exc:
            warn(f"生成模型画廊失败（将继续，仅影响视觉参考证据）：{exc}")

        # Constraints from config (script-owned hard constraints).
        canvas = (config.get("renderer", {}) or {}).get("canvas", {}) if isinstance((config.get("renderer", {}) or {}).get("canvas", {}), dict) else {}
        fonts = (config.get("renderer", {}) or {}).get("fonts", {}) if isinstance((config.get("renderer", {}) or {}).get("fonts", {}), dict) else {}
        constraints = {
            "canvas": {"width_px": int(canvas.get("width_px", 2400)), "height_px": int(canvas.get("height_px", 1800))},
            "max_phases": 5,
            "boxes_per_phase": "2-6",
            "font_size_px": int(fonts.get("default_size", 28)),
            "template_policy": {
                "use_template_ref": False,
                "note": "纯 AI 规划：模板画廊仅用于学习，不要求也不建议在 spec 中写 template_ref。",
            },
        }

        req = {
            "proposal_extract": proposal_extract,
            "model_gallery": gallery,
            "extra_context": context_text,
            "constraints": constraints,
            "output": {
                "write_plan_to": plan_path.as_posix(),
                "write_spec_to": spec_path.as_posix(),
                "spec_filename": spec_filename,
                "plan_filename": plan_filename,
            },
        }

        import json

        write_text(req_json, json.dumps(req, ensure_ascii=False, indent=2) + "\n")

        # Write an explicit request for host AI (kept stable to support offline runs).
        req_lines: List[str] = []
        req_lines.append("# nsfc-roadmap planning request (mode=ai)")
        req_lines.append("")
        req_lines.append("你将扮演“规划者”：基于提取的标书内容（立项依据 + 研究内容/技术路线），生成可落地的路线图规划与 spec 草案。")
        req_lines.append("")
        req_lines.append("## 输入证据（脚本已生成）")
        req_lines.append("")
        req_lines.append(f"- request_data: `{req_json.as_posix()}`")
        if gallery.get("contact_sheet"):
            req_lines.append(f"- models_contact_sheet（可先看图学习优秀结构/信息密度控制）: `{gallery['contact_sheet']}`")
        if gallery.get("models_dir"):
            req_lines.append(f"- models_dir（单张参考图）: `{gallery['models_dir']}`")
        req_lines.append("")
        req_lines.append("## 你的输出（必须同时写出 2 个文件）")
        req_lines.append("")
        req_lines.append(f"1) `roadmap-plan.md` → 写到：`{plan_path.as_posix()}`")
        req_lines.append(f"2) `spec_draft.yaml` → 写到：`{spec_path.as_posix()}`")
        req_lines.append("")
        req_lines.append("### 约束（必须满足）")
        req_lines.append("")
        req_lines.append("- spec 必须符合 `scripts/spec.py:load_spec()` 校验（字段齐全、结构合法）")
        req_lines.append("- 每阶段建议 2-6 个节点；主线闭环清晰；至少 1 个风险/替代方案节点（若研究叙事允许）")
        req_lines.append("- 纯 AI 规划：不要在 spec 中写 `template_ref`（除非用户明确要求固定某个模板）")
        req_lines.append("- `layout_template` 可选；不写也可以（渲染阶段会使用 config 的默认 layout 策略）")
        req_lines.append("")
        req_lines.append("当你写完两个文件后，请再次运行本脚本以进行合法性校验。")
        req_lines.append("")
        write_text(req_md, "\n".join(req_lines) + "\n")

        # If host AI already wrote outputs, validate and exit success.
        if plan_path.exists() and spec_path.exists():
            try:
                from spec import load_spec as _load_spec

                spec_data = load_yaml(spec_path)
                _load_spec(spec_data)
            except Exception as exc:
                fatal(f"AI 产出的 spec_draft.yaml 非法：{exc}")
            warn(f"AI 规划产物已就绪：{plan_path}")
            info(f"spec 草案：{spec_path}")
            return

        warn("AI 规划请求已生成，等待宿主 AI 写入 roadmap-plan.md + spec_draft.yaml：")
        info(f"- request: {req_md}")
        info(f"- data: {req_json}")
        return

    spec_data = default_spec_for_nsfc_young_2026()
    spec_data["title"] = "技术路线图（规划草案）"
    if "notes" in spec_data:
        spec_data.pop("notes", None)

    # Optional: attach template selection (kept in spec for reproducibility).
    if args.template and str(args.template).strip():
        spec_data["layout_template"] = str(args.template).strip()
    if args.template_ref and str(args.template_ref).strip():
        spec_data["template_ref"] = str(args.template_ref).strip()

    tex_path: Optional[Path] = None
    if args.proposal_file:
        if not args.proposal_file.exists() or not args.proposal_file.is_file():
            fatal(f"proposal_file 不存在或不是文件：{args.proposal_file}")
        tex_path = args.proposal_file
    elif args.proposal_path:
        if not args.proposal_path.exists():
            fatal(f"proposal_path 不存在：{args.proposal_path}")
        tex_path = find_candidate_tex(args.proposal_path)

    titles: List[str] = []
    if tex_path and tex_path.exists():
        titles = extract_item_titles(tex_path, max_items=5)
        if titles:
            try:
                effective, _ = resolve_layout_template(
                    layout_template=spec_data.get("layout_template"),
                    template_ref=spec_data.get("template_ref"),
                    root=root,
                )
            except Exception:
                effective = str(spec_data.get("layout_template") or "classic")
            spec_data = _apply_tex_hints(spec_data, tex_path, effective_layout=effective)

    context_text = _load_context_text(args.context, args.context_file)
    if args.proposal and str(args.proposal).strip():
        # Keep proposal text only in plan markdown (not in spec.notes).
        extra = str(args.proposal).strip()
        context_text = (context_text + "\n\n" + extra).strip() if context_text else extra

    spec_root = intermediate_dir if hide_intermediate else work_dir
    spec_path = spec_root / spec_filename
    write_text(spec_path, dump_yaml(spec_data))

    plan_path = work_dir / plan_filename
    _backup_then_overwrite(plan_path, intermediate_dir if hide_intermediate else work_dir)

    canvas = (
        (config.get("renderer", {}) or {}).get("canvas", {})
        if isinstance((config.get("renderer", {}) or {}).get("canvas", {}), dict)
        else {}
    )
    width_px = int(canvas.get("width_px", 2400))
    height_px = int(canvas.get("height_px", 1800))

    lines: List[str] = []
    lines.append("# roadmap-plan（规划草案）")
    lines.append("")
    lines.append("此文件用于先规划、后落图的流程：请先审阅本计划，再运行生成脚本。")
    lines.append("")
    lines.append("## 版式与交付约束")
    lines.append("")
    lines.append(f"- 画布：{width_px}x{height_px}px（A4 宽度不变，高度约 2/3 A4）")
    lines.append("- 标题/备注默认不落图（需显式开启 config.yaml:layout.title.enabled / layout.notes.enabled）")
    lines.append("- 交付根目录仅保留：roadmap.drawio/svg/png/pdf + roadmap-plan.md + .nsfc-roadmap/")
    lines.append("")

    # Template reference (optional, but recommended).
    try:
        # Ensure templates.yaml is readable early; do not fail hard if missing.
        db = load_template_db(root=root)
        # Always emit the visual model gallery for human/host-AI selection.
        planning_dir = intermediate_dir / "planning"
        planning_dir.mkdir(parents=True, exist_ok=True)
        fonts_cfg = (
            (config.get("renderer", {}) or {}).get("fonts", {})
            if isinstance((config.get("renderer", {}) or {}).get("fonts", {}), dict)
            else {}
        )
        candidates = fonts_cfg.get("candidates", []) if isinstance(fonts_cfg.get("candidates", []), list) else []
        gallery = materialize_model_gallery(
            list(db.templates.values()),
            src_dir=root / "references" / "models",
            out_dir=planning_dir,
            font_candidates=[str(x) for x in candidates if isinstance(x, str)],
        )
        effective, tmpl = resolve_layout_template(
            layout_template=spec_data.get("layout_template"),
            template_ref=spec_data.get("template_ref"),
            root=root,
        )
        if (spec_data.get("layout_template") or spec_data.get("template_ref") or effective != "classic") and effective:
            lines.append("## 模板参考（风格约束）")
            lines.append("")
            if spec_data.get("template_ref"):
                tref = str(spec_data.get("template_ref"))
                tinfo = get_template(tref, root=root)
                if tinfo is None:
                    lines.append(f"- template_ref: {tref}（⚠️ 未在 templates.yaml 中找到，将仅按 layout_template 回退）")
                else:
                    extra = ""
                    if tinfo.render_family and tinfo.render_family.strip() and tinfo.render_family.strip() != tinfo.family:
                        extra = f"；render_family: {tinfo.render_family}"
                    lines.append(f"- template_ref: {tinfo.id}（family: {tinfo.family}{extra}；file: {tinfo.file}）")
            if spec_data.get("layout_template"):
                lines.append(f"- layout_template: {spec_data.get('layout_template')}")
            lines.append(f"- effective_layout（用于渲染策略选择）: {effective}")
            lines.append("")
            lines.append("落地到 spec 的要求（建议）：")
            lines.append("- 保持“参考而非照搬”；先落骨架（分区/列/主链），再微调配色与信息层级")
            lines.append("- 约束写在本计划里（配色/分区/层级），并映射到 spec 节点分组与文本密度控制")
            lines.append("")
        if gallery.get("contact_sheet"):
            lines.append("## 模型画廊（视觉选型）")
            lines.append("")
            lines.append(f"- models_contact_sheet: `{gallery['contact_sheet']}`（推荐：先看图学习优秀结构与信息密度控制）")
            if gallery.get("models_dir"):
                lines.append(f"- models_dir: `{gallery['models_dir']}`（单张参考图）")
            lines.append("")
    except Exception:
        # Keep plan generation robust; template selection is optional.
        pass

    if tex_path:
        lines.append("## 输入来源")
        lines.append("")
        lines.append(f"- proposal_file: {tex_path}")
        if titles:
            lines.append(f"- 抽取到条目标题（前 {len(titles)} 个）:")
            for t in titles:
                lines.append(f"  - {t}")
        lines.append("")

    if context_text:
        lines.append("## 额外上下文（用户提供）")
        lines.append("")
        lines.append(context_text)
        lines.append("")

    lines.append("## 阶段与节点（草案）")
    lines.append("")
    phase_lines = _summarize_phases(spec_data)
    lines.extend(phase_lines if phase_lines else ["- （未解析到 phases）"])
    lines.append("")

    lines.append("## 命名与一致性约束")
    lines.append("")
    lines.append("- 节点命名与正文术语一致，避免口号式长句")
    lines.append("- 每阶段 2–6 个节点，避免过密/过稀")
    lines.append("- 输入→方法→评估→验证/交付形成闭环（写在计划而非图底备注）")
    lines.append("")

    lines.append("## 不落图但需要强调的内容")
    lines.append("")
    lines.append("- 评估口径、缩印可读性、风险与替代方案等")
    lines.append("")

    lines.append("## 可复现输入与下一步")
    lines.append("")
    lines.append(f"- spec_draft（中间产物）：`{spec_path}`")
    lines.append("")
    lines.append("生成交付文件（建议先手动微调 spec_draft 后再跑）：")
    lines.append("")
    lines.append("```bash")
    lines.append(
        f"python3 {(root / 'scripts' / 'generate_roadmap.py').as_posix()} "
        f"--spec-file {spec_path.as_posix()} "
        f"--output-dir {work_dir.as_posix()} "
        f"--rounds {int(config.get('evaluation', {}).get('max_rounds', 5))}"
    )
    lines.append("```")
    lines.append("")

    write_text(plan_path, "\n".join(lines) + "\n")

    warn(f"规划完成：{plan_path}")
    info(f"spec 草案：{spec_path}")


if __name__ == "__main__":
    main()
