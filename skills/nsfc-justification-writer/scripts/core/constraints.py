#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from .config_access import get_int, get_mapping
from .latex_parser import strip_comments
from .reference_validator import parse_cite_keys
from .wordcount import count_cjk_chars


@dataclass(frozen=True)
class PageLimit:
    min_pages: int
    max_pages: int
    recommended: Tuple[int, int]
    warning_threshold: int
    chars_per_page: int


@dataclass(frozen=True)
class RangeLimit:
    min_n: int
    max_n: int


def _constraints_cfg(cfg: Mapping[str, Any]) -> Mapping[str, Any]:
    return get_mapping(cfg, "constraints")


def load_page_limit(cfg: Mapping[str, Any]) -> PageLimit:
    page_cfg = get_mapping(_constraints_cfg(cfg), "page_limit")
    lo = max(0, get_int(page_cfg, "min", 6))
    hi = max(lo, get_int(page_cfg, "max", 10))

    rec_raw = page_cfg.get("recommended", [6, 8])
    if isinstance(rec_raw, Sequence) and len(rec_raw) >= 2:
        try:
            rec_a = int(rec_raw[0])
            rec_b = int(rec_raw[1])
        except (TypeError, ValueError):
            rec_a, rec_b = 6, 8
    else:
        rec_a, rec_b = 6, 8
    rec_lo, rec_hi = (rec_a, rec_b) if rec_a <= rec_b else (rec_b, rec_a)
    rec_lo = max(lo, rec_lo)
    rec_hi = max(rec_lo, min(hi, rec_hi))

    warn = get_int(page_cfg, "warning_threshold", 9)
    warn = max(lo, min(hi, warn))
    cpp = max(100, get_int(page_cfg, "chars_per_page", 1000))

    return PageLimit(
        min_pages=lo,
        max_pages=hi,
        recommended=(rec_lo, rec_hi),
        warning_threshold=warn,
        chars_per_page=cpp,
    )


def load_word_count_limit(cfg: Mapping[str, Any]) -> RangeLimit:
    wc_cfg = get_mapping(_constraints_cfg(cfg), "word_count")
    lo = max(0, get_int(wc_cfg, "min", 8000))
    hi = max(lo, get_int(wc_cfg, "max", 10000))
    return RangeLimit(min_n=lo, max_n=hi)


def load_reference_limit(cfg: Mapping[str, Any]) -> RangeLimit:
    ref_cfg = get_mapping(_constraints_cfg(cfg), "references")
    lo = max(0, get_int(ref_cfg, "min", 30))
    hi = max(lo, get_int(ref_cfg, "max", 50))
    return RangeLimit(min_n=lo, max_n=hi)


def load_opening_limit(cfg: Mapping[str, Any]) -> int:
    opening_cfg = get_mapping(_constraints_cfg(cfg), "opening")
    return max(50, get_int(opening_cfg, "cjk_chars", 300))


def estimate_pages(tex_text: str, *, chars_per_page: int) -> Tuple[int, float]:
    """
    仅用于“预警级”估算：用 cjk_strip_commands 的正文字符数 / chars_per_page 估算页数。
    """
    n = count_cjk_chars(tex_text or "", mode="cjk_strip_commands").cjk_count
    if chars_per_page <= 0:
        return n, 0.0
    pages = float(n) / float(chars_per_page)
    return n, max(0.0, pages)


def classify_range(n: int, *, lo: int, hi: int) -> str:
    if n < lo:
        return "too_few"
    if n > hi:
        return "too_many"
    return "within"


def classify_pages(pages: float, *, rule: PageLimit) -> str:
    rec_lo, rec_hi = rule.recommended
    if pages < float(rule.min_pages):
        return "too_short"
    if pages <= float(rec_hi):
        return "within_recommended"
    if pages <= float(rule.warning_threshold):
        return "within_limit"
    if pages <= float(rule.max_pages):
        return "near_limit"
    return "exceed"


_CMD_WITH_ARG_RE = re.compile(r"\\[a-zA-Z@]+\\*?\s*(?:\[[^\]]*\]\s*)*\{([^{}]*)\}")
_CMD_BARE_RE = re.compile(r"\\[a-zA-Z@]+\\*?")
_WS_RE = re.compile(r"\s+")


def _latex_to_plain_text(tex_text: str) -> str:
    """
    近似 LaTeX -> 纯文本：
    - 去注释
    - 将 \\cmd{...} 替换为 {...} 内部文本（仅处理“无嵌套花括号”的常见情形）
    - 删除剩余 \\cmd
    目的：给启发式规则做关键词命中（非严格解析）。
    """
    t = strip_comments(tex_text or "")
    # 多轮展开：逐步剥离最外层命令，同时保留参数中文
    for _ in range(8):
        new = _CMD_WITH_ARG_RE.sub(lambda m: m.group(1) or "", t)
        if new == t:
            break
        t = new
    t = _CMD_BARE_RE.sub("", t)
    t = t.replace("{", "").replace("}", "")
    t = t.replace("[", "").replace("]", "")
    t = _WS_RE.sub(" ", t)
    return t.strip()


def check_opening(tex_text: str, *, cjk_chars: int) -> Dict[str, Any]:
    """
    启发式开篇检查：
    - 在“开篇 cjk_chars 个中文字符”内同时命中“卡点/局限”与“突破/切入点”两类信号词。
    """
    plain = _latex_to_plain_text(tex_text or "")
    # 提取前 N 个 CJK 字符（保留原顺序）
    cjk = [ch for ch in plain if "\u3400" <= ch <= "\u9fff"]
    head = "".join(cjk[: max(0, int(cjk_chars))])

    gap_keywords = [
        "卡点",
        "瓶颈",
        "局限",
        "不足",
        "挑战",
        "难点",
        "痛点",
        "短板",
        "难以",
        "受限于",
    ]
    breakthrough_keywords = [
        "突破",
        "切入",
        "本项目",
        "本研究",
        "拟解决",
        "提出",
        "针对",
        "创新",
        "关键思路",
        "核心思路",
    ]

    hit_gap = any(k in head for k in gap_keywords)
    hit_break = any(k in head for k in breakthrough_keywords)

    issues: List[str] = []
    if not head:
        issues.append("开篇内容过短：无法完成 300 字直击核心检查")
    if not hit_gap:
        issues.append("开篇未明显点出“领域卡点/局限/瓶颈”（建议用 1-2 句明确指出现有方法受限之处）")
    if not hit_break:
        issues.append("开篇未明显给出“本项目的突破式切入/关键思路”（建议用 1 句指出拟突破的关键切口）")

    return {
        "cjk_chars": int(cjk_chars),
        "head_cjk_len": len(head),
        "ok": bool(head) and hit_gap and hit_break,
        "hit_gap": hit_gap,
        "hit_breakthrough": hit_break,
        "issues": issues,
    }


def count_unique_citations(tex_text: str) -> int:
    return len(set(parse_cite_keys(tex_text or "")))


def describe_constraints_summary(cfg: Mapping[str, Any]) -> str:
    """
    用于 CLI/报告的简短说明（避免到处重复 hardcode）。
    """
    page = load_page_limit(cfg)
    wc = load_word_count_limit(cfg)
    refs = load_reference_limit(cfg)
    return (
        f"页数 {page.min_pages}-{page.max_pages}（推荐 {page.recommended[0]}-{page.recommended[1]}）"
        f"；字数 {wc.min_n}-{wc.max_n}"
        f"；核心文献 {refs.min_n}-{refs.max_n}"
    )
