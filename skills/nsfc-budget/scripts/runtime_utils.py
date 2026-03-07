#!/usr/bin/env python3

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Tuple


DEFAULT_CONFIG: Dict[str, Any] = {
    "defaults": {
        "template_id": "01",
        "output_dirname": "budget_output",
        "intermediate_dirname": ".nsfc-budget",
        "project_type": "general",
        "total_budget_wan": {"general": 50, "local": 50, "youth": 30},
        "target_chars": {"recommended_min": 800, "recommended_max": 1000, "recommended_default": 900},
        "per_section_max_chars": 500,
        "indirect_rate_hint": {"general": 0.30, "local": 0.30, "youth": 0.30},
        "requested_total_tolerance_wan": 1.0,
        "compile_runs": 2,
    },
    "rules": {
        "require_workdir": True,
        "project_types": ["general", "local", "youth"],
        "budget_mode_default": "budget_based",
        "budget_modes": ["budget_based", "package_based", "historical_budget_based"],
        "budget_scopes": ["direct", "total", "to_be_confirmed"],
        "allowed_latex_commands": ["linebreak", "BudgetBold"],
        "zero_text": {
            "equipment": "本项目不列支设备费。",
            "business": "本项目不列支业务费。",
            "labor": "本项目不列支劳务费。",
            "transfer": "本项目无合作研究转拨资金。",
            "other_source": "本项目无其他来源资金。",
        },
    },
    "validation": {
        "equipment_ratio_warning": 0.50,
        "require_section_text_when_amount_positive": True,
    },
    "output": {
        "latex_entry": "budget.tex",
        "pdf_name": "budget.pdf",
        "section_files": {
            "equipment": "extraTex/1.1.设备费.tex",
            "business": "extraTex/1.2.业务费.tex",
            "labor": "extraTex/1.3.劳务费.tex",
            "transfer": "extraTex/2.1.合作研究转拨资金.tex",
            "other_source": "extraTex/3.1.其他来源资金.tex",
        },
    },
}


def merge_dict(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    merged: Dict[str, Any] = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = merge_dict(merged[key], value)
        else:
            merged[key] = value
    return merged


def load_yaml_file(path: Path) -> Tuple[Dict[str, Any], List[str]]:
    warnings: List[str] = []
    if not path.exists():
        return {}, [f"YAML 文件不存在：{path}"]
    try:
        import yaml  # type: ignore

        loaded = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        if not isinstance(loaded, dict):
            warnings.append(f"YAML 解析结果不是 dict：{path}")
            return {}, warnings
        return loaded, warnings
    except ImportError:
        warnings.append("缺少 PyYAML，回退到默认配置")
    except Exception as exc:
        warnings.append(f"读取 YAML 失败，回退到默认配置：{exc}")
    return {}, warnings


def load_config(skill_root: Path) -> Tuple[Dict[str, Any], List[str]]:
    loaded, warnings = load_yaml_file(skill_root / "config.yaml")
    return merge_dict(DEFAULT_CONFIG, loaded), warnings


def load_template_meta(template_dir: Path) -> Tuple[Dict[str, Any], List[str]]:
    return load_yaml_file(template_dir / ".template.yaml")


def safe_rel_path(raw: str, *, label: str) -> Path:
    path = Path(raw)
    if not raw or raw.strip() == "":
        raise ValueError(f"{label} 不能为空")
    if path.is_absolute():
        raise ValueError(f"{label} 不能是绝对路径：{raw}")
    if any(part in {"..", "", "."} for part in path.parts):
        raise ValueError(f"{label} 不能包含越界路径段：{raw}")
    return path


def resolve_under(base: Path, relative: str, *, label: str) -> Path:
    rel = safe_rel_path(relative, label=label)
    resolved = (base / rel).resolve()
    try:
        resolved.relative_to(base.resolve())
    except ValueError as exc:
        raise ValueError(f"{label} 解析后越界：{relative} -> {resolved}") from exc
    return resolved


def paths_overlap(first: Path, second: Path) -> bool:
    first_resolved = first.resolve()
    second_resolved = second.resolve()
    try:
        first_resolved.relative_to(second_resolved)
        return True
    except ValueError:
        pass
    try:
        second_resolved.relative_to(first_resolved)
        return True
    except ValueError:
        return False


def resolve_output_dir(workdir: Path, output_dirname: str, intermediate_dirname: str, *, label: str = "output_dirname") -> Path:
    output_dir = resolve_under(workdir, output_dirname, label=label)
    workdir_resolved = workdir.resolve()
    if output_dir == workdir_resolved:
        raise ValueError(f"{label} 不能指向工作目录根路径：{output_dirname}")

    intermediate_root = resolve_under(workdir, intermediate_dirname, label="intermediate_dirname")
    if paths_overlap(output_dir, intermediate_root):
        raise ValueError(
            f"{label} 不能与隐藏工作区 {intermediate_dirname} 重叠：{output_dirname}"
        )
    return output_dir


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def dump_json(path: Path, data: Dict[str, Any]) -> None:
    ensure_parent(path)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
