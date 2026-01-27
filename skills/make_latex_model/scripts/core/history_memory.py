#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
历史记忆库（HistoryMemory）

将每轮优化的上下文/决策/结果落盘，避免重复“试错”。
实现保持极简：JSONL 追加写 + 最近 N 条读取。
"""

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class IterationRecord:
    iteration: int
    timestamp: str
    context: Dict[str, Any]
    decision: Dict[str, Any]
    result: Dict[str, Any]


class HistoryMemory:
    """基于 JSONL 文件的历史记忆库"""

    def __init__(self, storage_path: Path):
        self.storage_path = Path(storage_path)
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)

    def record(
        self,
        iteration: int,
        context: Dict[str, Any],
        decision: Dict[str, Any],
        result: Dict[str, Any],
    ) -> None:
        rec = IterationRecord(
            iteration=iteration,
            timestamp=datetime.now().isoformat(),
            context=context,
            decision=decision,
            result=result,
        )
        with open(self.storage_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec.__dict__, ensure_ascii=False) + "\n")

    def get_recent(self, n: int = 5) -> List[Dict[str, Any]]:
        if n <= 0 or not self.storage_path.exists():
            return []

        # 反向读取最后 N 行（文件通常不大；这里保持简单）
        try:
            lines = self.storage_path.read_text(encoding="utf-8").splitlines()
        except Exception:
            return []

        recent = []
        for line in lines[-n:]:
            try:
                recent.append(json.loads(line))
            except Exception:
                continue
        return recent

    def clear(self) -> None:
        if self.storage_path.exists():
            self.storage_path.unlink()

