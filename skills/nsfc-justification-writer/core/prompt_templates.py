#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

from .config_access import get_mapping
DEFAULT_TIER2_DIAGNOSTIC_PROMPT = """\
你是 NSFC 立项依据"语义诊断器"。请基于以下 LaTeX 文本，输出诊断要点（JSON）：

字段：
- logic: 逻辑连贯性问题（列表）
- terminology: 术语/缩写不一致问题（列表）
- evidence: 证据不足/不可量化陈述（列表）
- suggestions: 3-6 条可执行修改建议（列表）

要求：
- 只输出 JSON
- 不生成新的引用；若需要引用，请提示"需用户提供 DOI/链接或走 nsfc-bib-manager 核验"

LaTeX 文本：
{tex}
"""


DEFAULT_REVIEW_SUGGESTIONS_PROMPT = """\
你是 NSFC 立项依据的"评审人视角质疑生成器"。

输入：
- dod_checklist: 验收清单（要点）
- tier1: 硬编码诊断结果（结构/引用/字数/不可核验表述）
- tex: 立项依据正文（可截断）

任务：输出 markdown（不要写 LaTeX），包含两部分：
1) 评审人可能会问的 8-12 个问题（每条可直接用于修改）
2) 对应的 8-12 条可执行修改建议（尽量给到"改哪里/怎么改/验证标准"）

约束：
- 不要杜撰引用与 DOI；如需要引用，用"需补充 DOI/链接或走 nsfc-bib-manager 核验"
- 避免绝对化表述（国际领先/国内首次等）

dod_checklist:
{dod_checklist}

tier1(json):
{tier1_json}

tex:
{tex}
"""


DEFAULT_WRITING_COACH_PROMPT = """\
你是 NSFC 立项依据的"渐进式写作教练"。

目标：帮助用户用最小压力完成 1.1 立项依据，从"骨架 → 段落 → 逻辑闭环 → 润色 → 验收"逐步推进。

输入：
- stage: skeleton|draft|revise|polish|final（或 auto）
- info_form: 用户已提供的信息（可能不完整）
- tier1: 结构/引用/字数/质量硬编码诊断
- term_matrix: 跨章节术语一致性矩阵（可为空）
- tex: 当前立项依据（可为空）

输出：markdown，格式固定为：
## 当前阶段判断
一句话说明当前处于哪个阶段以及原因。

## 本轮只做三件事
1) ...
2) ...
3) ...

## 需要你补充/确认的问题（不超过 8 个）
- ...

## 下一步可直接复制的写作提示词
给出 1 段可复制的提示词，用于让写作助手生成/修改某个 \\subsubsection 的正文（必须强调：不新增引用/引用先核验）。

约束：
- 永远先保证结构不被破坏
- 永远优先可核验性与术语一致性
"""


def _default_skill_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _read_text_if_exists(path: Path) -> Optional[str]:
    try:
        if path.is_file():
            return path.read_text(encoding="utf-8", errors="ignore").strip() + "\n"
    except Exception:
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
    # prompts/<name>.txt 或任意相对/绝对路径
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

    # default location: prompts/<name>.txt
    txt = _read_text_if_exists((skill_root / "prompts" / f"{name}.txt").resolve())
    if txt:
        return txt
    return default.strip() + "\n"


# Backward-compatible constants (loaded from prompts/ when present)
TIER2_DIAGNOSTIC_PROMPT = get_prompt(name="tier2_diagnostic", default=DEFAULT_TIER2_DIAGNOSTIC_PROMPT)
REVIEW_SUGGESTIONS_PROMPT = get_prompt(name="review_suggestions", default=DEFAULT_REVIEW_SUGGESTIONS_PROMPT)
WRITING_COACH_PROMPT = get_prompt(name="writing_coach", default=DEFAULT_WRITING_COACH_PROMPT)
