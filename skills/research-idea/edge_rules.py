"""research-idea 专属的阶段边语义；协议、Gate 和哈希由 BSK 负责。"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable

PREFIX = "bensz.research-ideation."
EDGE_APPLICABILITY = {
    (PREFIX + "literature", PREFIX + "candidates"): "not_applicable",
    (PREFIX + "candidates", PREFIX + "review"): "applicable",
    (PREFIX + "review", PREFIX + "reporting"): "not_applicable",
    (PREFIX + "reporting", PREFIX + "completed"): "applicable",
}


def applicability_errors(source: str, target: str, results: Iterable[dict[str, Any]]) -> list[str]:
    expected = EDGE_APPLICABILITY.get((source, target))
    if expected is None:
        return []
    errors: list[str] = []
    for result in results:
        if result.get("verifier_id") != "bensz.research.hypothesis-merit":
            continue
        facts = result.get("facts") if isinstance(result.get("facts"), dict) else {}
        actual = facts.get("applicability")
        if actual is None:
            continue
        if actual != expected:
            errors.append(f"merit_applicability_mismatch: {source} -> {target} 期望 {expected}，实际 {actual}")
    return errors


def reviewer_receipt_errors(project_root: Path, reviewer: dict[str, Any], label: str) -> list[str]:
    """对账 reviewer 领域摘要；BSK 只负责协议身份，不解释这些字段。"""
    errors: list[str] = []
    paths: dict[str, Path] = {}
    for key in ("thread_path", "done_path", "path"):
        raw = reviewer.get(key)
        if not isinstance(raw, str) or not raw.strip():
            errors.append(f"reviewer_receipt_mismatch: {label} 缺少 {key}")
            continue
        candidate = (project_root / raw).resolve()
        if not candidate.is_relative_to(project_root) or not candidate.is_file() or candidate.is_symlink():
            errors.append(f"reviewer_receipt_mismatch: {label} {key} 路径无效")
        else:
            paths[key] = candidate
    decoded: dict[str, Any] = {}
    for key in ("thread_path", "done_path"):
        if key in paths:
            try:
                decoded[key] = json.loads(paths[key].read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                errors.append(f"reviewer_receipt_mismatch: {label} {key} 不是合法 JSON")
    fields = ("thread_id", "model", "input_snapshot_hash", "started_at", "ended_at", "thread_status", "runner_status", "output_hash")
    for field in fields:
        expected = reviewer.get(field)
        if expected is None:
            errors.append(f"reviewer_receipt_mismatch: {label} 缺少 {field}")
            continue
        receipt_key = "status" if field in {"thread_status", "runner_status"} else field
        sources = [value.get(receipt_key) for value in decoded.values() if isinstance(value, dict) and receipt_key in value]
        if sources and expected not in sources:
            errors.append(f"reviewer_receipt_mismatch: {label} 字段 {field} 与原始回执不一致")
    return errors
