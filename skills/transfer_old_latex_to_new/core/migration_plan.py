#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Literal, Optional


TaskType = Literal["copy_one_to_one", "placeholder_new_added", "needs_manual"]


@dataclass(frozen=True)
class MigrationTask:
    id: int
    type: TaskType
    priority: str
    source: Optional[str] = None
    target: Optional[str] = None
    confidence: Optional[str] = None
    score: Optional[float] = None
    reason: Optional[str] = None
    notes: Optional[str] = None


@dataclass(frozen=True)
class MigrationPlan:
    generated_at: str
    strategy: str
    tasks: List[MigrationTask] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "metadata": {
                "generated_at": self.generated_at,
                "strategy": self.strategy,
            },
            "tasks": [asdict(t) for t in self.tasks],
            "warnings": list(self.warnings),
        }


def build_plan_from_diff(structure_diff: Dict[str, Any], config: Dict[str, Any], strategy: str) -> MigrationPlan:
    tasks: List[MigrationTask] = []
    warnings: List[str] = []
    task_id = 1

    one_to_one = (((structure_diff or {}).get("mapping") or {}).get("one_to_one") or [])
    low_conf = (((structure_diff or {}).get("mapping") or {}).get("low_confidence") or [])
    new_added = (((structure_diff or {}).get("mapping") or {}).get("new_added") or [])
    removed = (((structure_diff or {}).get("mapping") or {}).get("removed") or [])

    for item in one_to_one:
        tasks.append(
            MigrationTask(
                id=task_id,
                type="copy_one_to_one",
                priority="high" if item.get("confidence") == "high" else "medium",
                source=item.get("old"),
                target=item.get("new"),
                confidence=item.get("confidence"),
                score=item.get("score"),
                reason=item.get("reason"),
            )
        )
        task_id += 1

    for item in low_conf:
        tasks.append(
            MigrationTask(
                id=task_id,
                type="needs_manual",
                priority="medium",
                source=item.get("old"),
                target=item.get("new"),
                confidence="low",
                reason=item.get("reason"),
                notes="低置信度映射：默认不自动写入，建议人工确认后再迁移。",
            )
        )
        task_id += 1

    placeholder = ((config.get("migration", {}) or {}).get("content_generation", {}) or {}).get(
        "placeholder_text", "\\textbf{[此部分内容需要补充]}"
    )
    for item in new_added:
        tasks.append(
            MigrationTask(
                id=task_id,
                type="placeholder_new_added",
                priority="low",
                target=item.get("file"),
                notes=f"新模板新增章节：默认写入占位符：{placeholder}",
            )
        )
        task_id += 1

    if removed:
        warnings.append(f"存在 {len(removed)} 个旧章节未映射（将导出到 deliverables 供人工处理）。")

    return MigrationPlan(
        generated_at=datetime.now().isoformat(timespec="seconds"),
        strategy=strategy,
        tasks=tasks,
        warnings=warnings,
    )

