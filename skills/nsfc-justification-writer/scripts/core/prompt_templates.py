#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

from .config_access import get_mapping

def _missing_prompt_message(name: str) -> str:
    return (
        f"（Prompt 模板缺失：{name}；请检查 `assets/prompts/{name}.txt`（或旧路径 prompts/）"
        f" 或 `config.yaml` 的 `prompts.{name}` 配置）\n"
    )


def _default_skill_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _read_text_if_exists(path: Path) -> Optional[str]:
    try:
        if path.is_file():
            return path.read_text(encoding="utf-8", errors="ignore").strip() + "\n"
    except (OSError, UnicodeError):
        return None
    return None


def _looks_like_path(s: str) -> bool:
    t = (s or "").strip()
    if not t:
        return False
    if "\n" in t or "\r" in t:
        return False
    if t.endswith((".txt", ".md")):
        return True
    # assets/prompts/<name>.txt、prompts/<name>.txt 或任意相对/绝对路径
    return ("/" in t) or ("\\" in t)


def get_prompt(
    *,
    name: str,
    default: str,
    skill_root: Optional[Path] = None,
    config: Optional[Dict[str, Any]] = None,
    variant: Optional[str] = None,
) -> str:
    skill_root = (skill_root or _default_skill_root()).resolve()
    cfg = config or {}
    prompt_cfg = get_mapping(cfg, "prompts")
    override_key = name
    if variant:
        v = str(variant).strip()
        if v:
            override_key = f"{name}_{v}"
            if override_key not in prompt_cfg:
                # 常见：preset=medical/engineering，但用户用 medical_tier2_diagnostic 之类的命名
                override_key = name

    override = prompt_cfg.get(override_key) or prompt_cfg.get(name)
    if isinstance(override, str) and override.strip():
        if _looks_like_path(override):
            p = Path(str(override))
            if not p.is_absolute():
                p = (skill_root / p).resolve()
            txt = _read_text_if_exists(p)
            if txt:
                return txt
        # 允许在 override.yaml / preset.yaml 里直接写多行 prompt
        return override.strip() + "\n"

    # default locations: assets/prompts/<name>.txt (preferred), prompts/<name>.txt (legacy)
    for p in [
        (skill_root / "assets" / "prompts" / f"{name}.txt").resolve(),
        (skill_root / "prompts" / f"{name}.txt").resolve(),
    ]:
        txt = _read_text_if_exists(p)
        if txt:
            return txt
    return default.strip() + "\n"


# Backward-compatible constants (loaded from assets/prompts or prompts/ when present)
TIER2_DIAGNOSTIC_PROMPT = get_prompt(name="tier2_diagnostic", default=_missing_prompt_message("tier2_diagnostic"))
REVIEW_SUGGESTIONS_PROMPT = get_prompt(name="review_suggestions", default=_missing_prompt_message("review_suggestions"))
WRITING_COACH_PROMPT = get_prompt(name="writing_coach", default=_missing_prompt_message("writing_coach"))
