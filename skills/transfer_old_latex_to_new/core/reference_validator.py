#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Set

from .latex_utils import extract_cites, extract_labels, extract_refs, safe_read_text


@dataclass(frozen=True)
class ReferenceReport:
    """引用完整性报告"""
    total_labels: int  # 定义的标签总数
    total_refs: int  # 引用总数
    total_cites: int  # 文献引用总数
    undefined_refs: Set[str]  # 未定义的引用（引用了不存在的label）
    unused_labels: Set[str]  # 未使用的标签（定义了但没被引用）
    missing_cites: Set[str]  # 缺失的文献引用（.bib文件中不存在）
    intact_rate: float  # 引用完整性率（0-1）


def validate_references(
    project_root: Path,
    tex_files: List[str],
    bib_files: List[str],
) -> ReferenceReport:
    """
    验证 LaTeX 项目的引用完整性

    Args:
        project_root: 项目根目录
        tex_files: 要检查的 .tex 文件列表
        bib_files: 参考文献 .bib 文件列表

    Returns:
        ReferenceReport: 引用完整性报告
    """
    project_root = project_root.resolve()

    # 收集所有 labels, refs, cites
    all_labels: Set[str] = set()
    all_refs: Set[str] = set()
    all_cites: Set[str] = set()

    for tex_rel in tex_files:
        tex_path = project_root / tex_rel
        if not tex_path.exists():
            continue

        content = safe_read_text(tex_path)
        all_labels.update(extract_labels(content))
        all_refs.update(extract_refs(content))
        all_cites.update(extract_cites(content))

    # 检查未定义的引用
    undefined_refs = all_refs - all_labels

    # 检查未使用的标签
    unused_labels = all_labels - all_refs

    # 检查文献引用（从 .bib 文件中提取所有可用的 bibkey）
    available_bibkeys: Set[str] = set()
    for bib_rel in bib_files:
        bib_path = project_root / bib_rel
        if not bib_path.exists():
            continue

        content = safe_read_text(bib_path)
        # 简单提取 @article, @book 等条目的 bibkey
        import re
        for match in re.finditer(r'@[\w]+\{([^,]+)', content):
            available_bibkeys.add(match.group(1).strip())

    missing_cites = all_cites - available_bibkeys

    # 计算完整性率
    total_checks = len(all_refs) + len(all_cites)
    total_failures = len(undefined_refs) + len(missing_cites)
    intact_rate = 1.0 - (total_failures / total_checks) if total_checks > 0 else 1.0

    return ReferenceReport(
        total_labels=len(all_labels),
        total_refs=len(all_refs),
        total_cites=len(all_cites),
        undefined_refs=undefined_refs,
        unused_labels=unused_labels,
        missing_cites=missing_cites,
        intact_rate=intact_rate,
    )


def compare_reference_integrity(
    old_report: ReferenceReport,
    new_report: ReferenceReport,
    tolerance: float = 0.0,
) -> Dict[str, any]:
    """
    比较新旧项目的引用完整性

    Args:
        old_report: 旧项目的引用报告
        new_report: 新项目的引用报告
        tolerance: 容忍的完整性下降比例（默认0，不允许下降）

    Returns:
        比较结果
    """
    old_rate = old_report.intact_rate
    new_rate = new_report.intact_rate

    rate_change = new_rate - old_rate
    is_degraded = rate_change < -tolerance

    # 检查是否有新的未定义引用
    new_undefined = new_report.undefined_refs - old_report.undefined_refs

    # 检查是否有新的缺失文献
    new_missing_cites = new_report.missing_cites - old_report.missing_cites

    return {
        "old_intact_rate": old_rate,
        "new_intact_rate": new_rate,
        "rate_change": rate_change,
        "is_degraded": is_degraded,
        "new_undefined_refs": sorted(new_undefined),
        "new_missing_cites": sorted(new_missing_cites),
        "summary": {
            "intact_rate_preserved": not is_degraded,
            "new_issues_count": len(new_undefined) + len(new_missing_cites),
        }
    }


def validate_migration_reference_integrity(
    old_project: Path,
    new_project: Path,
    tex_files: List[str],
    bib_files: List[str],
    min_intact_rate: float = 0.95,
) -> Dict[str, any]:
    """
    验证迁移后的引用完整性

    Args:
        old_project: 旧项目路径
        new_project: 新项目路径
        tex_files: 已迁移的 .tex 文件列表
        bib_files: 参考文献 .bib 文件列表
        min_intact_rate: 最小允许的完整性率

    Returns:
        验证结果
    """
    # 验证旧项目
    old_report = validate_references(old_project, tex_files, bib_files)

    # 验证新项目
    new_report = validate_references(new_project, tex_files, bib_files)

    # 比较完整性
    comparison = compare_reference_integrity(old_report, new_report, tolerance=0.0)

    # 判断是否通过
    passed = (
        new_report.intact_rate >= min_intact_rate
        and not comparison["is_degraded"]
        and comparison["summary"]["new_issues_count"] == 0
    )

    return {
        "passed": passed,
        "old_report": {
            "intact_rate": old_report.intact_rate,
            "total_refs": old_report.total_refs,
            "undefined_refs": len(old_report.undefined_refs),
            "missing_cites": len(old_report.missing_cites),
        },
        "new_report": {
            "intact_rate": new_report.intact_rate,
            "total_refs": new_report.total_refs,
            "undefined_refs": len(new_report.undefined_refs),
            "missing_cites": len(new_report.missing_cites),
        },
        "comparison": comparison,
        "recommendation": _generate_recommendation(old_report, new_report, comparison),
    }


def _generate_recommendation(
    old_report: ReferenceReport,
    new_report: ReferenceReport,
    comparison: Dict[str, any],
) -> str:
    """生成修复建议"""
    if comparison["summary"]["new_issues_count"] == 0:
        return "✅ 引用完整性保持良好，无需修复。"

    issues = []

    if comparison["new_undefined_refs"]:
        issues.append(f"有 {len(comparison['new_undefined_refs'])} 个未定义引用：{list(comparison['new_undefined_refs'])[:5]}...")

    if comparison["new_missing_cites"]:
        issues.append(f"有 {len(comparison['new_missing_cites'])} 个缺失文献引用：{list(comparison['new_missing_cites'])[:5]}...")

    return "❌ " + "; ".join(issues) + " 请检查并修复。"
