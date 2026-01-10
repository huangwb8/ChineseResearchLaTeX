#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

from typing import Any, Dict

from .config_access import get_mapping, get_str

StyleMode = str  # "theoretical" | "mixed" | "engineering"


def get_style_mode(config: Dict[str, Any]) -> StyleMode:
    style_cfg = get_mapping(config, "style")
    mode = get_str(style_cfg, "mode", "theoretical").strip().lower()
    if mode in {"theoretical", "mixed", "engineering"}:
        return mode
    return "theoretical"


def style_preamble_text(mode: StyleMode) -> str:
    if mode == "engineering":
        return (
            "写作导向：工程/应用导向（可配置）\n"
            "- 优先讲清“应用场景-需求-约束-可验证指标/对照”\n"
            "- 工程细节允许出现，但仍需与科学问题/研究内容衔接\n"
            "- 避免不可核验绝对表述（国际领先/国内首次等）\n"
        )
    if mode == "mixed":
        return (
            "写作导向：理论 + 应用混合导向（可配置）\n"
            "- 先给出科学问题/假说与可证伪表述，再补应用动机与约束\n"
            "- 明确验证维度（理论证明/数值验证/对照实验）与可交付成果\n"
            "- 避免不可核验绝对表述（国际领先/国内首次等）\n"
        )
    return (
        "写作导向：理论创新导向（默认，可配置）\n"
        "- 聚焦科学问题/假说的可证伪性、理论贡献的清晰性\n"
        "- 现状不足优先写“假设过强/框架不统一/因果缺失/界不紧”等理论局限\n"
        "- 验证维度要明确（理论证明/定理/数值验证/对照实验）\n"
        "- 工程实现细节尽量留到“研究内容/技术路线”章节\n"
        "- 避免不可核验绝对表述（国际领先/国内首次等）\n"
    )

