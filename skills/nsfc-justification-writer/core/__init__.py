#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
内部 Python 模块入口（非稳定对外 API）。

说明：
- scripts/run.py 会直接从各模块导入实现；本文件仅提供“方便交互/调试”的聚合导出。
- 若你需要稳定接口，请优先通过 scripts/run.py 的子命令调用。
"""

from .ai_integration import AIIntegration
from .config_loader import get_runs_dir, load_config, validate_config
from .diagnostic import DiagnosticReport
from .editor import ApplyResult
from .errors import SkillError
from .hybrid_coordinator import HybridCoordinator
from .review_integration import (
    ReviewDirectoryInfo,
    analyze_review_directory,
    detect_slr_directory,
    extract_citation_keys_from_bib,
    extract_citations_from_tex,
    format_review_directory_summary,
    validate_citation_consistency,
    validate_read_access,
)

__all__ = [
    "AIIntegration",
    "ApplyResult",
    "DiagnosticReport",
    "HybridCoordinator",
    "ReviewDirectoryInfo",
    "SkillError",
    "analyze_review_directory",
    "detect_slr_directory",
    "extract_citation_keys_from_bib",
    "extract_citations_from_tex",
    "format_review_directory_summary",
    "get_runs_dir",
    "load_config",
    "validate_citation_consistency",
    "validate_config",
    "validate_read_access",
]
