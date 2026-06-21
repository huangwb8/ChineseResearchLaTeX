#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict


def _new_run_id() -> str:
    return datetime.now().strftime("%Y-%m-%d-%H-%M")


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
    if run_id is None:
        for idx in range(1, 100):
            candidate = rid if idx == 1 else f"{rid}-{idx:02d}"
            if not (runs_root / candidate).exists():
                rid = candidate
                break
        else:
            raise FileExistsError(f"无法在 {runs_root} 下分配唯一 run 目录: {rid}")
    root = (runs_root / rid).resolve()

    input_snapshot_dir = root / "input" / "snapshot"
    analysis_dir = root / "analysis"
    plan_dir = root / "plan"
    logs_dir = root / "log"
    deliverables_dir = root / "output" / "deliverables"
    backup_dir = root / "input" / "backup"

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
        input_snapshot_dir=root / "input" / "snapshot",
        analysis_dir=root / "analysis",
        plan_dir=root / "plan",
        logs_dir=root / "log",
        deliverables_dir=root / "output" / "deliverables",
        backup_dir=root / "input" / "backup",
    )
