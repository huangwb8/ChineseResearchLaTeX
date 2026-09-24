#!/usr/bin/env python3
"""Fail-closed consistency check for research-idea completion evidence."""
from __future__ import annotations

import json
from pathlib import Path
import sys
from typing import Any

SKILL_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(SKILL_ROOT / "scripts"))

from edge_rules import completion_evidence_errors  # noqa: E402


def verify(request: dict[str, Any]) -> dict[str, Any]:
    subject = request.get("subject") if isinstance(request.get("subject"), dict) else {}
    context = request.get("context") if isinstance(request.get("context"), dict) else {}
    target = subject.get("target")
    if target != "bensz.research-ideation.completed":
        return {
            "verdict": "pass",
            "facts": {"applicability": "not_applicable", "evidence_consistent": True},
            "findings": [],
        }
    task_root = context.get("task_root")
    index_path = context.get("completion_evidence_path")
    if not isinstance(task_root, str) or not isinstance(index_path, str):
        findings = [{
            "id": "completion_evidence_missing",
            "verdict": "fail",
            "message": "reporting -> completed 需要 task_root 与 completion_evidence_path",
        }]
    else:
        findings = [
            {"id": item["code"], "verdict": "fail", "message": item["message"]}
            for item in completion_evidence_errors(Path(task_root), Path(index_path))
        ]
    return {
        "verdict": "fail" if findings else "pass",
        "facts": {
            "applicability": "applicable",
            "evidence_consistent": not findings,
            "checked_index": "research-idea/output/completion-evidence.json",
        },
        "findings": findings,
    }


def main() -> int:
    request = json.load(sys.stdin)
    json.dump(verify(request), sys.stdout, ensure_ascii=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
