#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path


DEFAULT_BUDGETS = {
    "general": 50.0,
    "local": 50.0,
    "youth": 30.0,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Initialize a hidden nsfc-budget run directory.")
    parser.add_argument("--workdir", required=True, help="User work directory.")
    parser.add_argument("--project-type", choices=sorted(DEFAULT_BUDGETS.keys()), default="general")
    parser.add_argument("--total-budget-wan", type=float)
    parser.add_argument("--target-chars", type=int, default=900)
    parser.add_argument("--template-id", default="01")
    parser.add_argument("--output-dirname", default="budget_output")
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


def build_spec(args: argparse.Namespace, workdir: Path, run_dir: Path, snapped_materials: list[str]) -> dict:
    total_budget = args.total_budget_wan
    if total_budget is None:
        total_budget = DEFAULT_BUDGETS[args.project_type]
    return {
        "meta": {
            "project_title": "",
            "project_type": args.project_type,
            "budget_mode": "budget_based",
            "budget_scope": "to_be_confirmed",
            "requested_total_wan": total_budget,
            "direct_costs_total_wan": None,
            "indirect_costs_wan": None,
            "target_chars_min": max(0, args.target_chars - 100),
            "target_chars_max": args.target_chars + 100,
            "per_section_max_chars": 500,
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
            "requested_total_tolerance_wan": 1.0,
            "indirect_rate_hint": 0.30,
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
    workdir = Path(args.workdir).expanduser().resolve()
    if not workdir.exists() or not workdir.is_dir():
        print(f"[nsfc-budget] workdir does not exist or is not a directory: {workdir}", file=sys.stderr)
        return 2

    intermediate_root = ensure_directory(workdir / ".nsfc-budget")
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

    spec = build_spec(args, workdir, run_dir, snapped_materials)
    spec_path = run_dir / "budget_spec.json"
    spec_path.write_text(json.dumps(spec, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    manifest = {
        "workdir": str(workdir),
        "intermediate_root": str(intermediate_root),
        "run_dir": str(run_dir),
        "materials_dir": str(materials_dir),
        "spec_path": str(spec_path),
    }
    (run_dir / "run_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (intermediate_root / "ACTIVE_RUN.txt").write_text(str(run_dir) + "\n", encoding="utf-8")

    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
