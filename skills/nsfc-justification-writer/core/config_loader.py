#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence


DEFAULT_CONFIG: Dict[str, Any] = {
    "skill_info": {
        "name": "nsfc-justification-writer",
        "version": "0.6.0",
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
        "mode": "auto",
        "ai": {
            "enabled": True,
            "max_chars": 20000,
        },
        "dimensions": {
            "研究对象": {"研究对象": ["患者", "病例", "受试者", "样本"]},
            "指标": {"准确率": ["准确率", "精确度"]},
            "术语": {"深度学习": ["深度学习", "DL"]},
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


def _looks_like_path(s: str) -> bool:
    t = (s or "").strip()
    if not t:
        return False
    if "\n" in t or "\r" in t:
        return False
    if t.endswith((".txt", ".md", ".yaml", ".yml")):
        return True
    return ("/" in t) or ("\\" in t)

def _is_seq_str(x: Any) -> bool:
    return isinstance(x, list) and all(isinstance(it, str) for it in x)


def _is_alias_groups(x: Any) -> bool:
    if not isinstance(x, dict):
        return False
    for k, v in x.items():
        if not isinstance(k, str):
            return False
        if not _is_seq_str(v):
            return False
    return True


def validate_config(*, skill_root: Path, config: Dict[str, Any]) -> List[str]:
    """
    轻量配置校验：只校验关键字段与类型，不阻止用户加入额外键。
    返回错误列表（空列表表示通过）。
    """
    errors: List[str] = []

    def err(msg: str) -> None:
        errors.append(msg)

    skill_info = config.get("skill_info")
    if not isinstance(skill_info, dict):
        err("skill_info 必须是 dict")
    else:
        if not isinstance(skill_info.get("name"), str) or not str(skill_info.get("name")).strip():
            err("skill_info.name 必须是非空字符串")
        if not isinstance(skill_info.get("version"), str) or not str(skill_info.get("version")).strip():
            err("skill_info.version 必须是非空字符串")

    targets = config.get("targets")
    if not isinstance(targets, dict):
        err("targets 必须是 dict")
    else:
        if not isinstance(targets.get("justification_tex"), str) or not str(targets.get("justification_tex")).strip():
            err("targets.justification_tex 必须是非空字符串")
        bib_globs = targets.get("bib_globs", [])
        if not _is_seq_str(bib_globs):
            err("targets.bib_globs 必须是字符串列表")

    structure = config.get("structure")
    if not isinstance(structure, dict):
        err("structure 必须是 dict")
    else:
        expected = structure.get("expected_subsubsections", [])
        if not _is_seq_str(expected) or not expected:
            err("structure.expected_subsubsections 必须是非空字符串列表")
        m = structure.get("min_subsubsection_count")
        if not isinstance(m, int) or m <= 0:
            err("structure.min_subsubsection_count 必须是正整数")

    quality = config.get("quality")
    if not isinstance(quality, dict):
        err("quality 必须是 dict")
    else:
        if not _is_seq_str(quality.get("forbidden_phrases", [])):
            err("quality.forbidden_phrases 必须是字符串列表")
        if not _is_seq_str(quality.get("avoid_commands", [])):
            err("quality.avoid_commands 必须是字符串列表")

    wc = config.get("word_count", {})
    if not isinstance(wc, dict):
        err("word_count 必须是 dict")
    else:
        if not isinstance(wc.get("target", 4000), int):
            err("word_count.target 必须是整数")
        if not isinstance(wc.get("tolerance", 200), int):
            err("word_count.tolerance 必须是整数")

    ai = config.get("ai", {})
    if not isinstance(ai, dict):
        err("ai 必须是 dict")
    else:
        if not isinstance(ai.get("enabled", True), bool):
            err("ai.enabled 必须是 bool")
        msr = ai.get("min_success_rate_to_enable", 0.8)
        if not isinstance(msr, (int, float)) or not (0.0 <= float(msr) <= 1.0):
            err("ai.min_success_rate_to_enable 必须在 0~1 之间")

    prompts = config.get("prompts", {})
    if prompts is not None and not isinstance(prompts, dict):
        err("prompts 必须是 dict")
    elif isinstance(prompts, dict):
        for k, v in prompts.items():
            if not isinstance(v, str) or not v.strip():
                err(f"prompts.{k} 必须是非空字符串")
                continue
            # 允许：1) 文件路径；2) 直接写多行 prompt（用于 override/preset）
            if _looks_like_path(v):
                p = Path(v)
                if not p.is_absolute():
                    maybe = (Path(skill_root).resolve() / p).resolve()
                    if not maybe.exists():
                        err(f"prompts.{k} 路径不存在：{v}")

    terminology = config.get("terminology", {})
    if terminology is not None and not isinstance(terminology, dict):
        err("terminology 必须是 dict")
    elif isinstance(terminology, dict):
        mode = str(terminology.get("mode", "auto")).strip().lower()
        if mode not in {"auto", "ai", "legacy"}:
            err("terminology.mode 必须是 auto|ai|legacy")
        ai_cfg = terminology.get("ai", {})
        if ai_cfg is not None and not isinstance(ai_cfg, dict):
            err("terminology.ai 必须是 dict")
        elif isinstance(ai_cfg, dict):
            if "enabled" in ai_cfg and not isinstance(ai_cfg.get("enabled"), bool):
                err("terminology.ai.enabled 必须是 bool")
            if "max_chars" in ai_cfg and not isinstance(ai_cfg.get("max_chars"), int):
                err("terminology.ai.max_chars 必须是 int")
        if "dimensions" in terminology:
            dims = terminology.get("dimensions")
            if not isinstance(dims, dict) or not dims:
                err("terminology.dimensions 必须是非空 dict")
            else:
                for dim_name, groups in dims.items():
                    if not isinstance(dim_name, str) or not dim_name.strip():
                        err("terminology.dimensions 的 key 必须是非空字符串")
                        continue
                    if not _is_alias_groups(groups):
                        err(f"terminology.dimensions.{dim_name} 必须是 dict[str, list[str]]")
        elif "alias_groups" in terminology:
            if not _is_alias_groups(terminology.get("alias_groups")):
                err("terminology.alias_groups 必须是 dict[str, list[str]]")

    return errors


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
        config["active_preset"] = str(preset)
    else:
        config["active_preset"] = ""

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

    disable_validation = str(os.environ.get("NSFC_JUSTIFICATION_WRITER_DISABLE_CONFIG_VALIDATION", "")).strip().lower() in {
        "1",
        "true",
        "yes",
    }
    if not disable_validation:
        errs = validate_config(skill_root=skill_root, config=config)
        if errs:
            raise ValueError("配置校验失败：\n- " + "\n- ".join(errs))

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
