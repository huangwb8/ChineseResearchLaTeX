#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, Optional


DEFAULT_CONFIG: Dict[str, Any] = {
    "skill_info": {
        "name": "nsfc-justification-writer",
        "version": "0.4.0",
        "template_year": "2026",
        "category": "writing",
    },
    "workspace": {
        "runs_dir": "runs",
    },
    "targets": {
        "justification_tex": "extraTex/1.1.立项依据.tex",
        "related_tex": {
            "research_content": "extraTex/2.1.研究内容.tex",
            "research_foundation": "extraTex/3.1.研究基础.tex",
        },
        "bib_globs": ["references/*.bib", "references/**/*.bib"],
    },
    "structure": {
        "expected_subsubsections": ["研究背景", "国内外研究现状", "现有研究的局限性", "研究切入点"],
        "strict_title_match": True,
        "min_subsubsection_count": 4,
    },
    "quality": {
        "forbidden_phrases": ["国际领先", "国内首次", "世界领先", "填补空白"],
        "avoid_commands": ["\\section", "\\subsection", "\\input", "\\include"],
    },
    "ai": {
        "enabled": True,
        "min_success_rate_to_enable": 0.8,
    },
    "prompts": {
        "intent_parse": "prompts/intent_parse.txt",
        "tier2_diagnostic": "prompts/tier2_diagnostic.txt",
        "review_suggestions": "prompts/review_suggestions.txt",
        "writing_coach": "prompts/writing_coach.txt",
    },
    "references": {
        "allow_missing_citations": False,
    },
    "word_count": {
        "target": 4000,
        "tolerance": 200,
    },
    "terminology": {
        "alias_groups": {
            "研究对象": ["患者", "病例", "受试者", "样本"],
            "准确率": ["准确率", "精确度"],
            "深度学习": ["深度学习", "DL"],
        }
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


def _load_yaml_dict(path: Path) -> Dict[str, Any]:
    try:
        import yaml  # type: ignore
    except Exception:
        return {}
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8", errors="ignore")) or {}
        return raw if isinstance(raw, dict) else {}
    except Exception:
        return {}


def _default_user_override_path() -> Optional[Path]:
    home = Path.home()
    candidates = [
        home / ".config" / "nsfc-justification-writer" / "override.yaml",
        home / ".config" / "nsfc-justification-writer" / "override.yml",
    ]
    return next((p for p in candidates if p.exists() and p.is_file()), None)


def load_config(
    skill_root: Path,
    *,
    preset: Optional[str] = None,
    override_path: Optional[str] = None,
    load_user_override: bool = True,
) -> Dict[str, Any]:
    skill_root = Path(skill_root).resolve()
    config: Dict[str, Any] = dict(DEFAULT_CONFIG)

    config_path = (skill_root / "config.yaml").resolve()
    if config_path.exists():
        config = _deep_merge(config, _load_yaml_dict(config_path))

    if preset:
        preset_path = (skill_root / "config" / "presets" / f"{preset}.yaml").resolve()
        if preset_path.exists():
            config = _deep_merge(config, _load_yaml_dict(preset_path))

    disable_user_override = str(os.environ.get("NSFC_JUSTIFICATION_WRITER_DISABLE_USER_OVERRIDE", "")).strip().lower() in {
        "1",
        "true",
        "yes",
    }
    if load_user_override and (not disable_user_override):
        env_override = os.environ.get("NSFC_JUSTIFICATION_WRITER_OVERRIDE_PATH")
        user_path = Path(env_override).expanduser().resolve() if env_override else _default_user_override_path()
        if user_path and user_path.exists():
            config = _deep_merge(config, _load_yaml_dict(Path(user_path)))

    if override_path:
        p = Path(override_path).expanduser()
        if not p.is_absolute():
            p = (Path.cwd() / p).resolve()
        if p.exists():
            config = _deep_merge(config, _load_yaml_dict(p))

    return config


def get_runs_dir(skill_root: Path, config: Dict[str, Any]) -> Path:
    env_override = os.environ.get("NSFC_JUSTIFICATION_WRITER_RUNS_DIR")
    if env_override:
        p = Path(env_override)
        if not p.is_absolute():
            p = (Path(skill_root) / p).resolve()
        return p.resolve()
    runs_dir = (config.get("workspace", {}) or {}).get("runs_dir", "runs")
    return (Path(skill_root) / str(runs_dir)).resolve()
