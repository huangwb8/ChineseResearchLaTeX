#!/usr/bin/env python3
"""
path_scope.py - 工作目录路径隔离校验模块

提供统一的路径准入检查，确保脚本的 I/O 路径限制在 work_dir（scope_root）内，
避免跨 run 读取/写入导致结果污染。
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional, Union


ENV_SCOPE_ROOT = "SYSTEMATIC_LITERATURE_REVIEW_SCOPE_ROOT"


def resolve_and_check(path: Union[str, Path], scope_root: Path, must_exist: bool = False) -> Path:
    """解析路径并校验是否在 scope_root 内。"""
    scope_root = scope_root.expanduser().resolve()
    input_path = Path(path).expanduser()

    def _in_scope(p: Path) -> bool:
        try:
            p.relative_to(scope_root)
            return True
        except ValueError:
            return False

    # 兼容两种相对路径口径：
    # 1) 相对 scope_root（推荐：在 work_dir 内以相对路径传参）
    # 2) 相对 cwd（兼容：从仓库根目录传入 runs/{topic}/... 这种“带前缀”的相对路径）
    if input_path.is_absolute():
        resolved = input_path.resolve()
    else:
        # 识别一种常见用法：用户从仓库根目录传入“带 work_dir 前缀”的相对路径
        # 例如：scope_root=runs/topic，input=runs/topic/papers.jsonl
        # 此时应优先按 cwd 解析（cand2），避免 scope_root 再拼一次导致 runs/topic/runs/topic/...
        prefer_cwd = False
        try:
            scope_rel = scope_root.relative_to(Path.cwd().resolve())
            scope_parts = tuple(p for p in scope_rel.parts if p not in (".", ""))
            if scope_parts and input_path.parts[: len(scope_parts)] == scope_parts:
                prefer_cwd = True
        except Exception:
            prefer_cwd = False

        cand1 = (scope_root / input_path).resolve()
        cand2 = input_path.resolve()
        if must_exist and cand2.exists() and not _in_scope(cand2):
            raise ValueError(
                "路径不在工作目录内：{bad}\n工作目录：{root}\n这可能导致跨 run 污染，请检查路径输入。".format(
                    bad=cand2, root=scope_root
                )
            )
        ordered = (cand2, cand1) if prefer_cwd else (cand1, cand2)
        candidates = [p for p in ordered if _in_scope(p)]
        if must_exist:
            existed = [p for p in candidates if p.exists()]
            if existed:
                resolved = existed[0]
            else:
                resolved = candidates[0] if candidates else cand1
        else:
            resolved = candidates[0] if candidates else cand1

    if not _in_scope(resolved):
        raise ValueError(
            "路径不在工作目录内：{bad}\n工作目录：{root}\n这可能导致跨 run 污染，请检查路径输入。".format(
                bad=resolved, root=scope_root
            )
        )

    if must_exist and not resolved.exists():
        raise FileNotFoundError(f"路径不存在：{resolved}")

    return resolved


def get_scope_root_from_env() -> Optional[Path]:
    """从环境变量读取 scope_root（SYSTEMATIC_LITERATURE_REVIEW_SCOPE_ROOT）。"""
    env_var = os.environ.get(ENV_SCOPE_ROOT)
    return Path(env_var).expanduser().resolve() if env_var else None


def get_effective_scope_root(scope_root: Optional[Union[str, Path]]) -> Optional[Path]:
    """优先使用显式 scope_root，其次读取环境变量。"""
    if scope_root is None:
        return get_scope_root_from_env()
    return Path(scope_root).expanduser().resolve()
