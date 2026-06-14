#!/usr/bin/env python3
"""
path_scope.py - 工作目录路径隔离校验模块

提供统一的路径准入检查，确保脚本的 I/O 路径限制在 work_dir（scope_root）内，
避免跨 run 读取/写入导致结果污染。
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Optional, Union


# 环境变量名（支持长名称和短别名）
ENV_SCOPE_ROOT = "SYSTEMATIC_LITERATURE_REVIEW_SCOPE_ROOT"
ENV_SCOPE_ROOT_SHORT = "SLR_SCOPE_ROOT"  # 短别名
ENV_PATH_SCOPE_DEBUG = "SYSTEMATIC_LITERATURE_REVIEW_PATH_SCOPE_DEBUG"
ENV_PATH_SCOPE_DEBUG_SHORT = "SLR_PATH_SCOPE_DEBUG"  # 短别名


def _debug(msg: str) -> None:
    if os.environ.get(ENV_PATH_SCOPE_DEBUG) or os.environ.get(ENV_PATH_SCOPE_DEBUG_SHORT):
        print(f"[path_scope] {msg}", file=sys.stderr)


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
            cwd = Path.cwd().resolve()
            try:
                scope_rel = scope_root.relative_to(cwd)
            except ValueError:
                scope_rel = None
            scope_parts = tuple(p for p in (scope_rel.parts if scope_rel is not None else ()) if p not in (".", ""))
            if scope_parts and input_path.parts[: len(scope_parts)] == scope_parts:
                prefer_cwd = True
        except OSError as exc:
            # 避免无声吞异常：在 debug 模式输出线索，默认仍回退到“相对 scope_root”口径。
            _debug(f"failed to resolve cwd for prefer_cwd detection: {exc}")
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
        if not candidates:
            raise ValueError(
                "无法将路径解析到工作目录内：{input}\n"
                "工作目录：{root}\n"
                "候选路径：\n"
                "  - cand1(scope_root/input): {cand1}\n"
                "  - cand2(cwd/input): {cand2}\n"
                "提示：请优先传 work_dir 内的相对路径（如 papers.jsonl），或传入带 work_dir 前缀的路径（如 runs/<topic>/papers.jsonl）。".format(
                    input=input_path, root=scope_root, cand1=cand1, cand2=cand2
                )
            )
        if must_exist:
            existed = [p for p in candidates if p.exists()]
            if existed:
                resolved = existed[0]
            else:
                resolved = candidates[0]
        else:
            resolved = candidates[0]

    if not _in_scope(resolved):
        raise ValueError(
            "路径不在工作目录内：{bad}\n工作目录：{root}\n这可能导致跨 run 污染，请检查路径输入。".format(
                bad=resolved, root=scope_root
            )
        )

    if must_exist and not resolved.exists():
        raise FileNotFoundError(f"路径不存在：{resolved}")

    _debug(f"resolved: input={input_path} must_exist={must_exist} -> {resolved}")
    return resolved


def get_scope_root_from_env() -> Optional[Path]:
    """从环境变量读取 scope_root（支持长名称和短别名）。"""
    env_var = os.environ.get(ENV_SCOPE_ROOT) or os.environ.get(ENV_SCOPE_ROOT_SHORT)
    return Path(env_var).expanduser().resolve() if env_var else None


def get_effective_scope_root(scope_root: Optional[Union[str, Path]]) -> Optional[Path]:
    """优先使用显式 scope_root，其次读取环境变量。"""
    if scope_root is None:
        return get_scope_root_from_env()
    return Path(scope_root).expanduser().resolve()


def require_scope(func):
    """
    装饰器：确保函数的 Path 参数都在 scope_root 内。

    使用示例：
        @require_scope
        def process_papers(input_file: Path, output_file: Path):
            ...

    注意：
        - 需要设置 SYSTEMATIC_LITERATURE_REVIEW_SCOPE_ROOT 环境变量
        - 会检查所有 Path 或 str 类型的参数
        - 如果路径不在 scope_root 内，会抛出 ValueError
    """
    import functools
    import inspect

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        scope_root = get_scope_root_from_env()
        if scope_root is None:
            raise RuntimeError(
                f"SYSTEMATIC_LITERATURE_REVIEW_SCOPE_ROOT 环境变量未设置，无法校验路径隔离。"
                f"调用函数: {func.__name__}"
            )

        # 检查所有 Path 类型的参数
        sig = inspect.signature(func)
        bound = sig.bind(*args, **kwargs)
        bound.apply_defaults()

        for name, value in bound.arguments.items():
            if isinstance(value, (Path, str)) and value:
                try:
                    # 排除 URL（http/https 开头）
                    if isinstance(value, str) and value.startswith(("http://", "https://")):
                        continue
                    # 只校验看起来像路径的字符串（包含分隔符或以 . 开头）
                    if isinstance(value, str):
                        if "/" not in value and "\\" not in value and not value.startswith("."):
                            continue
                    resolve_and_check(value, scope_root)
                except ValueError as e:
                    raise ValueError(
                        f"函数 {func.__name__} 参数 '{name}' 路径校验失败：{e}"
                    ) from e

        return func(*args, **kwargs)

    return wrapper
