#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence


# ═══════════════════════════════════════════════════════════════════════
# 配置单一真相来源（Single Source of Truth）说明：
# config.yaml 是权威配置文件，DEFAULT_CONFIG 仅作为"兜底值"
# 修改配置时，请优先编辑 config.yaml，而非此文件
# ═══════════════════════════════════════════════════════════════════════

DEFAULT_CONFIG: Dict[str, Any] = {
    # 安全关键项：即使 YAML 缺失也必须生效的默认值（避免"空策略"导致任意写入）
    "guardrails": {
        "allowed_write_files": ["extraTex/1.1.立项依据.tex"],
        "forbidden_write_files": ["main.tex", "extraTex/@config.tex"],
        "forbidden_write_globs": ["**/*.cls", "**/*.sty"],
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
    except (ModuleNotFoundError, ImportError):
        return {}, "未安装 PyYAML，已跳过 YAML 配置加载（建议 `pip install pyyaml`）"
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8", errors="ignore")) or {}
        if not isinstance(raw, dict):
            return {}, "YAML 顶层不是 mapping（dict），已忽略"
        return raw, ""
    except (OSError, UnicodeError, ValueError, yaml.YAMLError) as e:  # type: ignore[attr-defined]
        return {}, f"YAML 解析失败（{type(e).__name__}: {e}），已忽略（请检查语法）"


def _default_user_override_path() -> Optional[Path]:
    home = Path.home()
    candidates = [
        home / ".config" / "nsfc-justification-writer" / "override.yaml",
        home / ".config" / "nsfc-justification-writer" / "override.yml",
    ]
    return next((p for p in candidates if p.exists() and p.is_file()), None)


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


def _is_nonempty_seq_str(x: Any) -> bool:
    return isinstance(x, list) and all(isinstance(it, str) and str(it).strip() for it in x) and len(x) > 0


def _looks_like_path(s: str) -> bool:
    t = (s or "").strip()
    if not t:
        return False
    if "\n" in t or "\r" in t:
        return False
    if t.endswith((".txt", ".md", ".yaml", ".yml")):
        return True
    return ("/" in t) or ("\\" in t)


def _resolve_prompt_path(skill_root: Path, value: str) -> Optional[Path]:
    v = str(value or "").strip()
    if not v or (not _looks_like_path(v)):
        return None
    p = Path(v).expanduser()
    if not p.is_absolute():
        p = (Path(skill_root).resolve() / p).resolve()
    return p.resolve()


def _collect_config_warnings(*, skill_root: Path, config: Dict[str, Any]) -> List[str]:
    warnings: List[str] = []
    prompts = config.get("prompts", {})
    if isinstance(prompts, dict):
        for k, v in prompts.items():
            if not isinstance(k, str):
                continue
            if not isinstance(v, str) or (not v.strip()):
                continue
            p = _resolve_prompt_path(skill_root, v)
            if p is None:
                continue
            # 仅做风险提示：外部路径内容可能被拼入 prompt（若上层注入 responder）
            if Path(v).expanduser().is_absolute():
                warnings.append(f"prompts.{k} 使用绝对路径：{v}（注意：该文件内容可能被拼入 prompt）")
            try:
                p.relative_to(Path(skill_root).resolve())
            except ValueError:
                warnings.append(f"prompts.{k} 指向 skill_root 之外：{v} -> {p}（注意：该文件内容可能被拼入 prompt）")
    return warnings


def _harden_guardrails(*, config: Dict[str, Any], meta: Dict[str, Any]) -> None:
    """
    安全关键项加固：
    - guardrails 必须存在且为 dict
    - allowed_write_files 不允许为空；若无效则回退到 DEFAULT_CONFIG（并给出 warning）
    - forbidden_write_files/forbidden_write_globs 若无效也回退到 DEFAULT_CONFIG（避免误放开 .cls/.sty 等）
    """
    default_guard = DEFAULT_CONFIG.get("guardrails", {})
    if not isinstance(default_guard, dict):
        default_guard = {}

    guard = config.get("guardrails")
    if not isinstance(guard, dict):
        config["guardrails"] = dict(default_guard)
        meta.setdefault("warnings", []).append("guardrails 非 dict（或被置空），已回退到安全默认值（白名单写入保持启用）")
        return

    allowed = guard.get("allowed_write_files")
    if not _is_nonempty_seq_str(allowed):
        guard["allowed_write_files"] = list(default_guard.get("allowed_write_files", ["extraTex/1.1.立项依据.tex"]))
        meta.setdefault("warnings", []).append(
            "guardrails.allowed_write_files 为空/无效，已回退到安全默认值（避免白名单失效）"
        )

    forbidden_files = guard.get("forbidden_write_files")
    if not _is_seq_str(forbidden_files):
        guard["forbidden_write_files"] = list(default_guard.get("forbidden_write_files", []))
        meta.setdefault("warnings", []).append("guardrails.forbidden_write_files 无效，已回退到安全默认值")

    forbidden_globs = guard.get("forbidden_write_globs")
    if not _is_seq_str(forbidden_globs):
        guard["forbidden_write_globs"] = list(default_guard.get("forbidden_write_globs", []))
        meta.setdefault("warnings", []).append("guardrails.forbidden_write_globs 无效，已回退到安全默认值")


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

    style = config.get("style", {})
    if style is not None and not isinstance(style, dict):
        err("style 必须是 dict")
    elif isinstance(style, dict) and style:
        mode = str(style.get("mode", "theoretical")).strip().lower()
        if mode not in {"theoretical", "mixed", "engineering"}:
            err("style.mode 必须是 theoretical|mixed|engineering")

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

    limits = config.get("limits", {})
    if limits is not None and not isinstance(limits, dict):
        err("limits 必须是 dict")
    elif isinstance(limits, dict):
        if "max_file_size_mb" in limits and not isinstance(limits.get("max_file_size_mb"), int):
            err("limits.max_file_size_mb 必须是 int")
        if "ai_max_input_chars" in limits and not isinstance(limits.get("ai_max_input_chars"), int):
            err("limits.ai_max_input_chars 必须是 int")
        if "writing_coach_preview_chars" in limits and not isinstance(limits.get("writing_coach_preview_chars"), int):
            err("limits.writing_coach_preview_chars 必须是 int")
        if "word_target" in limits:
            wt = limits.get("word_target")
            if wt is not None and not isinstance(wt, dict):
                err("limits.word_target 必须是 dict")
            elif isinstance(wt, dict):
                if "min" in wt and not isinstance(wt.get("min"), int):
                    err("limits.word_target.min 必须是 int")
                if "max" in wt and not isinstance(wt.get("max"), int):
                    err("limits.word_target.max 必须是 int")

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

    guardrails = config.get("guardrails")
    if not isinstance(guardrails, dict):
        err("guardrails 必须是 dict（安全关键项）")
    else:
        if not _is_nonempty_seq_str(guardrails.get("allowed_write_files")):
            err("guardrails.allowed_write_files 必须是非空字符串列表（安全关键项：写入白名单不可为空）")
        if not _is_seq_str(guardrails.get("forbidden_write_files", [])):
            err("guardrails.forbidden_write_files 必须是字符串列表")
        if not _is_seq_str(guardrails.get("forbidden_write_globs", [])):
            err("guardrails.forbidden_write_globs 必须是字符串列表")

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
            if not isinstance(dims, dict):
                err("terminology.dimensions 必须是 dict")
            elif dims:
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

    # 第三方约束：仅做类型校验（不要求必须存在）
    constraints = config.get("constraints")
    if constraints is not None and not isinstance(constraints, dict):
        err("constraints 必须是 dict")
    elif isinstance(constraints, dict):
        page = constraints.get("page_limit")
        if page is not None and not isinstance(page, dict):
            err("constraints.page_limit 必须是 dict")
        elif isinstance(page, dict):
            for k in ["min", "max", "warning_threshold", "chars_per_page"]:
                if k in page and not isinstance(page.get(k), int):
                    err(f"constraints.page_limit.{k} 必须是 int")
            if "recommended" in page:
                rec = page.get("recommended")
                if not (isinstance(rec, list) and len(rec) >= 2 and all(isinstance(x, int) for x in rec[:2])):
                    err("constraints.page_limit.recommended 必须是 [int, int]")

        wc = constraints.get("word_count")
        if wc is not None and not isinstance(wc, dict):
            err("constraints.word_count 必须是 dict")
        elif isinstance(wc, dict):
            for k in ["min", "max"]:
                if k in wc and not isinstance(wc.get(k), int):
                    err(f"constraints.word_count.{k} 必须是 int")

        refs = constraints.get("references")
        if refs is not None and not isinstance(refs, dict):
            err("constraints.references 必须是 dict")
        elif isinstance(refs, dict):
            for k in ["min", "max"]:
                if k in refs and not isinstance(refs.get(k), int):
                    err(f"constraints.references.{k} 必须是 int")

        opening = constraints.get("opening")
        if opening is not None and not isinstance(opening, dict):
            err("constraints.opening 必须是 dict")
        elif isinstance(opening, dict):
            if "cjk_chars" in opening and not isinstance(opening.get("cjk_chars"), int):
                err("constraints.opening.cjk_chars 必须是 int")

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
        # 新规范：assets/presets/<name>.yaml（优先）
        # 兼容旧路径：config/presets/<name>.yaml
        preset_name = str(preset).strip()
        preset_candidates = [
            (skill_root / "assets" / "presets" / f"{preset_name}.yaml").resolve(),
            (skill_root / "config" / "presets" / f"{preset_name}.yaml").resolve(),
        ]
        preset_path = next((p for p in preset_candidates if p.exists()), preset_candidates[0])
        _merge_yaml(preset_path, label=f"preset={preset_name}")
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

    meta["warnings"].extend(_collect_config_warnings(skill_root=skill_root, config=config))
    config["_config_loader"] = meta

    disable_validation = str(os.environ.get("NSFC_JUSTIFICATION_WRITER_DISABLE_CONFIG_VALIDATION", "")).strip().lower() in {
        "1",
        "true",
        "yes",
    }
    # 无 PyYAML：只能运行 DEFAULT_CONFIG（至少保证 guardrails 生效），跳过强校验避免“承诺降级但实际失败”
    if not bool(meta.get("yaml_available", True)):
        disable_validation = True
        meta["warnings"].append("未安装 PyYAML：已跳过配置强校验（当前仅保证 guardrails 等安全兜底生效）")

    if not disable_validation:
        errs = validate_config(skill_root=skill_root, config=config)
        if errs:
            raise ValueError("配置校验失败：\n- " + "\n- ".join(errs))

    # 即使用户显式关闭校验，也不允许安全关键项被“置空/移除”
    _harden_guardrails(config=config, meta=meta)

    return config


def get_runs_dir(skill_root: Path, config: Dict[str, Any]) -> Path:
    env_override = os.environ.get("NSFC_JUSTIFICATION_WRITER_RUNS_DIR")
    if env_override:
        p = Path(env_override)
        if not p.is_absolute():
            p = (Path(skill_root) / p).resolve()
        return p.resolve()
    workspace = config.get("workspace", {})
    workspace = workspace if isinstance(workspace, dict) else {}
    runs_dir = workspace.get("runs_dir", "tests/_artifacts/runs")
    return (Path(skill_root) / str(runs_dir)).resolve()
