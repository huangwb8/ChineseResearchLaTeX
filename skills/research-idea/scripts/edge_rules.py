"""research-idea 专属领域规则；协议、Gate 和哈希由 BSK 负责。"""
from __future__ import annotations

import json
import hashlib
import re
from pathlib import Path
from typing import Any, Iterable

PREFIX = "bensz.research-ideation."
EDGE_APPLICABILITY = {
    (PREFIX + "literature", PREFIX + "candidates"): "not_applicable",
    (PREFIX + "candidates", PREFIX + "review"): "applicable",
    (PREFIX + "review", PREFIX + "reporting"): "not_applicable",
    (PREFIX + "reporting", PREFIX + "completed"): "applicable",
}
REVIEWER_RECEIPT_SCHEMA = "research-idea-reviewer-receipt-v1"
INTERPRETATION_RECEIPT_SCHEMA = "research-idea-interpretation-receipt-v1"
INTERPRETATION_CONTRACT = "research-literature-interpretation-evidence-v1"
_AGENT_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")


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
    if reviewer.get("receipt_schema") != REVIEWER_RECEIPT_SCHEMA:
        errors.append(f"reviewer_receipt_mismatch: {label} receipt_schema 未知")
    paths: dict[str, Path] = {}
    for key in ("thread_path", "done_path", "path"):
        raw = reviewer.get(key)
        if not isinstance(raw, str) or not raw.strip():
            errors.append(f"reviewer_receipt_mismatch: {label} 缺少 {key}")
            continue
        unresolved = project_root / raw
        candidate = unresolved.resolve()
        if unresolved.is_symlink() or not candidate.is_relative_to(project_root) or not candidate.is_file():
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
    thread = decoded.get("thread_path") if isinstance(decoded.get("thread_path"), dict) else {}
    done = decoded.get("done_path") if isinstance(decoded.get("done_path"), dict) else {}
    runner = thread.get("runner") if isinstance(thread.get("runner"), dict) else {}
    exit_code = done.get("exit_code")
    runner_status = done.get("runner_status") or done.get("status")
    if runner_status is None and isinstance(exit_code, int):
        runner_status = "completed" if exit_code == 0 else "failed"
    expected_sources = {
        "thread_id": thread.get("thread_id"),
        "agent_id": thread.get("agent_id"),
        "agent_label": thread.get("agent_label") or thread.get("role"),
        "model": thread.get("model") or runner.get("model"),
        "input_snapshot_hash": thread.get("input_snapshot_hash"),
        "thread_status": thread.get("thread_status") or thread.get("status"),
        "runner_status": runner_status,
        "started_at": done.get("started_at") or done.get("start_at"),
        "ended_at": done.get("ended_at") or done.get("end_at"),
        "exit_code": exit_code,
    }
    for field, actual in expected_sources.items():
        expected = reviewer.get(field)
        if expected is None:
            errors.append(f"reviewer_receipt_mismatch: {label} 缺少 {field}")
        elif actual is None:
            errors.append(f"reviewer_receipt_mismatch: {label} 原始回执缺少 {field}")
        elif expected != actual:
            errors.append(f"reviewer_receipt_mismatch: {label} 字段 {field} 与原始回执不一致")
    agent_id = reviewer.get("agent_id")
    if not isinstance(agent_id, str) or not _AGENT_ID_RE.fullmatch(agent_id):
        errors.append(f"reviewer_receipt_mismatch: {label} agent_id 非 canonical 标识")
    if reviewer.get("thread_status") != "completed":
        errors.append(f"reviewer_receipt_mismatch: {label} thread_status 未完成")
    if reviewer.get("runner_status") != "completed" or reviewer.get("exit_code") != 0:
        errors.append(f"reviewer_receipt_mismatch: {label} runner 未成功完成")
    result_path = paths.get("path")
    if result_path is not None:
        actual_hash = "sha256:" + hashlib.sha256(result_path.read_bytes()).hexdigest()
        if reviewer.get("output_hash") != actual_hash:
            errors.append(f"reviewer_receipt_mismatch: {label} output_hash 与 RESULT 不一致")
    return errors


def _frontmatter(path: Path) -> dict[str, str]:
    """读取论文解读契约使用的简单标量 frontmatter。"""
    text = path.read_text(encoding="utf-8")
    match = re.match(r"\A---\n(.*?)\n---(?:\n|$)", text, re.S)
    if not match:
        return {}
    fields: dict[str, str] = {}
    for line in match.group(1).splitlines():
        key, separator, value = line.partition(":")
        if separator and re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", key.strip()):
            fields[key.strip()] = value.strip().strip("'\"")
    return fields


def _scoped_file(task_root: Path, raw: Any) -> Path | None:
    if not isinstance(raw, str) or not raw.strip():
        return None
    unresolved = task_root / raw
    candidate = unresolved.resolve()
    if unresolved.is_symlink() or not candidate.is_relative_to(task_root) or not candidate.is_file():
        return None
    return candidate


def completion_evidence_errors(task_root: Path, index_path: Path) -> list[dict[str, str]]:
    """确定性核对 completion index 与论文/回执源 artifact；未知结构 fail-closed。"""
    errors: list[dict[str, str]] = []

    def add(code: str, message: str) -> None:
        errors.append({"code": code, "message": message})

    task_root = task_root.resolve()
    unresolved_index = index_path
    index_path = unresolved_index.resolve()
    if unresolved_index.is_symlink() or not index_path.is_relative_to(task_root) or not index_path.is_file():
        add("completion_evidence_invalid", "completion evidence 不在任务根内或不是普通文件")
        return errors
    try:
        index = json.loads(index_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        add("completion_evidence_invalid", "completion evidence 不是合法 JSON")
        return errors
    if not isinstance(index, dict):
        add("completion_evidence_invalid", "completion evidence 顶层必须是对象")
        return errors
    dependencies = index.get("dependencies")
    if not isinstance(dependencies, dict):
        add("completion_evidence_invalid", "completion evidence 缺少 dependencies")
        return errors
    raw_interpretations = dependencies.get("research-literature-interpretation", [])
    interpretations = raw_interpretations if isinstance(raw_interpretations, list) else [raw_interpretations]
    for position, record in enumerate(interpretations, start=1):
        label = f"论文解读 {position}"
        if not isinstance(record, dict):
            add("interpretation_record_invalid", f"{label} 索引不是对象")
            continue
        note = _scoped_file(task_root, record.get("path"))
        if note is None:
            add("interpretation_path_invalid", f"{label} 路径无效")
            continue
        metadata = _frontmatter(note)
        if metadata.get("interpretation_contract") != INTERPRETATION_CONTRACT:
            add("interpretation_contract_mismatch", f"{label} interpretation_contract 不匹配")
        for field in ("source_id", "evidence_depth", "read_scope", "stable_citation"):
            if not isinstance(record.get(field), str) or record.get(field) != metadata.get(field):
                add("interpretation_metadata_mismatch", f"{label} {field} 与源解读不一致")
        receipt = record.get("execution_receipt")
        if not isinstance(receipt, dict) or receipt.get("schema") != INTERPRETATION_RECEIPT_SCHEMA:
            add("interpretation_receipt_invalid", f"{label} 缺少版本化 execution_receipt")
        else:
            mode = receipt.get("identity_proof")
            if mode not in {"host-agent", "isolated-task"}:
                add("interpretation_receipt_invalid", f"{label} identity_proof 未知")
            for field in ("task_id", "status", "input_snapshot_hash", "output_hash"):
                if receipt.get(field) in (None, ""):
                    add("interpretation_receipt_invalid", f"{label} execution_receipt 缺少 {field}")
            if receipt.get("status") != "completed":
                add("interpretation_receipt_invalid", f"{label} 解读任务未完成")
            if mode == "host-agent" and (
                not isinstance(receipt.get("agent_id"), str)
                or not _AGENT_ID_RE.fullmatch(receipt["agent_id"])
            ):
                add("interpretation_receipt_invalid", f"{label} host-agent 缺少 canonical agent_id")
            actual_note_hash = "sha256:" + hashlib.sha256(note.read_bytes()).hexdigest()
            if receipt.get("output_hash") != actual_note_hash:
                add("interpretation_receipt_invalid", f"{label} output_hash 与解读文件不一致")
        if record.get("evidence_depth") == "fulltext":
            fulltext = record.get("fulltext_source")
            if not isinstance(fulltext, dict):
                add("fulltext_source_missing", f"{label} fulltext 缺少源文件绑定")
                continue
            source = _scoped_file(task_root, fulltext.get("path"))
            if source is None:
                add("fulltext_source_invalid", f"{label} fulltext_source 路径无效")
            else:
                actual_hash = "sha256:" + hashlib.sha256(source.read_bytes()).hexdigest()
                if fulltext.get("sha256") != actual_hash:
                    add("fulltext_source_hash_mismatch", f"{label} fulltext_source 哈希不一致")

    review = index.get("review")
    if isinstance(review, dict) and isinstance(review.get("rounds"), list):
        for round_item in review["rounds"]:
            if not isinstance(round_item, dict) or not isinstance(round_item.get("reviewers"), list):
                continue
            for reviewer_no, reviewer in enumerate(round_item["reviewers"], start=1):
                if not isinstance(reviewer, dict):
                    continue
                label = f"第 {round_item.get('round')} 轮 reviewer {reviewer_no}"
                for message in reviewer_receipt_errors(task_root, reviewer, label):
                    add("reviewer_receipt_mismatch", message)
    return errors
