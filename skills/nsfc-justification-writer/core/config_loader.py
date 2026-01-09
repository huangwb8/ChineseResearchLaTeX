#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence


DEFAULT_CONFIG: Dict[str, Any] = {
    "skill_info": {
        "name": "nsfc-justification-writer",
        "version": "0.7.0",
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
        "recommended_subsubsections": ["研究背景", "国内外研究现状", "现有研究的局限性", "研究切入点"],
        "strict_title_match": False,
        "min_subsubsection_count": 4,
        "enable_dimension_coverage_check": True,
    },
    # 安全关键项：即使 YAML 依赖缺失，也必须默认生效（避免“空策略”导致任意写入）。
    "guardrails": {
        "allowed_write_files": ["extraTex/1.1.立项依据.tex"],
        "forbidden_write_files": ["main.tex", "extraTex/@config.tex"],
        "forbidden_write_globs": ["**/*.cls", "**/*.sty"],
    },
    "latex_style_contract": {
        "keep_commands": ["\\justifying", "\\indent"],
        "avoid_commands": ["\\section", "\\subsection", "\\input", "\\include"],
    },
    "quality_contract": {
        "must_include": [
            "价值与必要性（为什么要做）",
            "国内外现状与不足（现有不足）",
            "科学问题/核心假说（切入点）",
            "本项目贡献与小结（承上启下）",
        ],
        "avoid": [
            "无法核验的绝对表述（例如“国内首次”“国际领先”）",
            "幻觉引用（未核验即给出作者/年份/期刊/DOI）",
        ],
    },
    "quality": {
        "high_risk_examples": ["国际领先", "国内首次", "世界领先", "填补空白"],
        "avoid_commands": ["\\section", "\\subsection", "\\input", "\\include"],
        "strict_mode": False,
        "enable_ai_judgment": True,
        "ai_judgment_mode": "semantic",
    },
    "ai": {
        "enabled": True,
        "tier2_chunk_size": 12000,
        "tier2_max_chunks": 20,
        "cache_dir": ".cache/ai",
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
        "_note": "4000 字为示例兜底值；实际目标字数优先从用户意图/信息表/学科预设动态解析",
        "mode": "cjk_only",
    },
    "terminology": {
        "mode": "auto",
        "enable_ai_semantic_check": True,
        "ai_mode": "auto",
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
    "writing_coach": {
        "enable_ai_stage_inference": True,
        "ai_inference_mode": "auto",
        "fallback_rules": {"draft_threshold_ratio": 0.4, "draft_min_chars": 600},
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


def _load_yaml_dict_with_warning(path: Path) -> tuple[Dict[str, Any], str]:
    try:
        import yaml  # type: ignore
    except Exception:
        return {}, "未安装 PyYAML，已跳过 YAML 配置加载（建议 `pip install pyyaml`）"
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8", errors="ignore")) or {}
        if not isinstance(raw, dict):
            return {}, "YAML 顶层不是 mapping（dict），已忽略"
        return raw, ""
    except Exception:
        return {}, "YAML 解析失败，已忽略（请检查语法）"


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
        expected = structure.get("expected_subsubsections", None)
        recommended = structure.get("recommended_subsubsections", None)
        if (expected is None) and (recommended is None):
            err("structure.expected_subsubsections 或 structure.recommended_subsubsections 必须至少存在一个")
        else:
            seq = recommended if recommended is not None else expected
            if not _is_seq_str(seq) or not seq:
                err("structure.(expected_subsubsections|recommended_subsubsections) 必须是非空字符串列表")
        m = structure.get("min_subsubsection_count")
        if not isinstance(m, int) or m <= 0:
            err("structure.min_subsubsection_count 必须是正整数")

    quality = config.get("quality")
    if not isinstance(quality, dict):
        err("quality 必须是 dict")
    else:
        if "forbidden_phrases" in quality and not _is_seq_str(quality.get("forbidden_phrases", [])):
            err("quality.forbidden_phrases 必须是字符串列表")
        if "high_risk_examples" in quality and not _is_seq_str(quality.get("high_risk_examples", [])):
            err("quality.high_risk_examples 必须是字符串列表")
        if not _is_seq_str(quality.get("avoid_commands", [])):
            err("quality.avoid_commands 必须是字符串列表")
        if "strict_mode" in quality and not isinstance(quality.get("strict_mode"), bool):
            err("quality.strict_mode 必须是 bool")
        if "enable_ai_judgment" in quality and not isinstance(quality.get("enable_ai_judgment"), bool):
            err("quality.enable_ai_judgment 必须是 bool")
        if "ai_judgment_mode" in quality and not isinstance(quality.get("ai_judgment_mode"), str):
            err("quality.ai_judgment_mode 必须是 str")

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
        if "tier2_chunk_size" in ai and not isinstance(ai.get("tier2_chunk_size"), int):
            err("ai.tier2_chunk_size 必须是 int")
        if "tier2_max_chunks" in ai and not isinstance(ai.get("tier2_max_chunks"), int):
            err("ai.tier2_max_chunks 必须是 int")
        if "cache_dir" in ai and not isinstance(ai.get("cache_dir"), str):
            err("ai.cache_dir 必须是 str")

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
        if mode not in {"auto", "ai", "legacy", "semantic_only", "legacy_only"}:
            err("terminology.mode 必须是 auto|ai|legacy|semantic_only|legacy_only")
        if "enable_ai_semantic_check" in terminology and not isinstance(terminology.get("enable_ai_semantic_check"), bool):
            err("terminology.enable_ai_semantic_check 必须是 bool")
        if "ai_mode" in terminology and not isinstance(terminology.get("ai_mode"), str):
            err("terminology.ai_mode 必须是 str")
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

    writing_coach = config.get("writing_coach")
    if writing_coach is not None and not isinstance(writing_coach, dict):
        err("writing_coach 必须是 dict")
    elif isinstance(writing_coach, dict):
        if "enable_ai_stage_inference" in writing_coach and not isinstance(writing_coach.get("enable_ai_stage_inference"), bool):
            err("writing_coach.enable_ai_stage_inference 必须是 bool")
        if "ai_inference_mode" in writing_coach and not isinstance(writing_coach.get("ai_inference_mode"), str):
            err("writing_coach.ai_inference_mode 必须是 str")
        if "fallback_rules" in writing_coach and not isinstance(writing_coach.get("fallback_rules"), dict):
            err("writing_coach.fallback_rules 必须是 dict")

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
    meta: Dict[str, Any] = {"yaml_available": True, "loaded_files": [], "warnings": []}

    def _merge_yaml(path: Path, *, label: str) -> None:
        nonlocal config, meta
        if not path.exists():
            return
        data, warn = _load_yaml_dict_with_warning(path)
        if warn:
            meta["warnings"].append(f"{label}: {warn} -> {path}")
            if "未安装 PyYAML" in warn:
                meta["yaml_available"] = False
            return
        config = _deep_merge(config, data)
        meta["loaded_files"].append(str(path))

    config_path = (skill_root / "config.yaml").resolve()
    _merge_yaml(config_path, label="repo config.yaml")

    if preset:
        preset_path = (skill_root / "config" / "presets" / f"{preset}.yaml").resolve()
        _merge_yaml(preset_path, label=f"preset={preset}")
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
            _merge_yaml(Path(user_path), label="user override")

    if override_path:
        p = Path(override_path).expanduser()
        if not p.is_absolute():
            p = (Path.cwd() / p).resolve()
        _merge_yaml(p, label="--override")

    config["_config_loader"] = meta

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
