#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

class SkillError(Exception):
    """
    统一的 Skill 异常基类：携带可读的修复建议（供 CLI 友好输出）。
    """

    def __init__(self, message: str, *, fix_suggestion: str = "") -> None:
        super().__init__(message)
        self.fix_suggestion = str(fix_suggestion or "").strip()


class BackupNotFoundError(SkillError):
    def __init__(self, run_id: str) -> None:
        self.run_id = run_id
        super().__init__(
            f"未找到 run_id={run_id} 的备份文件",
            fix_suggestion=(
                "建议：先运行 `list-runs` 查看可用 run_id；\n"
                "或检查 `config.yaml:workspace.runs_dir` 是否指向正确的任务级工作区。"
            ),
        )
