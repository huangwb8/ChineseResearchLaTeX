#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

from typing import Any, Dict, Mapping

from .constraints import (
    check_opening,
    classify_pages,
    classify_range,
    count_unique_citations,
    estimate_pages,
    load_opening_limit,
    load_page_limit,
    load_reference_limit,
    load_word_count_limit,
)


def snapshot_third_party_constraints(*, tex_text: str, config: Mapping[str, Any]) -> Dict[str, Any]:
    """
    将“第三方瘦身提质约束”落到可机器读的 snapshot，供 diagnose/review/coach 展示与预警。
    注意：本模块只做诊断/预警，不作为写入阻断。
    """
    page_rule = load_page_limit(config)
    stripped_wc, pages = estimate_pages(tex_text, chars_per_page=page_rule.chars_per_page)
    page_status = classify_pages(pages, rule=page_rule)

    word_rule = load_word_count_limit(config)
    word_range_status = classify_range(stripped_wc, lo=word_rule.min_n, hi=word_rule.max_n)

    refs_rule = load_reference_limit(config)
    unique_cites = count_unique_citations(tex_text)
    refs_status = classify_range(unique_cites, lo=refs_rule.min_n, hi=refs_rule.max_n)

    opening_chars = load_opening_limit(config)
    opening = check_opening(tex_text, cjk_chars=opening_chars)

    return {
        "page_limit": {
            "min": page_rule.min_pages,
            "max": page_rule.max_pages,
            "recommended": [page_rule.recommended[0], page_rule.recommended[1]],
            "warning_threshold": page_rule.warning_threshold,
            "chars_per_page": page_rule.chars_per_page,
        },
        "estimated_pages": round(float(pages), 1),
        "page_status": page_status,
        "word_count_stripped": int(stripped_wc),
        "word_count_range": {"min": word_rule.min_n, "max": word_rule.max_n, "status": word_range_status},
        "references_unique": int(unique_cites),
        "references_range": {"min": refs_rule.min_n, "max": refs_rule.max_n, "status": refs_status},
        "opening": opening,
    }

