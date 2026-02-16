#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import difflib
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from .editor import atomic_write_text, backup_file
from .errors import BackupNotFoundError
from .observability import ensure_run_dir, make_run_id


@dataclass(frozen=True)
class RunInfo:
    run_id: str
    path: Path


def list_runs(*, runs_root: Path) -> List[RunInfo]:
    runs_root = Path(runs_root).resolve()
    if not runs_root.is_dir():
        return []
    items = []
    for p in runs_root.iterdir():
        if p.is_dir():
            items.append(RunInfo(run_id=p.name, path=p))
    return sorted(items, key=lambda x: x.run_id, reverse=True)


def find_backup_for_run(*, runs_root: Path, run_id: str, filename: str) -> Path:
    runs_root = Path(runs_root).resolve()
    run_dir = (runs_root / run_id).resolve()
    if not run_dir.is_dir():
        raise BackupNotFoundError(run_id)

    candidates = sorted(run_dir.glob(f"backup/**/{filename}"))
    if not candidates:
        raise BackupNotFoundError(run_id)
    return candidates[-1].resolve()


def find_backup_for_run_v2(
    *,
    runs_root: Path,
    run_id: str,
    target_relpath: Optional[str],
    filename_fallback: str,
) -> Path:
    """
    优先按 target_relpath 精确定位备份；找不到则回退到旧版“按文件名”匹配。
    兼容历史 runs 目录结构。
    """
    runs_root = Path(runs_root).resolve()
    run_dir = (runs_root / run_id).resolve()
    if not run_dir.is_dir():
        raise BackupNotFoundError(run_id)

    if target_relpath:
        rel = str(target_relpath).strip().lstrip("/").lstrip("\\")
        if rel and (".." not in Path(rel).parts):
            candidates = sorted(run_dir.glob(f"backup/**/{rel}"))
            if candidates:
                return candidates[-1].resolve()

    # backward-compatible fallback
    return find_backup_for_run(runs_root=runs_root, run_id=run_id, filename=filename_fallback)


def unified_diff(
    *,
    old_text: str,
    new_text: str,
    fromfile: str,
    tofile: str,
    context_lines: int = 3,
) -> str:
    old_lines = (old_text or "").splitlines(keepends=True)
    new_lines = (new_text or "").splitlines(keepends=True)
    diff = difflib.unified_diff(old_lines, new_lines, fromfile=fromfile, tofile=tofile, n=int(context_lines))
    return "".join(diff).strip() + "\n"


def rollback_from_backup(
    *,
    runs_root: Path,
    run_id: str,
    target_path: Path,
    target_relpath: Optional[str] = None,
    backup_current: bool = True,
    rollback_run_id: Optional[str] = None,
) -> Path:
    target_path = Path(target_path).resolve()
    backup_path = find_backup_for_run_v2(
        runs_root=runs_root,
        run_id=run_id,
        target_relpath=target_relpath,
        filename_fallback=target_path.name,
    )
    desired = backup_path.read_text(encoding="utf-8", errors="ignore")

    if backup_current and target_path.exists():
        rid = rollback_run_id or make_run_id("rollback")
        run_dir = ensure_run_dir(Path(runs_root).resolve(), rid)
        backup_root = (run_dir / "backup").resolve()
        backup_file(src=target_path, backup_root=backup_root, run_id=rid, relpath=target_relpath)

    atomic_write_text(target_path, desired)
    return backup_path
