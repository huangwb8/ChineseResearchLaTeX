#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Set

from .latex_utils import extract_all_resource_paths, safe_read_text


@dataclass(frozen=True)
class ResourceInfo:
    """资源文件信息"""
    rel_path: str  # 相对于项目根目录的路径
    referenced_by: List[str]  # 引用此文件的 .tex 文件列表
    exists: bool  # 文件是否存在


@dataclass(frozen=True)
class ResourceScanResult:
    """资源文件扫描结果"""
    resources: Dict[str, ResourceInfo]  # rel_path -> ResourceInfo
    total_count: int
    missing_count: int
    directories: Set[str]  # 涉及的目录列表


def scan_project_resources(
    project_root: Path,
    tex_files: List[str],
    exclude_dirs: Set[str] | None = None,
) -> ResourceScanResult:
    """
    扫描项目中所有引用的资源文件

    Args:
        project_root: 项目根目录
        tex_files: 要扫描的 .tex 文件列表（相对路径）
        exclude_dirs: 要排除的目录（如 ".git", "node_modules"）

    Returns:
        ResourceScanResult: 扫描结果
    """
    project_root = project_root.resolve()
    exclude_dirs = exclude_dirs or {".git", "__pycache__", "node_modules", ".venv", "venv"}

    resources: Dict[str, ResourceInfo] = {}
    referenced_by_map: Dict[str, List[str]] = {}

    for tex_rel in tex_files:
        tex_path = project_root / tex_rel
        if not tex_path.exists():
            continue

        content = safe_read_text(tex_path)
        resource_paths = extract_all_resource_paths(content)

        for res_path in resource_paths:
            # 解析相对路径
            # LaTeX 资源路径可能相对于 .tex 文件，或相对于项目根目录
            tex_dir = tex_path.parent

            # 尝试多个可能的路径
            possible_paths = [
                tex_dir / res_path,  # 相对于 .tex 文件
                project_root / res_path,  # 相对于项目根目录
            ]

            actual_path: Path | None = None
            for p in possible_paths:
                if p.exists():
                    actual_path = p
                    break

            # 计算相对于项目根目录的路径
            if actual_path:
                rel = str(actual_path.relative_to(project_root)).replace("\\", "/")
            else:
                # 即使文件不存在，也记录路径
                # 假设相对于 .tex 文件
                rel = str((tex_dir / res_path).relative_to(project_root)).replace("\\", "/")

            if rel not in referenced_by_map:
                referenced_by_map[rel] = []
            referenced_by_map[rel].append(tex_rel)

            # 记录资源信息
            if rel not in resources:
                resources[rel] = ResourceInfo(
                    rel_path=rel,
                    referenced_by=[],
                    exists=actual_path is not None,
                )

    # 更新 referenced_by
    updated_resources: Dict[str, ResourceInfo] = {}
    for rel, info in resources.items():
        updated_resources[rel] = ResourceInfo(
            rel_path=info.rel_path,
            referenced_by=sorted(set(referenced_by_map.get(rel, []))),
            exists=info.exists,
        )

    # 统计
    total_count = len(updated_resources)
    missing_count = sum(1 for info in updated_resources.values() if not info.exists)

    # 收集涉及的目录
    directories: Set[str] = set()
    for rel in updated_resources.keys():
        dir_part = str(Path(rel).parent)
        if dir_part and dir_part != ".":
            directories.add(dir_part)

    return ResourceScanResult(
        resources=updated_resources,
        total_count=total_count,
        missing_count=missing_count,
        directories=directories,
    )


def copy_resources(
    old_project: Path,
    new_project: Path,
    resources: Dict[str, ResourceInfo],
    copy_strategy: str = "missing",  # missing(只复制缺失的) | all(全部复制) | dry_run(只报告不复制)
    dry_run: bool = False,
) -> Dict[str, any]:
    """
    复制资源文件到新项目

    Args:
        old_project: 旧项目根目录
        new_project: 新项目根目录
        resources: 资源文件扫描结果
        copy_strategy: 复制策略
        dry_run: 是否只报告不实际复制

    Returns:
        复制结果报告
    """
    old_project = old_project.resolve()
    new_project = new_project.resolve()

    copied: List[str] = []
    skipped: List[str] = []
    failed: List[Dict[str, str]] = []
    created_dirs: Set[str] = set()

    for rel, info in resources.items():
        if not info.exists:
            skipped.append(rel)
            continue

        old_path = old_project / rel
        new_path = new_project / rel

        # 检查是否需要复制
        if copy_strategy == "missing" and new_path.exists():
            skipped.append(rel)
            continue

        # 创建目标目录
        target_dir = str(new_path.parent)
        if target_dir not in created_dirs:
            if not dry_run:
                new_path.parent.mkdir(parents=True, exist_ok=True)
            created_dirs.add(target_dir)

        # 复制文件
        try:
            if not dry_run:
                shutil.copy2(old_path, new_path)
            copied.append(rel)
        except Exception as e:
            failed.append({
                "path": rel,
                "error": str(e),
            })

    return {
        "copied": copied,
        "skipped": skipped,
        "failed": failed,
        "created_dirs": sorted(created_dirs),
        "summary": {
            "total": len(resources),
            "copied_count": len(copied),
            "skipped_count": len(skipped),
            "failed_count": len(failed),
        }
    }


def validate_resource_integrity(
    new_project: Path,
    resources: Dict[str, ResourceInfo],
) -> Dict[str, any]:
    """
    验证新项目中的资源引用完整性

    Args:
        new_project: 新项目根目录
        resources: 资源文件列表

    Returns:
        验证结果报告
    """
    new_project = new_project.resolve()

    valid: List[str] = []
    missing: List[str] = []
    broken_refs: List[Dict[str, str]] = []

    for rel, info in resources.items():
        new_path = new_project / rel

        if not new_path.exists():
            missing.append(rel)
            # 记录哪些 .tex 文件引用了缺失的资源
            for tex_file in info.referenced_by:
                broken_refs.append({
                    "resource": rel,
                    "referenced_by": tex_file,
                })
        else:
            valid.append(rel)

    return {
        "valid": valid,
        "missing": missing,
        "broken_refs": broken_refs,
        "summary": {
            "total": len(resources),
            "valid_count": len(valid),
            "missing_count": len(missing),
        }
    }
