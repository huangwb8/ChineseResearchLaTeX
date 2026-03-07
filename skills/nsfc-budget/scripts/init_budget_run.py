#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from runtime_utils import dump_json, load_config, resolve_under


def parse_args() -> argparse.Namespace:
    skill_root = Path(__file__).resolve().parents[1]
    config, _warnings = load_config(skill_root)
    defaults = config.get("defaults") or {}
    target_chars = defaults.get("target_chars") or {}
    parser = argparse.ArgumentParser(description="Initialize a hidden nsfc-budget run directory.")
    parser.add_argument("--workdir", required=True, help="User work directory.")
    parser.add_argument("--project-type", choices=sorted((defaults.get("total_budget_wan") or {}).keys()), default=str(defaults.get("project_type") or "general"))
    parser.add_argument("--total-budget-wan", type=float)
    parser.add_argument("--target-chars", type=int, default=int(target_chars.get("recommended_default") or 900))
    parser.add_argument("--template-id", default=str(defaults.get("template_id") or "01"))
    parser.add_argument("--output-dirname", default=str(defaults.get("output_dirname") or "budget_output"))
    parser.add_argument("--material", action="append", default=[], help="Material file or directory to snapshot.")
    return parser.parse_args()


def ensure_directory(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def unique_path(path: Path) -> Path:
    if not path.exists():
        return path
    stem = path.stem
    suffix = path.suffix
    counter = 2
    while True:
        candidate = path.with_name(f"{stem}_{counter}{suffix}")
        if not candidate.exists():
            return candidate
        counter += 1


def copy_material(source: Path, destination_dir: Path) -> str:
    target = unique_path(destination_dir / source.name)
    if source.is_dir():
        shutil.copytree(source, target)
    else:
        shutil.copy2(source, target)
    return str(target)


def build_spec(args: argparse.Namespace, workdir: Path, run_dir: Path, snapped_materials: list[str], config: dict) -> dict:
    defaults = config.get("defaults") or {}
    total_budget = args.total_budget_wan
    if total_budget is None:
        total_budget = float(((defaults.get("total_budget_wan") or {}).get(args.project_type)) or 0)
    indirect_rate_hint = float((((defaults.get("indirect_rate_hint") or {}).get(args.project_type)) or 0.30))
    return {
        "meta": {
            "project_title": "",
            "project_type": args.project_type,
            "budget_mode": str((config.get("rules") or {}).get("budget_mode_default") or "budget_based"),
            "budget_scope": "to_be_confirmed",
            "requested_total_wan": total_budget,
            "direct_costs_total_wan": None,
            "indirect_costs_wan": None,
            "target_chars_min": max(0, args.target_chars - 100),
            "target_chars_max": args.target_chars + 100,
            "per_section_max_chars": int(defaults.get("per_section_max_chars") or 500),
            "template_id": args.template_id,
            "workdir": str(workdir),
            "output_dirname": args.output_dirname,
            "run_dir": str(run_dir),
            "materials": snapped_materials,
            "notes": "",
        },
        "budget": {
            "equipment_wan": 0.0,
            "business_wan": 0.0,
            "labor_wan": 0.0,
            "transfer_wan": 0.0,
            "other_source_wan": 0.0,
            "requested_total_tolerance_wan": float(defaults.get("requested_total_tolerance_wan") or 1.0),
            "indirect_rate_hint": indirect_rate_hint,
        },
        "sections": {
            "equipment": {"amount_wan": 0.0, "paragraphs": []},
            "business": {"amount_wan": 0.0, "paragraphs": []},
            "labor": {"amount_wan": 0.0, "paragraphs": []},
            "transfer": {"amount_wan": 0.0, "paragraphs": []},
            "other_source": {"amount_wan": 0.0, "paragraphs": []},
        },
        "evidence": {
            "pricing_basis": [],
            "assumptions": [],
            "items_to_confirm": [],
        },
    }


def main() -> int:
    args = parse_args()
    skill_root = Path(__file__).resolve().parents[1]
    config, config_warnings = load_config(skill_root)
    workdir = Path(args.workdir).expanduser().resolve()
    if not workdir.exists() or not workdir.is_dir():
        print(f"[nsfc-budget] workdir does not exist or is not a directory: {workdir}", file=sys.stderr)
        return 2

    try:
        resolve_under(workdir, args.output_dirname, label="output_dirname")
        template_dir = resolve_under(skill_root / "models", args.template_id, label="template_id")
        if not template_dir.exists() or not template_dir.is_dir():
            raise ValueError(f"template_id 对应模板不存在：{args.template_id}")
    except ValueError as exc:
        print(f"[nsfc-budget] {exc}", file=sys.stderr)
        return 2

    intermediate_root = ensure_directory(workdir / str((config.get("defaults") or {}).get("intermediate_dirname") or ".nsfc-budget"))
    run_dir = intermediate_root / f"run_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    ensure_directory(run_dir)
    materials_dir = ensure_directory(run_dir / "materials")
    ensure_directory(run_dir / "logs")
    ensure_directory(run_dir / "build")

    snapped_materials = []
    for raw in args.material:
        source = Path(raw).expanduser().resolve()
        if not source.exists():
            print(f"[nsfc-budget] warning: material not found, skipped: {source}", file=sys.stderr)
            continue
        snapped_materials.append(copy_material(source, materials_dir))

    spec = build_spec(args, workdir, run_dir, snapped_materials, config)
    spec_path = run_dir / "budget_spec.json"
    dump_json(spec_path, spec)

    manifest = {
        "workdir": str(workdir),
        "intermediate_root": str(intermediate_root),
        "run_dir": str(run_dir),
        "materials_dir": str(materials_dir),
        "spec_path": str(spec_path),
        "config_warnings": config_warnings,
    }
    dump_json(run_dir / "run_manifest.json", manifest)
    (intermediate_root / "ACTIVE_RUN.txt").write_text(str(run_dir) + "\n", encoding="utf-8")

    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
