from __future__ import annotations

import datetime as dt
import json
import re
from pathlib import Path
from typing import Any

import yaml


def skill_root() -> Path:
    return Path(__file__).resolve().parents[1]


def load_config(root: Path | None = None) -> dict[str, Any]:
    config_path = (root or skill_root()) / "config.yaml"
    return yaml.safe_load(config_path.read_text(encoding="utf-8"))


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def write_json(path: Path, payload: Any) -> None:
    ensure_dir(path.parent)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=False) + "\n",
        encoding="utf-8",
    )


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_text(path: Path, text: str) -> None:
    ensure_dir(path.parent)
    path.write_text(text, encoding="utf-8")


def resolve_path(path_str: str, base: Path | None = None) -> Path:
    path = Path(path_str).expanduser()
    if not path.is_absolute():
        path = (base or Path.cwd()) / path
    return path.resolve()


def is_within(parent: Path, child: Path) -> bool:
    parent_resolved = parent.resolve()
    child_resolved = child.resolve()
    return child_resolved == parent_resolved or parent_resolved in child_resolved.parents


def require_within(parent: Path, child: Path, label: str) -> Path:
    if not is_within(parent, child):
        raise ValueError(f"{label} 必须位于工作区内: {child}")
    return child


def resolve_path_within(path_str: str, *, parent: Path, label: str, base: Path | None = None) -> Path:
    return require_within(parent.resolve(), resolve_path(path_str, base=base), label)


def workspace_output_path(workspace: Path, relative_path: str) -> Path:
    return require_within(workspace.resolve(), (workspace / relative_path).resolve(), "输出路径")


def generate_run_id(config: dict[str, Any], now: dt.datetime | None = None) -> str:
    workspace_cfg = config["workspace"]
    stamp = (now or dt.datetime.now()).strftime(workspace_cfg["timestamp_format"])
    return f"{workspace_cfg['run_prefix']}{stamp}"


def allocate_unique_run_id(workspace_base: Path, run_id: str) -> str:
    if not (workspace_base / run_id).exists():
        return run_id
    for idx in range(2, 100):
        candidate = f"{run_id}-{idx:02d}"
        if not (workspace_base / candidate).exists():
            return candidate
    raise ValueError(f"无法在 {workspace_base} 下分配唯一工作目录: {run_id}")


def normalize_text(text: str | None) -> str:
    if not text:
        return ""
    collapsed = re.sub(r"[^a-z0-9]+", " ", text.lower())
    return re.sub(r"\s+", " ", collapsed).strip()


def float_or_none(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def quartile_from_category(category: str | None) -> str:
    text = (category or "").upper()
    for quartile in ("Q1", "Q2", "Q3", "Q4"):
        if quartile in text:
            return quartile
    return "unknown"


def slugify(text: str, max_length: int = 80) -> str:
    slug = normalize_text(text).replace(" ", "-")
    slug = re.sub(r"-{2,}", "-", slug).strip("-")
    return slug[:max_length] or "item"


def compact_text(text: str | None, max_chars: int = 220) -> str:
    cleaned = re.sub(r"\s+", " ", (text or "")).strip()
    if len(cleaned) <= max_chars:
        return cleaned
    return cleaned[: max_chars - 1].rstrip() + "…"
