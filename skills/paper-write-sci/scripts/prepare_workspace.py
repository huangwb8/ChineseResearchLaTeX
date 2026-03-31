#!/usr/bin/env python3
from __future__ import annotations

import argparse
from datetime import datetime
import json
import re
import sys
from pathlib import Path

import yaml


def load_config(skill_root: Path) -> dict:
    with (skill_root / "config.yaml").open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def canonical_mode(config: dict, requested: str | None) -> str:
    mode_cfg = config["mode"]
    if not requested:
        return mode_cfg["default"]

    normalized = requested.strip()
    if normalized in mode_cfg["options"]:
        return normalized

    for canonical, aliases in mode_cfg.get("aliases", {}).items():
        if normalized == canonical or normalized in aliases:
            return canonical

    valid = sorted(set(mode_cfg["options"]) | set(sum(mode_cfg.get("aliases", {}).values(), [])))
    raise ValueError(f"unknown mode: {requested}. valid values: {', '.join(valid)}")


def canonical_style(config: dict, requested: str | None) -> str:
    available = {item["name"] for item in config["style"]["available"]}
    chosen = requested or config["style"]["default"]
    if chosen not in available:
        raise ValueError(f"unknown style: {chosen}. valid values: {', '.join(sorted(available))}")
    return chosen


def slugify_topic(config: dict, topic: str | None) -> str:
    topic_cfg = config["runtime_outputs"]["topic_slug"]
    if not topic:
        return topic_cfg["fallback"]

    slug = re.sub(r"[^A-Za-z0-9_-]+", topic_cfg["separator"], topic.strip())
    slug = re.sub(rf"{re.escape(topic_cfg['separator'])}+", topic_cfg["separator"], slug)
    slug = slug.strip(topic_cfg["separator"]).strip("_")
    slug = slug[: topic_cfg["max_length"]].rstrip(topic_cfg["separator"]).rstrip("_")
    return slug or topic_cfg["fallback"]


def resolve_paper_dir(config: dict, paper_dir: str) -> Path:
    path = Path(paper_dir).expanduser().resolve()
    paper_cfg = config["input_validation"]["paper_dir"]
    if paper_cfg.get("must_exist", True) and not path.exists():
        raise ValueError(f"paper_dir does not exist: {path}")
    if paper_cfg.get("must_be_directory", True) and not path.is_dir():
        raise ValueError(f"paper_dir is not a directory: {path}")
    return path


def resolve_reference_materials(config: dict, items: list[str]) -> list[str]:
    ref_cfg = config["input_validation"]["reference_materials"]
    resolved: list[str] = []
    for item in items:
        path = Path(item).expanduser().resolve()
        if ref_cfg.get("must_exist", True) and not path.exists():
            raise ValueError(f"reference material does not exist: {path}")
        if path.is_dir() and not ref_cfg.get("allow_directories", True):
            raise ValueError(f"reference material directory not allowed: {path}")
        if path.is_file() and not ref_cfg.get("allow_files", True):
            raise ValueError(f"reference material file not allowed: {path}")
        resolved.append(str(path))
    return resolved


def safe_relative_path(value: str, *, label: str) -> Path:
    path = Path(value)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError(f"{label} must be a relative path inside the run directory: {value}")
    return path


def allocate_run_dir(hidden_root: Path, pattern: str, timestamp: str) -> tuple[str, Path]:
    run_id = pattern.format(timestamp=timestamp)
    candidate = hidden_root / run_id
    if not candidate.exists():
        return run_id, candidate

    suffix = 2
    while True:
        run_id_with_suffix = f"{run_id}_{suffix}"
        candidate = hidden_root / run_id_with_suffix
        if not candidate.exists():
            return run_id_with_suffix, candidate
        suffix += 1


def legacy_hidden_roots(paper_dir: Path, workspace_cfg: dict) -> list[str]:
    names = workspace_cfg.get("legacy_hidden_dirs")
    if names is None:
        legacy_name = workspace_cfg.get("legacy_hidden_dir")
        names = [legacy_name] if legacy_name else []
    return [str((paper_dir / name).resolve()) for name in names]


def ensure_workspace(skill_root: Path, config: dict, paper_dir: Path, mode: str, style: str, topic: str, refs: list[str]) -> dict:
    workspace_cfg = config["workspace"]
    hidden_root = paper_dir / workspace_cfg["hidden_dir"]
    hidden_root.mkdir(parents=True, exist_ok=True)

    runtime_cfg = config["runtime_outputs"]
    timestamp = datetime.now().strftime(runtime_cfg["timestamp_format"])
    run_id, run_dir = allocate_run_dir(hidden_root, runtime_cfg["run_dir_pattern"], timestamp)
    run_dir.mkdir(parents=True, exist_ok=False)

    for subdir in workspace_cfg.get("subdirs", []):
        (run_dir / subdir).mkdir(parents=True, exist_ok=True)

    plan_dir = paper_dir / runtime_cfg["collaborative_plan_dir"]
    plan_dir.mkdir(parents=True, exist_ok=True)

    manifest_path = run_dir / safe_relative_path(runtime_cfg["runtime_manifest"], label="runtime_manifest")
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    plan_filename = runtime_cfg["collaborative_plan_pattern"].format(topic=topic, timestamp=timestamp, run_id=run_id)
    payload = {
        "paper_dir": str(paper_dir),
        "workspace_root": str(hidden_root),
        "workspace_dir": str(run_dir),
        "legacy_workspace_roots": legacy_hidden_roots(paper_dir, workspace_cfg),
        "run_id": run_id,
        "mode": mode,
        "style": style,
        "topic_slug": topic,
        "timestamp": timestamp,
        "collaborative_plan_dir": str(plan_dir),
        "collaborative_plan_preview": str(plan_dir / plan_filename),
        "analysis_dir": str(run_dir / "analysis"),
        "number_check_dir": str(run_dir / "number-check"),
        "logic_check_dir": str(run_dir / "logic-check"),
        "render_dir": str(run_dir / "render"),
        "reference_materials": refs,
        "script": str((skill_root / config["scripts"]["prepare_workspace"]).resolve()),
    }
    manifest_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prepare paper-write-sci runtime workspace")
    parser.add_argument("--paper-dir", required=True)
    parser.add_argument("--mode")
    parser.add_argument("--style")
    parser.add_argument("--topic")
    parser.add_argument("--reference-material", action="append", default=[])
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    skill_root = Path(__file__).resolve().parents[1]
    config = load_config(skill_root)
    try:
        paper_dir = resolve_paper_dir(config, args.paper_dir)
        mode = canonical_mode(config, args.mode)
        style = canonical_style(config, args.style)
        topic = slugify_topic(config, args.topic)
        references = resolve_reference_materials(config, args.reference_material)
        payload = ensure_workspace(skill_root, config, paper_dir, mode, style, topic, references)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
