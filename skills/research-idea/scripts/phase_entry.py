#!/usr/bin/env python3
"""用一个固定入口执行 research-idea 的 BSK 阶段验证与转移。"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys
from typing import Any

from bensz_skill_kernel.runtime import EventLog
from bensz_skill_kernel.states import SkillStateDeclaration
from bensz_skill_kernel.verifiers import FilesystemVerifierRegistry
from bensz_skill_kernel.workspace import TaskWorkspace

PREFIX = "bensz.research-ideation."
ACTION_TRANSITIONS = {
    "literature": (PREFIX + "literature", PREFIX + "candidates"),
    "candidates": (PREFIX + "candidates", PREFIX + "review"),
    "review": (PREFIX + "review", PREFIX + "reporting"),
    "reporting": (PREFIX + "reporting", PREFIX + "completed"),
}


def load_object(path: Path, label: str) -> dict[str, Any]:
    if not path.is_file():
        raise ValueError(f"缺少{label}: {path}")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"{label}不是合法 JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"{label}必须是对象")
    return value


def load_submissions(path: Path | None) -> list[dict[str, Any]]:
    if path is None:
        return []
    value: Any = load_object(path, "Verifier 回传")
    if "submissions" in value:
        value = value["submissions"]
    else:
        value = [value]
    if not isinstance(value, list) or not all(isinstance(item, dict) for item in value):
        raise ValueError("Verifier 回传必须是结果对象或 submissions 对象数组")
    return value


def resolve_task_root(project_root: Path, raw: Path) -> Path:
    resolved = raw.expanduser()
    if not resolved.is_absolute():
        resolved = project_root / resolved
    resolved = resolved.resolve()
    if not resolved.is_relative_to(project_root):
        raise ValueError("task-root 必须位于项目内")
    return resolved


def scoped_input_path(workspace: TaskWorkspace, raw: str, label: str) -> Path:
    path = Path(raw).expanduser().resolve()
    allowed = workspace.paths("research-idea").path("input").resolve()
    if not path.is_relative_to(allowed):
        raise ValueError(f"{label}必须位于本任务 research-idea/input 内")
    return path


def verifier_request(
    input_data: dict[str, Any], *, action: str, run_id: str, attempt_id: str
) -> dict[str, Any]:
    source, target = ACTION_TRANSITIONS[action]
    context = input_data.get("context", {})
    evidence = input_data.get("evidence", [])
    if not isinstance(context, dict) or not isinstance(evidence, list):
        raise ValueError("Verifier 输入必须包含对象 context 和数组 evidence")
    if not evidence:
        raise ValueError("Verifier 输入 evidence 不得为空")
    return {
        "run_id": run_id,
        "attempt_id": attempt_id,
        "subject": {"operation": "advance", "source": source, "target": target},
        "context": context,
        "evidence": evidence,
    }


def transition_with_bsk(
    *, task: Path, skill_root: Path, target: str, run_id: str, attempt_id: str
) -> dict[str, Any]:
    command = [
        sys.executable,
        "-m",
        "bensz_skill_kernel.cli",
        "state",
        "transition",
        str(task),
        "research-idea",
        target,
        "--skill-root",
        str(skill_root),
        "--run-id",
        run_id,
        "--attempt-id",
        attempt_id,
    ]
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        raise ValueError(result.stderr.strip() or result.stdout.strip() or "bsk transition 执行失败")
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise ValueError("bsk transition 未返回合法 JSON") from exc
    if payload.get("status") != "transitioned":
        raise ValueError(f"bsk transition 未通过: {payload.get('reason', payload.get('status'))}")
    return payload


def run(args: argparse.Namespace) -> dict[str, Any]:
    project = Path(args.project_root).expanduser().resolve()
    task = resolve_task_root(project, Path(args.task_root))
    skill_root = Path(args.skill_root).expanduser().resolve()
    workspace = TaskWorkspace.open_existing(task)
    source, target = ACTION_TRANSITIONS[args.action]
    current = workspace.read_meta_state("research-idea").get("current_state")
    if current != source:
        raise ValueError(f"action={args.action} 要求当前 State={source}，实际为 {current or 'unknown'}")

    input_path = scoped_input_path(workspace, args.input, "Verifier 输入")
    request = verifier_request(
        load_object(input_path, "Verifier 输入"),
        action=args.action,
        run_id=args.run_id,
        attempt_id=args.attempt_id,
    )
    declaration = SkillStateDeclaration.from_skill_root(skill_root)
    requirements = declaration.verifier_requirements()
    registry = FilesystemVerifierRegistry(skill_root / "references/verifiers")
    submission_path = scoped_input_path(workspace, args.submissions, "Verifier 回传") if args.submissions else None
    submissions = load_submissions(submission_path)
    executions = []
    for requirement in requirements:
        matching = [item for item in submissions if item.get("pack_id") == requirement["id"]]
        executions.append(
            registry.run_contract(
                requirement["id"],
                request,
                version=requirement["version"],
                run_id=args.run_id,
                attempt_id=args.attempt_id,
                submissions=matching,
            )
        )

    handoffs = [
        handoff.to_audit_dict()
        for execution in executions
        for handoff in execution.report.handoffs
    ]
    if handoffs:
        return {
            "status": "awaiting_agent",
            "current_state": current,
            "target_state": target,
            "request": request,
            "handoffs": handoffs,
        }

    _, gate_event = EventLog(workspace.events).record_verification(
        [execution.to_event_payload() for execution in executions],
        {"decision": "wait"},
        scope="skill",
        actor="research-idea:phase-entry",
        run_id=args.run_id,
        attempt_id=args.attempt_id,
        idempotency_key=f"research-idea:{args.run_id}:{args.attempt_id}:verification",
        requirements=requirements,
    )
    gate = gate_event.payload if gate_event is not None else {"decision": "wait"}
    if gate.get("decision") != "allow":
        return {
            "status": "rejected",
            "current_state": current,
            "target_state": target,
            "gate": gate,
        }
    transition = transition_with_bsk(
        task=task,
        skill_root=skill_root,
        target=target,
        run_id=args.run_id,
        attempt_id=args.attempt_id,
    )
    return {"status": "transitioned", "gate": gate, "transition": transition}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--task-root", required=True)
    parser.add_argument("--skill-root", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--action", choices=tuple(ACTION_TRANSITIONS), required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--attempt-id", required=True)
    parser.add_argument("--input", required=True, help="包含 context 和 evidence 的 JSON")
    parser.add_argument("--submissions", help="Agent 按 BSK handoff 绑定的 component-result JSON")
    args = parser.parse_args()
    try:
        result = run(args)
    except (OSError, ValueError) as exc:
        print(json.dumps({"status": "rejected", "error": str(exc)}, ensure_ascii=False, indent=2))
        raise SystemExit(2)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if result["status"] == "rejected":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
