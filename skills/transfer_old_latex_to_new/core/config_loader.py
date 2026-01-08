#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional


DEFAULT_CONFIG: Dict[str, Any] = {
    "migration": {
        "max_rounds": 5,
        "min_rounds": 3,
        "convergence_threshold": 0.05,
        "default_strategy": "smart",
        "content_generation": {
            "method": "placeholder",
            "placeholder_text": "\\textbf{[此部分内容需要补充]}",
        },
    },
    "quality_thresholds": {
        "min_similarity": 0.7,
        "min_word_count": 50,
    },
    "compilation": {
        "engine": "xelatex",
        "pass_sequence": ["xelatex", "bibtex", "xelatex", "xelatex"],
        "interaction_mode": "nonstopmode",
        "timeout_per_pass": 120,
        "total_timeout": 600,
    },
    "mapping_heuristics": {
        "title_similarity_weight": 0.4,
        "content_similarity_weight": 0.3,
        "position_proximity_weight": 0.2,
        "structural_pattern_weight": 0.1,
        "high_similarity_threshold": 0.85,
        "medium_similarity_threshold": 0.7,
        "low_similarity_threshold": 0.5,
    },
    "output": {
        "verbose": True,
    },
    "workspace": {
        "runs_dir": "runs",
    },
}


def _deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    merged: Dict[str, Any] = dict(base)
    for key, value in (override or {}).items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def load_config(skill_root: Path) -> Dict[str, Any]:
    config_path = Path(skill_root) / "config.yaml"
    config: Dict[str, Any] = dict(DEFAULT_CONFIG)
    if not config_path.exists():
        return config

    try:
        import yaml  # type: ignore
    except Exception:
        return config

    try:
        raw = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
        if not isinstance(raw, dict):
            return config
        return _deep_merge(config, raw)
    except Exception:
        return config


@dataclass(frozen=True)
class MappingThresholds:
    high: float
    medium: float
    low: float


def get_mapping_thresholds(config: Dict[str, Any]) -> MappingThresholds:
    mh = config.get("mapping_heuristics", {}) or {}
    return MappingThresholds(
        high=float(mh.get("high_similarity_threshold", 0.85)),
        medium=float(mh.get("medium_similarity_threshold", 0.7)),
        low=float(mh.get("low_similarity_threshold", 0.5)),
    )


def get_runs_dir(skill_root: Path, config: Dict[str, Any]) -> Path:
    runs_dir = (config.get("workspace", {}) or {}).get("runs_dir", "runs")
    return (Path(skill_root) / runs_dir).resolve()

