#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .observability import make_run_id


@dataclass(frozen=True)
class ApplyResult:
    changed: bool
    target_path: Path
    backup_path: Optional[Path]


def _safe_relpath(relpath: str) -> Path:
    """
    仅允许“相对路径”（防止把绝对路径/.. 注入到备份目录结构中）。
    """
    p = Path(str(relpath or "").strip())
    if p.is_absolute():
        raise ValueError(f"relpath 必须是相对路径：{relpath}")
    if any(part in {"..", ""} for part in p.parts):
        raise ValueError(f"relpath 非法：{relpath}")
    return p


def backup_file(*, src: Path, backup_root: Path, run_id: Optional[str] = None, relpath: Optional[str] = None) -> Path:
    run = run_id or make_run_id("backup")
    if relpath:
        dst = (backup_root / run / _safe_relpath(relpath)).resolve()
    else:
        dst = (backup_root / run / src.name).resolve()
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    return dst


def atomic_write_text(path: Path, content: str) -> None:
    path = path.resolve()
    tmp_path = path.with_name(f".{path.name}.tmp")
    tmp_path.write_text(content, encoding="utf-8")
    os.replace(tmp_path, path)


def apply_new_content(
    *,
    target_path: Path,
    new_text: str,
    backup_root: Optional[Path] = None,
    run_id: Optional[str] = None,
    target_relpath: Optional[str] = None,
) -> ApplyResult:
    target_path = target_path.resolve()
    old = target_path.read_text(encoding="utf-8", errors="ignore") if target_path.exists() else ""
    if old == new_text:
        return ApplyResult(changed=False, target_path=target_path, backup_path=None)

    backup_path: Optional[Path] = None
    if backup_root is not None and target_path.exists():
        backup_path = backup_file(src=target_path, backup_root=backup_root, run_id=run_id, relpath=target_relpath)

    atomic_write_text(target_path, new_text)
    return ApplyResult(changed=True, target_path=target_path, backup_path=backup_path)
