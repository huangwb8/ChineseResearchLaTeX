#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class Event:
    name: str
    data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Observability:
    events: List[Event] = field(default_factory=list)

    def add(self, name: str, **data: Any) -> None:
        self.events.append(Event(name=name, data=dict(data)))

    def to_dict(self) -> Dict[str, Any]:
        return {"events": [{"name": e.name, "data": e.data} for e in self.events]}

    def write_json(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")


def ensure_run_dir(runs_root: Path, run_id: str) -> Path:
    run_dir = (runs_root / run_id).resolve()
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir


def make_run_id(prefix: str = "run") -> str:
    import datetime as _dt

    ts = _dt.datetime.now().strftime("%Y%m%d%H%M%S")
    return f"{prefix}_{ts}"


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def maybe_write(path: Optional[Path], content: str) -> None:
    if path is None:
        return
    write_text(path, content)

