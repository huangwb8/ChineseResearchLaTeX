#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
systematic-literature-review 集成模块

提供对 systematic-literature-review 生成的文献综述目录的只读访问支持。
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Set


# systematic-literature-review 生成的目录标记隐藏文件夹
_SLR_MARKER = ".systematic-literature-review"


@dataclass(frozen=True)
class ReviewDirectoryInfo:
    """
    文献综述目录信息

    Attributes:
        path: 目录路径
        is_slr_directory: 是否为 systematic-literature-review 生成的目录
        tex_files: 可用的 .tex 文件列表
        bib_files: 可用的 .bib 文件列表
        read_only: 是否为只读访问
    """
    path: Path
    is_slr_directory: bool
    tex_files: List[Path]
    bib_files: List[Path]
    read_only: bool


def detect_slr_directory(path: Path) -> bool:
    """
    检测给定目录是否为 systematic-literature-review 生成的文献综述目录。

    识别标准（满足任一即可）：
    1. 目录中存在隐藏文件夹 `.systematic-literature-review`（运行中的 pipeline）
    2. 目录中存在 systematic-literature-review 典型的文件组合：
       - `{主题}_review.tex` 文件
       - `{主题}_参考文献.bib` 或 `references.bib` 文件
       - `{主题}_工作条件.md` 文件

    Args:
        path: 待检测的目录路径

    Returns:
        如果是 systematic-literature-review 生成的目录则返回 True
    """
    p = Path(path).resolve()
    if not p.is_dir():
        return False

    # 方法1：检查是否存在标记文件夹（运行中的 pipeline）
    marker_dir = p / _SLR_MARKER
    if marker_dir.is_dir():
        # 进一步检查是否存在典型的 .tex 和 .bib 文件
        tex_files = list(p.glob("*_review.tex"))
        bib_files = list(p.glob("*_参考文献.bib")) + list(p.glob("references.bib"))
        if len(tex_files) > 0 and len(bib_files) > 0:
            return True

    # 方法2：检查是否存在典型的文件组合（已完成的输出目录）
    tex_files = list(p.glob("*_review.tex"))
    bib_files = list(p.glob("*_参考文献.bib")) + list(p.glob("references.bib"))
    work_condition_files = list(p.glob("*_工作条件.md"))

    if len(tex_files) > 0 and len(bib_files) > 0:
        # 如果存在工作条件文件，强烈提示为 SLR 目录
        if len(work_condition_files) > 0:
            return True
        # 如果 tex 和 bib 文件名前缀一致，也认为是 SLR 目录
        tex_prefixes = {f.name.replace("_review.tex", "") for f in tex_files}
        bib_prefixes = {f.name.replace("_参考文献.bib", "").replace("references.bib", "references") for f in bib_files}
        if tex_prefixes & bib_prefixes:  # 有共同前缀
            return True

    return False


def analyze_review_directory(
    path: Path,
    *,
    allow_write: bool = False,
) -> ReviewDirectoryInfo:
    """
    分析文献综述目录，返回目录信息。

    Args:
        path: 文献综述目录路径
        allow_write: 是否允许写入（对 systematic-literature-review 目录默认为只读）

    Returns:
        ReviewDirectoryInfo 对象
    """
    p = Path(path).resolve()
    is_slr = detect_slr_directory(p)

    # 收集 .tex 文件
    tex_patterns = ["*.tex", "*_review.tex"]
    tex_files: Set[Path] = set()
    for pattern in tex_patterns:
        tex_files.update(p.glob(pattern))
    # 过滤掉隐藏文件和备份文件
    tex_files = {f for f in tex_files if not f.name.startswith(".") and not f.name.endswith(".bak")}

    # 收集 .bib 文件
    bib_patterns = ["*.bib", "*_参考文献.bib", "references.bib"]
    bib_files: Set[Path] = set()
    for pattern in bib_patterns:
        bib_files.update(p.glob(pattern))
    bib_files = {f for f in bib_files if not f.name.startswith(".")}

    return ReviewDirectoryInfo(
        path=p,
        is_slr_directory=is_slr,
        tex_files=sorted(tex_files),
        bib_files=sorted(bib_files),
        read_only=(is_slr and not allow_write),
    )


def validate_read_access(info: ReviewDirectoryInfo) -> List[str]:
    """
    验证目录的可读性，返回问题列表。

    Args:
        info: ReviewDirectoryInfo 对象

    Returns:
        问题列表（空列表表示无问题）
    """
    issues: List[str] = []

    # 检查 .tex 文件
    if not info.tex_files:
        issues.append("未找到 .tex 文件")

    # 检查 .bib 文件
    if not info.bib_files:
        issues.append("未找到 .bib 文件")

    # 检查文件可读性
    for tex_file in info.tex_files:
        if not tex_file.is_file():
            issues.append(f".tex 文件不可读: {tex_file.name}")

    for bib_file in info.bib_files:
        if not bib_file.is_file():
            issues.append(f".bib 文件不可读: {bib_file.name}")

    return issues


def extract_citation_keys_from_bib(bib_path: Path) -> Set[str]:
    """
    从 .bib 文件中提取所有 citation key。

    Args:
        bib_path: .bib 文件路径

    Returns:
        citation key 集合
    """
    if not bib_path.is_file():
        return set()

    # BibTeX 条目模式：@article{key, 或 @book{key,
    entry_pattern = re.compile(r"@\w+\s*\{\s*([^\s,]+)\s*,")

    keys: Set[str] = set()
    try:
        with open(bib_path, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                matches = entry_pattern.findall(line)
                keys.update(matches)
    except Exception:
        # 文件读取失败时返回空集合
        pass

    return keys


def extract_citations_from_tex(tex_path: Path) -> Set[str]:
    """
    从 .tex 文件中提取所有 \\cite{...} 中的 key。

    Args:
        tex_path: .tex 文件路径

    Returns:
        citation key 集合
    """
    if not tex_path.is_file():
        return set()

    # 匹配 \cite{key} 或 \cite{key1,key2}
    cite_pattern = re.compile(r"\\cite\s*\{\s*([^}]+)\s*\}")

    keys: Set[str] = set()
    try:
        with open(tex_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
            matches = cite_pattern.findall(content)
            for match in matches:
                # 分割多个 key（逗号分隔）
                for key in match.split(","):
                    key = key.strip()
                    if key:
                        keys.add(key)
    except Exception:
        # 文件读取失败时返回空集合
        pass

    return keys


def validate_citation_consistency(
    tex_path: Path,
    bib_path: Path,
) -> Dict[str, Set[str]]:
    """
    验证 .tex 文件中的引用与 .bib 文件中的定义是否一致。

    Args:
        tex_path: .tex 文件路径
        bib_path: .bib 文件路径

    Returns:
        字典，包含：
        - 'missing_in_bib': 在 .tex 中引用但 .bib 中未定义的 key
        - 'unused_in_bib': 在 .bib 中定义但 .tex 中未引用的 key
    """
    tex_keys = extract_citations_from_tex(tex_path)
    bib_keys = extract_citation_keys_from_bib(bib_path)

    return {
        "missing_in_bib": tex_keys - bib_keys,
        "unused_in_bib": bib_keys - tex_keys,
    }


def format_review_directory_summary(info: ReviewDirectoryInfo) -> str:
    """
    格式化输出文献综述目录信息摘要。

    Args:
        info: ReviewDirectoryInfo 对象

    Returns:
        格式化的摘要字符串
    """
    lines = [
        f"文献综述目录: {info.path}",
        f"类型: {'systematic-literature-review 生成的目录' if info.is_slr_directory else '普通目录'}",
        f"访问模式: {'只读' if info.read_only else '可读写'}",
        "",
        f"TeX 文件 ({len(info.tex_files)} 个):",
    ]

    for tex_file in info.tex_files:
        lines.append(f"  - {tex_file.name}")

    lines.append(f"\nBibTeX 文件 ({len(info.bib_files)} 个):")
    for bib_file in info.bib_files:
        lines.append(f"  - {bib_file.name}")

    return "\n".join(lines)
