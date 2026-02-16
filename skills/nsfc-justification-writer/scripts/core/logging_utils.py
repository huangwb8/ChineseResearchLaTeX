#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import logging


def configure_logging(*, verbose: bool = False) -> None:
    """
    统一脚本与核心模块的日志输出口径：
    - 默认：仅输出 WARNING 及以上（stderr）
    - --verbose：输出 DEBUG（stderr）
    """
    level = logging.DEBUG if verbose else logging.WARNING
    root = logging.getLogger()

    if not root.handlers:
        logging.basicConfig(level=level, format="%(message)s")
        return

    root.setLevel(level)
    for h in root.handlers:
        h.setLevel(level)
