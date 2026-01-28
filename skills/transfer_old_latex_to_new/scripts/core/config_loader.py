#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional


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
    # 预设配置（profiles）
    "profiles": {
        "quick": {
            "description": "快速模式（适合小项目，<20 个文件）",
            "ai": {
                "batch_mode": False,
                "max_workers": 2,
            },
            "cache": {
                "enabled": False,
            },
            "content_optimization": {
                "max_rounds": 3,
            },
        },
        "balanced": {
            "description": "平衡模式（适合中型项目，20-100 个文件）",
            "ai": {
                "batch_mode": True,
                "batch_size": 10,
                "max_workers": 4,
            },
            "cache": {
                "enabled": True,
                "memory_max_size": 1000,
            },
            "content_optimization": {
                "max_rounds": 5,
            },
        },
        "thorough": {
            "description": "精确模式（适合大型项目，>100 个文件）",
            "ai": {
                "batch_mode": True,
                "batch_size": 20,
                "max_workers": 8,
            },
            "cache": {
                "enabled": True,
                "memory_max_size": 2000,
            },
            "content_optimization": {
                "max_rounds": 7,
            },
        },
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
    mapping = config.get("mapping", {}) or {}
    thresholds = (mapping.get("thresholds") or {}) if isinstance(mapping, dict) else {}
    if isinstance(thresholds, dict) and thresholds:
        return MappingThresholds(
            high=float(thresholds.get("high", 0.85)),
            medium=float(thresholds.get("medium", 0.7)),
            low=float(thresholds.get("low", 0.5)),
        )

    mh = config.get("mapping_heuristics", {}) or {}
    return MappingThresholds(
        high=float(mh.get("high_similarity_threshold", 0.85)),
        medium=float(mh.get("medium_similarity_threshold", 0.7)),
        low=float(mh.get("low_similarity_threshold", 0.5)),
    )


def get_runs_dir(skill_root: Path, config: Dict[str, Any]) -> Path:
    runs_dir = (config.get("workspace", {}) or {}).get("runs_dir", "runs")
    return (Path(skill_root) / runs_dir).resolve()


def apply_profile(config: Dict[str, Any], profile_name: Optional[str] = None) -> Dict[str, Any]:
    """
    应用配置预设（profile）

    Args:
        config: 原始配置
        profile_name: 预设名称（quick/balanced/thorough），None 表示不应用

    Returns:
        应用预设后的配置
    """
    if not profile_name:
        return config

    profiles = config.get("profiles", {})
    profile = profiles.get(profile_name, {})

    if not profile:
        return config

    return _deep_merge(config, profile)


def list_profiles(config: Optional[Dict[str, Any]] = None) -> List[str]:
    """
    列出可用的配置预设

    Args:
        config: 配置字典（None 则使用默认配置）

    Returns:
        预设名称列表
    """
    if config is None:
        config = DEFAULT_CONFIG

    profiles = config.get("profiles", {})
    return list(profiles.keys())


def get_profile_description(config: Dict[str, Any], profile_name: str) -> Optional[str]:
    """
    获取预设的描述

    Args:
        config: 配置字典
        profile_name: 预设名称

    Returns:
        预设描述，不存在返回 None
    """
    profiles = config.get("profiles", {})
    profile = profiles.get(profile_name, {})
    return profile.get("description") if isinstance(profile, dict) else None


def load_config_with_profile(
    skill_root: Path,
    profile: Optional[str] = None,
) -> Dict[str, Any]:
    """
    加载配置并应用预设

    Args:
        skill_root: 技能根目录
        profile: 预设名称（可选）

    Returns:
        最终配置
    """
    config = load_config(skill_root)
    return apply_profile(config, profile)
