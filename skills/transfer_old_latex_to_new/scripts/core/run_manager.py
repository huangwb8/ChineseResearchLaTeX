#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict


def _new_run_id() -> str:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    rand = os.urandom(3).hex()
    return f"{ts}_{rand}"


@dataclass(frozen=True)
class RunPaths:
    run_id: str
    run_root: Path
    input_snapshot_dir: Path
    analysis_dir: Path
    plan_dir: Path
    logs_dir: Path
    deliverables_dir: Path
    backup_dir: Path


def create_run(runs_root: Path, run_id: str | None = None) -> RunPaths:
    rid = run_id or _new_run_id()
    root = (runs_root / rid).resolve()

    input_snapshot_dir = root / "input_snapshot"
    analysis_dir = root / "analysis"
    plan_dir = root / "plan"
    logs_dir = root / "logs"
    deliverables_dir = root / "deliverables"
    backup_dir = root / "backup"

    for p in [
        input_snapshot_dir,
        analysis_dir,
        plan_dir,
        logs_dir,
        deliverables_dir,
        backup_dir,
    ]:
        p.mkdir(parents=True, exist_ok=True)

    return RunPaths(
        run_id=rid,
        run_root=root,
        input_snapshot_dir=input_snapshot_dir,
        analysis_dir=analysis_dir,
        plan_dir=plan_dir,
        logs_dir=logs_dir,
        deliverables_dir=deliverables_dir,
        backup_dir=backup_dir,
    )


def get_run(runs_root: Path, run_id: str) -> RunPaths:
    root = (runs_root / run_id).resolve()
    if not root.exists():
        raise FileNotFoundError(f"run_id 不存在: {root}")
    return RunPaths(
        run_id=run_id,
        run_root=root,
        input_snapshot_dir=root / "input_snapshot",
        analysis_dir=root / "analysis",
        plan_dir=root / "plan",
        logs_dir=root / "logs",
        deliverables_dir=root / "deliverables",
        backup_dir=root / "backup",
    )

