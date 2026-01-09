#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict


DEFAULT_CONFIG: Dict[str, Any] = {
    "skill_info": {
        "name": "nsfc-justification-writer",
        "version": "0.3.0",
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


def get_runs_dir(skill_root: Path, config: Dict[str, Any]) -> Path:
    env_override = os.environ.get("NSFC_JUSTIFICATION_WRITER_RUNS_DIR")
    if env_override:
        p = Path(env_override)
        if not p.is_absolute():
            p = (Path(skill_root) / p).resolve()
        return p.resolve()
    runs_dir = (config.get("workspace", {}) or {}).get("runs_dir", "runs")
    return (Path(skill_root) / str(runs_dir)).resolve()
