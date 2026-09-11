#!/usr/bin/env python3
"""检查 research-idea 最终交付是否具备完整完成证据。"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from validate_report import validate_report

PREFIX = "bensz.research-ideation."
COMPLETED = PREFIX + "completed"
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
    if path.stat().st_size == 0:
        errors.append(f"{label} 是空文件: {raw}")
    return path


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


def check_dependency_index(index: dict[str, Any], task_root: Path, manifest: dict[str, Any], report: dict[str, Any], errors: list[str]) -> None:
    dependencies = index.get("dependencies")
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
            require_nonempty_file(task_root, record_path(item), errors, f"{skill} 产物 {index_no}")

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
                require_nonempty_file(task_root, reviewer.get("path"), errors, f"第 {round_no} 轮 reviewer {reviewer_no}")
            require_nonempty_file(task_root, item.get("summary_path"), errors, f"第 {round_no} 轮汇总")
        require_nonempty_file(task_root, review.get("synthesis_path"), errors, "独立审查总综合")


def check_state_and_gate(task_root: Path, required_verifiers: list[str], errors: list[str]) -> dict[str, Any]:
    meta = load_json(task_root / "research-idea/log/meta-state.json", errors, "领域状态快照")
    events = read_events(task_root / "log/events.ndjson", errors)
    current_state = meta.get("current_state")
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
        return {"current_state": current_state, "event_count": len(events), "completed_transition": None}
    completed_event = completed_events[-1]
    run_id = completed_event.get("run_id")
    attempt_id = completed_event.get("attempt_id")
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
    if index:
        check_dependency_index(index, task_root, manifest, report_result, errors)

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
