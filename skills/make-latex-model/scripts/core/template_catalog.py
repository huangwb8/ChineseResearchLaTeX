#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
内置模板目录。

目标：
1. 保留脚本需要的稳定结构化信息。
2. 不在 skill 内固化会随年份变化的官方标题文案。
3. 允许项目级 `.template.yaml` 继续做局部覆盖。
"""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any, Dict, Optional


_TEMPLATE_CATALOG: Dict[str, Dict[str, Any]] = {
    "nsfc/young": {
        "template": {
            "name": "nsfc/young",
            "display_name": "国家自然科学基金-青年科学基金项目",
            "product_line": "nsfc",
            "category": "research_funding",
        },
        "structure": {
            "content_dir": "extraTex",
            "config_file": "@config.tex",
            "main_file": "main.tex",
            "template_dir": "template",
        },
    },
    "nsfc/general": {
        "template": {
            "name": "nsfc/general",
            "display_name": "国家自然科学基金-面上项目",
            "product_line": "nsfc",
            "category": "research_funding",
        },
        "structure": {
            "content_dir": "extraTex",
            "config_file": "@config.tex",
            "main_file": "main.tex",
            "template_dir": "template",
        },
    },
    "nsfc/local": {
        "template": {
            "name": "nsfc/local",
            "display_name": "国家自然科学基金-地区科学基金项目",
            "product_line": "nsfc",
            "category": "research_funding",
        },
        "structure": {
            "content_dir": "extraTex",
            "config_file": "@config.tex",
            "main_file": "main.tex",
            "template_dir": "template",
        },
    },
    "paper/default": {
        "template": {
            "name": "paper/default",
            "display_name": "SCI 论文模板",
            "product_line": "paper",
            "category": "manuscript",
        },
        "structure": {
            "content_dir": "extraTex",
            "main_file": "main.tex",
        },
    },
    "thesis/default": {
        "template": {
            "name": "thesis/default",
            "display_name": "毕业论文模板",
            "product_line": "thesis",
            "category": "thesis",
        },
        "structure": {
            "content_dir": "extraTex",
            "main_file": "main.tex",
        },
    },
    "cv/default": {
        "template": {
            "name": "cv/default",
            "display_name": "中英文学术简历模板",
            "product_line": "cv",
            "category": "cv",
        },
        "structure": {
            "main_file": "main-zh.tex",
        },
    },
}


def normalize_template_name(template_name: Optional[str]) -> Optional[str]:
    """统一模板名分隔符。"""
    if not template_name:
        return None
    return str(template_name).strip().replace(".", "/")


def get_template_catalog() -> Dict[str, Dict[str, Any]]:
    """返回完整模板目录副本。"""
    return copy.deepcopy(_TEMPLATE_CATALOG)


def get_template_defaults(template_name: Optional[str]) -> Dict[str, Any]:
    """返回指定模板的内置默认配置。"""
    normalized = normalize_template_name(template_name)
    if not normalized:
        return {}
    return copy.deepcopy(_TEMPLATE_CATALOG.get(normalized, {}))


def detect_template_name(project_path: Optional[Path]) -> Optional[str]:
    """根据项目路径推断模板名。"""
    if not project_path:
        return None

    project_name = project_path.name.lower()

    if "nsfc_young" in project_name:
        return "nsfc/young"
    if "nsfc_general" in project_name:
        return "nsfc/general"
    if "nsfc_local" in project_name:
        return "nsfc/local"
    if project_name.startswith("paper-"):
        return "paper/default"
    if project_name.startswith("thesis-"):
        return "thesis/default"
    if project_name.startswith("cv-"):
        return "cv/default"
    return None
