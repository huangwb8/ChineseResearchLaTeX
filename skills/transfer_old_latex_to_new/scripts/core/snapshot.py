#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Iterable, List, Optional


def snapshot_project_editables(project_root: Path, snapshot_root: Path) -> List[str]:
    """
    快照用户可编辑内容（不包含 main.tex/.cls/.sty 等）。

    复制内容：
    - extraTex/*.tex（排除 extraTex/@config.tex）
    - references/*.bib
    - figures/**（若存在）
    """
    project_root = project_root.resolve()
    snapshot_root = snapshot_root.resolve()
    snapshot_root.mkdir(parents=True, exist_ok=True)

    copied: List[str] = []

    def copy_rel(rel: Path) -> None:
        src = (project_root / rel).resolve()
        if not src.exists():
            return
        dst = (snapshot_root / rel).resolve()
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        copied.append(str(rel).replace("\\", "/"))

    extra_dir = project_root / "extraTex"
    if extra_dir.exists():
        for p in sorted(extra_dir.glob("*.tex")):
            if p.name == "@config.tex":
                continue
            copy_rel(p.relative_to(project_root))

    ref_dir = project_root / "references"
    if ref_dir.exists():
        for p in sorted(ref_dir.glob("*.bib")):
            copy_rel(p.relative_to(project_root))

    figures_dir = project_root / "figures"
    if figures_dir.exists():
        for p in sorted(figures_dir.rglob("*")):
            if not p.is_file():
                continue
            rel = p.relative_to(project_root)
            dst = (snapshot_root / rel).resolve()
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(p, dst)
            copied.append(str(rel).replace("\\", "/"))

    return copied

