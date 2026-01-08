#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Tuple

from .latex_utils import safe_read_text
from .reference_validator import validate_migration_reference_integrity
from .resource_manager import copy_resources, scan_project_resources, validate_resource_integrity
from .security_manager import SecurityManager


def _atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(content, encoding="utf-8")
    tmp.replace(path)


def _copy_file(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


@dataclass(frozen=True)
class ApplyResult:
    applied: List[Dict[str, Any]]
    skipped: List[Dict[str, Any]]
    warnings: List[str]
    resources: Dict[str, Any]  # 资源文件处理结果
    references: Dict[str, Any]  # 引用完整性验证结果

    def to_dict(self) -> Dict[str, Any]:
        return {
            "applied": self.applied,
            "skipped": self.skipped,
            "warnings": self.warnings,
            "resources": self.resources,
            "references": self.references,
        }


def snapshot_targets(new_project: Path, backup_root: Path, targets: List[str], security: SecurityManager) -> None:
    new_project = new_project.resolve()
    backup_root = backup_root.resolve()
    for rel in targets:
        abs_path = (new_project / rel).resolve()
        if not abs_path.exists():
            continue
        security.assert_can_write(abs_path)  # 允许写入的才需要备份
        backup_path = (backup_root / rel).resolve()
        backup_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(abs_path, backup_path)


def restore_snapshot(new_project: Path, backup_root: Path, security: SecurityManager) -> List[str]:
    restored: List[str] = []
    new_project = new_project.resolve()
    backup_root = backup_root.resolve()
    if not backup_root.exists():
        return restored
    for file_path in backup_root.rglob("*"):
        if not file_path.is_file():
            continue
        rel = file_path.relative_to(backup_root)
        target = (new_project / rel).resolve()
        security.assert_can_write(target)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(file_path, target)
        restored.append(str(rel).replace("\\", "/"))
    return restored


def apply_plan(
    old_project: Path,
    new_project: Path,
    plan: Dict[str, Any],
    config: Dict[str, Any],
    security: SecurityManager,
    backup_root: Path,
    allow_low_confidence: bool = False,
) -> ApplyResult:
    tasks = (plan or {}).get("tasks") or []
    placeholder = ((config.get("migration", {}) or {}).get("content_generation", {}) or {}).get(
        "placeholder_text", "\\textbf{[此部分内容需要补充]}"
    )

    target_files: List[str] = []
    for t in tasks:
        if t.get("target"):
            target_files.append(t["target"])

    snapshot_targets(new_project, backup_root, target_files, security)

    applied: List[Dict[str, Any]] = []
    skipped: List[Dict[str, Any]] = []
    warnings: List[str] = []

    # ========== 第一步：迁移 .tex 内容文件 ==========
    for t in tasks:
        t_type = t.get("type")
        target_rel = t.get("target")
        source_rel = t.get("source")

        if t_type == "needs_manual":
            skipped.append({**t, "skip_reason": "needs_manual"})
            continue

        if t.get("confidence") == "low" and not allow_low_confidence:
            skipped.append({**t, "skip_reason": "low_confidence"})
            continue

        if not target_rel:
            skipped.append({**t, "skip_reason": "missing_target"})
            continue

        target_abs = (new_project / target_rel).resolve()
        security.assert_can_write(target_abs)

        if t_type == "copy_one_to_one":
            if not source_rel:
                skipped.append({**t, "skip_reason": "missing_source"})
                continue
            source_abs = (old_project / source_rel).resolve()
            if not source_abs.exists():
                skipped.append({**t, "skip_reason": f"source_not_found: {source_rel}"})
                continue
            content = safe_read_text(source_abs)
            _atomic_write(target_abs, content)
            applied.append({**t, "status": "copied"})
            continue

        if t_type == "placeholder_new_added":
            _atomic_write(target_abs, placeholder + "\n")
            applied.append({**t, "status": "placeholder_written"})
            continue

        skipped.append({**t, "skip_reason": f"unknown_task_type: {t_type}"})

    if skipped:
        warnings.append(f"有 {len(skipped)} 个任务未自动执行，详见 apply 结果。")

    # ========== 第二步：扫描并迁移资源文件 ==========
    # 资源文件处理配置
    resource_config = (config.get("migration", {}) or {}).get("figure_handling", "copy")
    copy_resources_enabled = resource_config == "copy"

    resources_result: Dict[str, Any] = {
        "enabled": copy_resources_enabled,
        "scanned": False,
        "copied": False,
        "validated": False,
        "scan_summary": {},
        "copy_summary": {},
        "validation_summary": {},
    }

    if copy_resources_enabled and applied:
        # 收集已迁移的 .tex 文件列表
        migrated_tex_files = [t["target"] for t in applied if t.get("status") == "copied"]

        if migrated_tex_files:
            # 扫描旧项目的资源文件
            scan_result = scan_project_resources(
                old_project,
                migrated_tex_files,
                exclude_dirs={".git", "__pycache__", "node_modules"},
            )

            resources_result["scanned"] = True
            resources_result["scan_summary"] = {
                "total": scan_result.total_count,
                "missing": scan_result.missing_count,
                "directories": sorted(scan_result.directories),
            }

            # 复制资源文件到新项目（只复制缺失的）
            copy_result = copy_resources(
                old_project,
                new_project,
                scan_result.resources,
                copy_strategy="missing",  # 只复制新项目中不存在的
                dry_run=False,
            )

            resources_result["copied"] = True
            resources_result["copy_summary"] = copy_result["summary"]

            # 验证新项目中的资源引用完整性
            validation_result = validate_resource_integrity(
                new_project,
                scan_result.resources,
            )

            resources_result["validated"] = True
            resources_result["validation_summary"] = validation_result["summary"]

            # 如果有缺失资源，添加警告
            if validation_result["summary"]["missing_count"] > 0:
                warnings.append(
                    f"有 {validation_result['summary']['missing_count']} 个资源文件在新项目中缺失，"
                    "可能导致编译失败。请检查 resources 部分。"
                )

    # ========== 第三步：验证引用完整性 ==========
    references_result: Dict[str, Any] = {
        "validated": False,
        "old_report": {},
        "new_report": {},
        "comparison": {},
        "passed": False,
    }

    if applied:
        # 收集已迁移的 .tex 文件列表
        migrated_tex_files = [t["target"] for t in applied if t.get("status") == "copied"]

        if migrated_tex_files:
            # 获取参考文献文件
            old_bib_files = []
            new_bib_files = []
            # 假设参考文献文件位置相同，都在 references/ 目录
            for tex_file in migrated_tex_files:
                # 这里简化处理，实际可以从项目分析中获取
                pass

            # 执行引用完整性验证
            ref_validation = validate_migration_reference_integrity(
                old_project,
                new_project,
                migrated_tex_files,
                [],  # bib_files (暂时为空，可以后续增强)
                min_intact_rate=0.95,
            )

            references_result["validated"] = True
            references_result["old_report"] = ref_validation["old_report"]
            references_result["new_report"] = ref_validation["new_report"]
            references_result["comparison"] = ref_validation["comparison"]
            references_result["passed"] = ref_validation["passed"]

            # 如果引用完整性下降，添加警告
            if not ref_validation["passed"]:
                warnings.append(
                    f"引用完整性验证失败：{ref_validation['recommendation']}"
                )

    return ApplyResult(
        applied=applied,
        skipped=skipped,
        warnings=warnings,
        resources=resources_result,
        references=references_result,
    )

