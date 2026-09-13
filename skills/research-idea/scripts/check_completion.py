#!/usr/bin/env python3
"""检查 research-idea 最终交付是否具备完整完成证据。"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from validate_report import validate_report

PREFIX = "bensz.research-ideation."
COMPLETED = PREFIX + "completed"
FORWARD_TARGETS = {
    "bensz.workspace.ready": PREFIX + "literature",
    PREFIX + "literature": PREFIX + "candidates",
    PREFIX + "candidates": PREFIX + "review",
    PREFIX + "review": PREFIX + "reporting",
    PREFIX + "reporting": COMPLETED,
}
REQUIRED_DEPENDENCIES = {
    "exploration": (
        "research-topic-extractor",
        "research-literature-radar",
        "research-literature-interpretation",
    ),
    "novelty": ("research-literature-review",),
}


def load_json(path: Path, errors: list[str], label: str) -> dict[str, Any]:
    if not path.is_file():
        errors.append(f"缺少{label}: {path}")
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        errors.append(f"{label}不是合法 JSON: {exc}")
        return {}
    if not isinstance(data, dict):
        errors.append(f"{label}必须是对象")
        return {}
    return data


def read_events(path: Path, errors: list[str]) -> list[dict[str, Any]]:
    if not path.is_file():
        errors.append(f"缺少 bsk 事件日志: {path}")
        return []
    events: list[dict[str, Any]] = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError as exc:
            errors.append(f"事件日志第 {line_no} 行不是合法 JSON: {exc}")
            continue
        if isinstance(event, dict):
            events.append(event)
        else:
            errors.append(f"事件日志第 {line_no} 行不是对象")
    return events


def project_relative_path(project_root: Path, raw: Any, errors: list[str], label: str) -> Path | None:
    if not isinstance(raw, str) or not raw.strip():
        errors.append(f"{label} 缺少相对路径")
        return None
    path = (project_root / raw).resolve()
    try:
        path.relative_to(project_root)
    except ValueError:
        errors.append(f"{label} 超出允许范围: {raw}")
        return None
    return path


def require_nonempty_file(project_root: Path, raw: Any, errors: list[str], label: str) -> Path | None:
    path = project_relative_path(project_root, raw, errors, label)
    if path is None:
        return None
    if not path.is_file():
        errors.append(f"{label} 不存在或不是文件: {raw}")
        return None
    if path.is_symlink():
        errors.append(f"{label} 不得使用符号链接: {raw}")
        return None
    if path.stat().st_size == 0:
        errors.append(f"{label} 是空文件: {raw}")
    return path


def file_snapshot(path: Path) -> dict[str, Any]:
    """返回可复核的内容快照；不把原始内容写入索引。"""
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    stat = path.stat()
    return {
        "sha256": f"sha256:{digest}",
        "size": stat.st_size,
        "mtime_ns": stat.st_mtime_ns,
    }


def check_snapshot(path: Path, record: dict[str, Any], errors: list[str], label: str) -> None:
    """若索引提供 snapshot，则校验内容、大小和修改时间均未变化。"""
    snapshot = record.get("snapshot")
    # 兼容早期扁平字段，同时优先使用 snapshot 对象。
    if snapshot is None and any(key in record for key in ("content_hash", "sha256", "size", "mtime_ns")):
        snapshot = {key: record[key] for key in ("content_hash", "sha256", "size", "mtime_ns") if key in record}
    if snapshot is None:
        return
    if not isinstance(snapshot, dict):
        errors.append(f"{label} snapshot 必须是对象")
        return
    actual = file_snapshot(path)
    if "output_hash" in record and record["output_hash"] != actual["sha256"]:
        errors.append(f"{label} output_hash 与文件内容不一致")
    if "content_hash" in snapshot and snapshot["content_hash"] != actual["sha256"]:
        errors.append(f"{label} content_hash 与证据快照不一致")
    for key in ("sha256", "size", "mtime_ns"):
        if key in snapshot and snapshot[key] != actual[key]:
            errors.append(f"{label} {key} 与证据快照不一致")


def check_binding(record: dict[str, Any], run_id: str | None, attempt_id: str | None, errors: list[str], label: str) -> None:
    """校验新索引中的来源是否属于完成转移的同一 run/attempt。"""
    for key, expected in (("run_id", run_id), ("attempt_id", attempt_id)):
        if key in record and expected is not None and record[key] != expected:
            errors.append(f"{label} {key} 不属于 completed 的当前 attempt")


def records(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if isinstance(value, dict):
        if isinstance(value.get("artifacts"), list):
            return value["artifacts"]
        return [value]
    if isinstance(value, str):
        return [value]
    return []


def record_path(record: Any) -> Any:
    if isinstance(record, str):
        return record
    if isinstance(record, dict):
        return record.get("path")
    return None


def record_status(record: Any) -> str | None:
    if isinstance(record, dict) and isinstance(record.get("status"), str):
        return record["status"]
    return None


def check_dependency_index(index: dict[str, Any], task_root: Path, manifest: dict[str, Any], report: dict[str, Any], errors: list[str], *, run_id: str | None = None, attempt_id: str | None = None) -> None:
    dependencies = index.get("dependencies")
    strict = index.get("schema") in {"research-idea-completion-v2", "research-idea-completion-v3"}
    if not isinstance(dependencies, dict):
        errors.append("完成证据索引缺少 dependencies 对象")
        dependencies = {}
    raw_statuses = report.get("execution_statuses") if isinstance(report.get("execution_statuses"), dict) else {}
    statuses = {key: raw_statuses.get(key) for key in ("exploration", "novelty", "review")}
    required = list(REQUIRED_DEPENDENCIES["exploration"]) if statuses["exploration"] == "complete" else []
    if statuses["novelty"] == "complete":
        required.extend(REQUIRED_DEPENDENCIES["novelty"])
    for skill in required:
        items = records(dependencies.get(skill))
        if not items:
            errors.append(f"缺少依赖 Skill 可复核产物: {skill}")
            continue
        for index_no, item in enumerate(items, start=1):
            status = record_status(item)
            if status and status not in {"complete", "completed", "pass", "passed", "not_required"}:
                errors.append(f"{skill} 第 {index_no} 个产物状态不是完成: {status}")
            path = require_nonempty_file(task_root, record_path(item), errors, f"{skill} 产物 {index_no}")
            if path is not None and isinstance(item, dict):
                check_snapshot(path, item, errors, f"{skill} 产物 {index_no}")
                if strict:
                    if not isinstance(item.get("snapshot"), dict) and "content_hash" not in item:
                        errors.append(f"{skill} 产物 {index_no} 缺少内容快照")
                    check_binding(item, run_id, attempt_id, errors, f"{skill} 产物 {index_no}")
                    if not isinstance(item.get("source_id"), str) or not item["source_id"].strip():
                        errors.append(f"{skill} 产物 {index_no} 缺少稳定 source_id")
                    if skill == "research-literature-interpretation":
                        for field in ("evidence_depth", "read_scope", "stable_citation"):
                            if not isinstance(item.get(field), str) or not item[field].strip():
                                errors.append(f"{skill} 产物 {index_no} 缺少 {field}")
                    if skill == "research-literature-review":
                        for field in ("evidence_depth", "equivalence_checked", "multi_source"):
                            if field not in item:
                                errors.append(f"{skill} 产物 {index_no} 缺少 {field}")
                        if item.get("evidence_depth") not in {"fulltext", "full-text", "全文"} or item.get("equivalence_checked") is not True or item.get("multi_source") is not True:
                            errors.append(f"{skill} 产物 {index_no} 未达到 Premium 全文/多源/等价性门禁")

    if statuses["review"] == "complete":
        review = index.get("review")
        if not isinstance(review, dict):
            errors.append("完成证据索引缺少 review 对象")
            return
        rounds = manifest.get("settings", {}).get("rounds", 3)
        agents = manifest.get("settings", {}).get("agents", 3)
        try:
            rounds = int(rounds)
            agents = int(agents)
        except (TypeError, ValueError):
            errors.append("manifest 中 rounds/agents 不是整数")
            return
        round_items = review.get("rounds")
        if not isinstance(round_items, list):
            errors.append("review.rounds 必须列出每轮独立审查证据")
            return
        by_round = {item.get("round"): item for item in round_items if isinstance(item, dict)}
        for round_no in range(1, rounds + 1):
            item = by_round.get(round_no)
            if not isinstance(item, dict):
                errors.append(f"缺少第 {round_no} 轮审查证据")
                continue
            reviewers = item.get("reviewers")
            if not isinstance(reviewers, list):
                errors.append(f"第 {round_no} 轮缺少 reviewers 列表")
                continue
            reviewer_ids = [entry.get("id") for entry in reviewers if isinstance(entry, dict)]
            if len(set(reviewer_ids)) < agents:
                errors.append(f"第 {round_no} 轮独立审查者不足: 需要 {agents}，实际 {len(set(reviewer_ids))}")
            for reviewer_no, reviewer in enumerate(reviewers, start=1):
                if not isinstance(reviewer, dict):
                    errors.append(f"第 {round_no} 轮第 {reviewer_no} 个 reviewer 不是对象")
                    continue
                path = require_nonempty_file(task_root, reviewer.get("path"), errors, f"第 {round_no} 轮 reviewer {reviewer_no}")
                if path is not None:
                    check_snapshot(path, reviewer, errors, f"第 {round_no} 轮 reviewer {reviewer_no}")
                if strict:
                    if not isinstance(reviewer.get("snapshot"), dict) and "output_hash" not in reviewer:
                        errors.append(f"第 {round_no} 轮 reviewer {reviewer_no} 缺少输出快照")
                    required = ("thread_id", "model", "input_snapshot_hash", "output_hash", "started_at", "ended_at")
                    for field in required:
                        if not isinstance(reviewer.get(field), str) or not reviewer[field].strip():
                            errors.append(f"第 {round_no} 轮 reviewer {reviewer_no} 缺少 {field}")
                    if reviewer.get("review_type") == "synthetic_review" or reviewer.get("independent") is False:
                        errors.append(f"第 {round_no} 轮 reviewer {reviewer_no} 不能计入独立审查")
                    check_binding(reviewer, run_id, attempt_id, errors, f"第 {round_no} 轮 reviewer {reviewer_no}")
            require_nonempty_file(task_root, item.get("summary_path"), errors, f"第 {round_no} 轮汇总")
        synthesis = require_nonempty_file(task_root, review.get("synthesis_path"), errors, "独立审查总综合")
        if strict:
            if not isinstance(review.get("synthesis"), dict):
                errors.append("review 缺少 authoritative synthesis 元数据")
            check_binding(review, run_id, attempt_id, errors, "独立审查总综合")


def check_completion_layers(index: dict[str, Any], report: dict[str, Any], errors: list[str]) -> None:
    """新契约把流程完成与证据/结论资格拆成四层。"""
    layers = index.get("completion_layers")
    if layers is None:
        if index.get("schema") in {"research-idea-completion-v2", "research-idea-completion-v3"}:
            errors.append("新完成证据索引缺少 completion_layers")
        return
    if not isinstance(layers, dict):
        errors.append("completion_layers 必须是对象")
        return
    required = ("artifact_ready", "execution_recorded", "evidence_sufficient", "claim_eligible")
    for key in required:
        if layers.get(key) is not True:
            errors.append(f"完成层 {key} 未满足")
    if report.get("outcome") in {"recommended", "no_qualified"} and layers.get("claim_eligible") is not True:
        errors.append("正式结论要求 claim_eligible=true")


def first_control_break(
    events: list[dict[str, Any]], current_state: Any, required_verifiers: list[str]
) -> dict[str, Any] | None:
    """定位 State 身份链上第一个可复核断点，不改写历史事件。"""
    transitions = [
        (position, event)
        for position, event in enumerate(events)
        if event.get("type") == "state.transition"
        and event.get("payload", {}).get("skill") == "research-idea"
    ]
    if not transitions:
        return {
            "code": "initial_state_transition_missing",
            "current_state": current_state,
            "expected_target": PREFIX + "literature",
        }

    expected_source = "bensz.workspace.ready"
    first_identity: tuple[Any, Any] | None = None
    for transition_index, (position, event) in enumerate(transitions):
        payload = event.get("payload", {})
        identity = (event.get("run_id"), event.get("attempt_id"))
        if first_identity is None:
            first_identity = identity
            if (
                not isinstance(identity[0], str)
                or not identity[0]
                or not isinstance(identity[1], str)
                or not identity[1]
                or identity[1] == "default"
            ):
                return {
                    "code": "state_entry_identity_missing",
                    "event_id": event.get("event_id"),
                    "state": payload.get("to_state"),
                }
        elif identity != first_identity:
            return {
                "code": "state_entry_identity_changed",
                "event_id": event.get("event_id"),
                "expected_run_id": first_identity[0],
                "expected_attempt_id": first_identity[1],
                "actual_run_id": identity[0],
                "actual_attempt_id": identity[1],
            }
        if payload.get("from_state") != expected_source:
            return {
                "code": "state_chain_discontinuous",
                "event_id": event.get("event_id"),
                "expected_from": expected_source,
                "actual_from": payload.get("from_state"),
            }
        if transition_index > 0:
            previous_position = transitions[transition_index - 1][0]
            segment_gates = [
                item for item in events[previous_position + 1:position]
                if item.get("type") == "verification.gate"
            ]
            matching_gates = [
                item for item in segment_gates
                if (item.get("run_id"), item.get("attempt_id")) == identity
            ]
            if not matching_gates:
                return {
                    "code": "gate_missing_before_transition",
                    "event_id": event.get("event_id"),
                    "from_state": expected_source,
                    "to_state": payload.get("to_state"),
                }
            gate = matching_gates[-1]
            if gate.get("payload", {}).get("decision") not in {"allow", "allow_with_warnings"}:
                return {
                    "code": "non_allow_gate_before_transition",
                    "gate_event_id": gate.get("event_id"),
                    "event_id": event.get("event_id"),
                    "decision": gate.get("payload", {}).get("decision"),
                }
            result_refs = set(gate.get("payload", {}).get("result_refs") or [])
            missing_refs = [item for item in required_verifiers if item not in result_refs]
            if missing_refs:
                return {
                    "code": "required_verifiers_missing_before_transition",
                    "gate_event_id": gate.get("event_id"),
                    "event_id": event.get("event_id"),
                    "missing": missing_refs,
                }
        expected_target = FORWARD_TARGETS.get(expected_source)
        if payload.get("to_state") != expected_target:
            return {
                "code": "unsupported_rework_transition",
                "event_id": event.get("event_id"),
                "from_state": expected_source,
                "actual_target": payload.get("to_state"),
                "expected_target": expected_target,
            }
        expected_source = str(payload.get("to_state"))

    entry_position, entry = transitions[-1]
    entry_state = entry.get("payload", {}).get("to_state")
    if entry_state != current_state:
        return {
            "code": "state_snapshot_event_mismatch",
            "event_id": entry.get("event_id"),
            "snapshot_state": current_state,
            "event_state": entry_state,
        }
    if current_state == COMPLETED:
        return None

    entry_identity = (entry.get("run_id"), entry.get("attempt_id"))
    gates = [
        event for event in events[entry_position + 1:]
        if event.get("type") == "verification.gate"
    ]
    for gate in gates:
        gate_identity = (gate.get("run_id"), gate.get("attempt_id"))
        if gate_identity != entry_identity:
            return {
                "code": "state_entry_identity_mismatch",
                "entry_event_id": entry.get("event_id"),
                "gate_event_id": gate.get("event_id"),
                "entry_run_id": entry_identity[0],
                "entry_attempt_id": entry_identity[1],
                "gate_run_id": gate_identity[0],
                "gate_attempt_id": gate_identity[1],
            }
        decision = gate.get("payload", {}).get("decision")
        if decision not in {"allow", "allow_with_warnings"}:
            return {
                "code": "verifier_gate_rejected",
                "gate_event_id": gate.get("event_id"),
                "decision": decision,
                "current_state": current_state,
            }
        return {
            "code": "transition_missing_after_allow_gate",
            "gate_event_id": gate.get("event_id"),
            "current_state": current_state,
            "expected_target": FORWARD_TARGETS.get(str(current_state)),
        }
    return {
        "code": "verifier_or_gate_missing",
        "entry_event_id": entry.get("event_id"),
        "current_state": current_state,
        "expected_target": FORWARD_TARGETS.get(str(current_state)),
    }


def check_state_and_gate(task_root: Path, required_verifiers: list[str], errors: list[str]) -> dict[str, Any]:
    meta = load_json(task_root / "research-idea/log/meta-state.json", errors, "领域状态快照")
    events = read_events(task_root / "log/events.ndjson", errors)
    current_state = meta.get("current_state")
    control_break = first_control_break(events, current_state, required_verifiers)
    if control_break is not None:
        errors.append(f"控制链首个断点: {control_break['code']}")
    if current_state != COMPLETED:
        errors.append(f"运行状态未到 completed: 当前为 {current_state or 'unknown'}")
    completed_events = [
        event for event in events
        if event.get("type") == "state.transition"
        and event.get("payload", {}).get("skill") == "research-idea"
        and event.get("payload", {}).get("to_state") == COMPLETED
    ]
    if not completed_events:
        errors.append("事件日志缺少 reporting -> completed 转移")
        return {
            "current_state": current_state,
            "event_count": len(events),
            "completed_transition": None,
            "first_control_break": control_break,
        }
    completed_event = completed_events[-1]
    run_id = completed_event.get("run_id")
    attempt_id = completed_event.get("attempt_id")
    # 完成只能来自 reporting，且 manifest 若声明身份必须一致。
    if completed_event.get("payload", {}).get("from_state") != PREFIX + "reporting":
        errors.append("completed 转移不是 reporting -> completed")
    gates = [
        event for event in events
        if event.get("type") == "verification.gate"
        and event.get("run_id") == run_id
        and event.get("attempt_id") == attempt_id
        and event.get("payload", {}).get("decision") == "allow"
    ]
    if not gates:
        errors.append("缺少与 completed 转移同 run/attempt 的 allow Gate")
    else:
        result_refs = set(gates[-1].get("payload", {}).get("result_refs") or [])
        missing = [item for item in required_verifiers if item not in result_refs]
        if missing:
            errors.append("completed Gate 未覆盖全部 required Verifier: " + ", ".join(missing))
    return {
        "current_state": current_state,
        "event_count": len(events),
        "completed_transition": {"run_id": run_id, "attempt_id": attempt_id},
        "gate_count": len(gates),
        "run_id": run_id,
        "attempt_id": attempt_id,
        "first_control_break": control_break,
    }


def check_completion(project_root: Path, task_root: Path, report_path: Path | None = None, evidence_index: Path | None = None) -> dict[str, Any]:
    project_root = project_root.expanduser().resolve()
    task_root = task_root.expanduser()
    if not task_root.is_absolute():
        task_root = (project_root / task_root).resolve()
    errors: list[str] = []
    warnings: list[str] = []
    try:
        task_root.relative_to(project_root)
    except ValueError:
        errors.append("task-root 必须位于项目内")
    workspace = load_json(task_root / ".workspace.json", errors, "任务工作区声明")
    if workspace and workspace.get("protocol") != "bensz-api-task-v1":
        errors.append("任务工作区协议不是 bensz-api-task-v1")
    manifest = load_json(task_root / "research-idea/input/manifest.json", errors, "research-idea manifest")
    if report_path is None and isinstance(manifest.get("output_path"), str):
        report_path = project_relative_path(project_root, manifest["output_path"], errors, "manifest.output_path")
    elif report_path is not None and not report_path.is_absolute():
        report_path = (project_root / report_path).resolve()
    if report_path is None:
        report_result = {"passed": False, "completion_eligible": False, "errors": ["缺少最终报告路径"]}
        errors.append("缺少最终报告路径")
    else:
        if not bool(manifest.get("settings", {}).get("allow_custom_name")) and isinstance(manifest.get("output_path"), str):
            expected = project_relative_path(project_root, manifest["output_path"], errors, "manifest.output_path")
            if expected is not None and report_path.resolve() != expected.resolve():
                errors.append("最终报告路径与 manifest.output_path 不一致")
        allow_custom_name = bool(manifest.get("settings", {}).get("allow_custom_name"))
        report_result = validate_report(report_path, allow_custom_name=allow_custom_name, project_root=project_root)
        for error in report_result.get("errors", []):
            errors.append(f"报告校验失败: {error}")
    if report_result.get("outcome") == "insufficient":
        errors.append("insufficient 是阶段性评估，不能进入 completed")
    elif not report_result.get("completion_eligible"):
        errors.append("报告不具备完成资格")

    if evidence_index is None:
        evidence_index = task_root / "research-idea/output/completion-evidence.json"
    elif not evidence_index.is_absolute():
        evidence_index = (project_root / evidence_index).resolve()
    index = load_json(evidence_index, errors, "完成证据索引")
    state_result = None
    # 先读取最后一次完成事件，供证据索引做 run/attempt 绑定检查。
    probe_events = read_events(task_root / "log/events.ndjson", [])
    completed_probe = [e for e in probe_events if e.get("type") == "state.transition" and e.get("payload", {}).get("to_state") == COMPLETED]
    current_run = completed_probe[-1].get("run_id") if completed_probe else None
    current_attempt = completed_probe[-1].get("attempt_id") if completed_probe else None
    if index:
        check_completion_layers(index, report_result, errors)
        if index.get("schema") in {"research-idea-completion-v2", "research-idea-completion-v3"}:
            if not isinstance(index.get("run_id"), str) or not isinstance(index.get("attempt_id"), str):
                errors.append("新完成证据索引必须包含字符串 run_id/attempt_id")
            if index.get("run_id") != current_run or index.get("attempt_id") != current_attempt:
                errors.append("完成证据索引与 completed 事件的 run/attempt 不一致")
            if not isinstance(index.get("authoritative_attempt"), dict):
                errors.append("新完成证据索引缺少 authoritative_attempt")
        check_dependency_index(index, task_root, manifest, report_result, errors, run_id=current_run, attempt_id=current_attempt)

    required_verifiers = []
    config_path = Path(__file__).resolve().parents[1] / "config.yaml"
    try:
        import yaml
        config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
        required_verifiers = [
            f"{item['id']}@{item['version']}"
            for item in config.get("runtime", {}).get("verifiers", [])
            if item.get("required")
        ]
    except Exception as exc:  # pragma: no cover - defensive CLI guard
        warnings.append(f"无法读取 required Verifier 配置: {exc}")
    state_result = check_state_and_gate(task_root, required_verifiers, errors)
    # manifest 可选声明 run/attempt；声明后不得与最终完成事件冲突。
    for key, actual in (("run_id", state_result.get("run_id")), ("attempt_id", state_result.get("attempt_id"))):
        if key in manifest and manifest.get(key) != actual:
            errors.append(f"manifest.{key} 与 completed 事件不一致")
    return {
        "passed": not errors,
        "errors": errors,
        "warnings": warnings,
        "report": report_result,
        "state": state_result,
        "evidence_index": str(evidence_index),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="检查 research-idea 是否可宣称完整完成")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--task-root", required=True)
    parser.add_argument("--report", help="用户指定友好文件名时传入最终报告路径；未传则读取 manifest.output_path")
    parser.add_argument("--evidence-index", help="默认读取 research-idea/output/completion-evidence.json")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    result = check_completion(
        Path(args.project_root),
        Path(args.task_root),
        Path(args.report) if args.report else None,
        Path(args.evidence_index) if args.evidence_index else None,
    )
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"status={'PASS' if result['passed'] else 'FAIL'}")
        print(f"current_state={result['state'].get('current_state')}")
        print(f"report_outcome={result['report'].get('outcome')}")
        print(f"report_completion_eligible={str(result['report'].get('completion_eligible')).lower()}")
        for error in result["errors"]:
            print(f"error={error}")
        for warning in result["warnings"]:
            print(f"warning={warning}")
    if not result["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
