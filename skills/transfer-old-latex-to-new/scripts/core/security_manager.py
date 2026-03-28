#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


class SecurityError(Exception):
    pass


class SystemFileModificationError(SecurityError):
    pass


@dataclass(frozen=True)
class AllowedWrite:
    root: Path
    patterns: List[re.Pattern[str]]


class SecurityManager:
    """
    迁移技能安全管理：
    - 禁止修改系统文件：main.tex、extraTex/@config.tex、*.cls、*.sty
    - 默认仅允许写入：extraTex/*.tex(排除@config)、references/*.bib、以及本 skill runs/**
    - packages/ 公共包源码与 projects/ 模板骨架一律视为只读
    """

    SYSTEM_BLACKLIST_REL = {
        "main.tex",
        "extraTex/@config.tex",
        "@config.tex",
    }

    def __init__(self, allowed_writes: Iterable[AllowedWrite]):
        self.allowed_writes = list(allowed_writes)

    @staticmethod
    def _is_blacklisted(rel_path: str) -> bool:
        rel_norm = rel_path.replace("\\", "/")
        if rel_norm in SecurityManager.SYSTEM_BLACKLIST_REL:
            return True
        if rel_norm.endswith(".cls") or rel_norm.endswith(".sty"):
            return True
        return False

    @staticmethod
    def _allowed_patterns_from_config(config: Optional[Dict[str, Any]]) -> List[re.Pattern[str]]:
        default_patterns = [
            re.compile(r"^extraTex/(?!@config\.tex$).+\.tex$"),
            re.compile(r"^references/.+\.bib$"),
        ]
        if not isinstance(config, dict):
            return default_patterns

        protection = config.get("template_protection") or {}
        if not isinstance(protection, dict):
            return default_patterns

        raw_patterns = protection.get("allowed_write_patterns")
        if not isinstance(raw_patterns, list) or not raw_patterns:
            return default_patterns

        compiled: List[re.Pattern[str]] = []
        for item in raw_patterns:
            if not isinstance(item, str) or not item.strip():
                continue
            compiled.append(re.compile(item))
        return compiled or default_patterns

    @staticmethod
    def for_new_project(
        new_project: Path,
        runs_root: Path,
        config: Optional[Dict[str, Any]] = None,
    ) -> "SecurityManager":
        new_project = new_project.resolve()
        runs_root = runs_root.resolve()
        return SecurityManager(
            allowed_writes=[
                AllowedWrite(
                    root=new_project,
                    patterns=SecurityManager._allowed_patterns_from_config(config),
                ),
                AllowedWrite(
                    root=runs_root,
                    patterns=[re.compile(r"^.+$")],
                ),
            ]
        )

    def assert_can_write(self, file_path: Path) -> None:
        file_path = file_path.resolve()

        for allowed in self.allowed_writes:
            try:
                rel = file_path.relative_to(allowed.root)
            except ValueError:
                continue

            rel_str = str(rel).replace("\\", "/")
            if self._is_blacklisted(rel_str):
                raise SystemFileModificationError(
                    f"禁止写入系统文件: {allowed.root}/{rel_str}（只允许修改正文内容层，如 extraTex/*.tex(排除@config.tex)、references/*.bib）"
                )

            if any(p.match(rel_str) for p in allowed.patterns):
                return

        raise SecurityError(
            "写入路径不在白名单中: "
            f"{file_path}\n"
            "允许范围：new_project 正文内容层（默认 extraTex/*.tex 排除 @config.tex、references/*.bib）以及 runs/**。"
        )
