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


def backup_file(*, src: Path, backup_root: Path, run_id: Optional[str] = None) -> Path:
    run = run_id or make_run_id("backup")
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
) -> ApplyResult:
    target_path = target_path.resolve()
    old = target_path.read_text(encoding="utf-8", errors="ignore") if target_path.exists() else ""
    if old == new_text:
        return ApplyResult(changed=False, target_path=target_path, backup_path=None)

    backup_path: Optional[Path] = None
    if backup_root is not None and target_path.exists():
        backup_path = backup_file(src=target_path, backup_root=backup_root, run_id=run_id)

    atomic_write_text(target_path, new_text)
    return ApplyResult(changed=True, target_path=target_path, backup_path=backup_path)

