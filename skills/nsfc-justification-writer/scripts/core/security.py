#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, List, Mapping, Optional

from .config_access import get_mapping, get_seq_str
from .config_loader import DEFAULT_CONFIG


@dataclass(frozen=True)
class WritePolicy:
    allowed_relpaths: List[str]
    forbidden_relpaths: List[str]
    forbidden_globs: List[str]


def build_write_policy(config: Mapping[str, Any]) -> WritePolicy:
    guard = get_mapping(config, "guardrails")
    if not guard:
        # 兜底：即使上层未通过 config_loader.load_config() 加载，也不允许“空策略”导致任意写入
        guard = get_mapping(DEFAULT_CONFIG, "guardrails")
    return WritePolicy(
        allowed_relpaths=list(get_seq_str(guard, "allowed_write_files")) or ["extraTex/1.1.立项依据.tex"],
        forbidden_relpaths=list(get_seq_str(guard, "forbidden_write_files")) or ["main.tex", "extraTex/@config.tex"],
        forbidden_globs=list(get_seq_str(guard, "forbidden_write_globs")) or ["**/*.cls", "**/*.sty"],
    )


def _matches_any_glob(path: Path, globs: Iterable[str]) -> bool:
    for pat in globs:
        if path.match(pat):
            return True
    return False


def validate_write_target(
    *,
    project_root: Path,
    target_path: Path,
    policy: WritePolicy,
) -> None:
    project_root = project_root.resolve()
    target_path = target_path.resolve()
    try:
        rel = target_path.relative_to(project_root)
    except ValueError as e:
        raise RuntimeError(f"写入目标不在 project_root 内：{target_path}") from e

    rel_str = rel.as_posix()

    if policy.forbidden_relpaths and rel_str in set(policy.forbidden_relpaths):
        raise RuntimeError(f"禁止写入文件：{rel_str}")

    if policy.forbidden_globs and _matches_any_glob(rel, policy.forbidden_globs):
        raise RuntimeError(f"禁止写入路径（glob 命中）：{rel_str}")

    if policy.allowed_relpaths:
        if rel_str not in set(policy.allowed_relpaths):
            raise RuntimeError(f"写入目标不在白名单：{rel_str}")


def resolve_target_path(project_root: Path, relpath: str) -> Path:
    return (project_root / relpath).resolve()
