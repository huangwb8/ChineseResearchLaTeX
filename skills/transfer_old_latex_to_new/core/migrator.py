#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Tuple

from .latex_utils import safe_read_text
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

    def to_dict(self) -> Dict[str, Any]:
        return {
            "applied": self.applied,
            "skipped": self.skipped,
            "warnings": self.warnings,
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

    return ApplyResult(applied=applied, skipped=skipped, warnings=warnings)

