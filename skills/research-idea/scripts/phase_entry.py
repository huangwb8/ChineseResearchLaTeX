#!/usr/bin/env python3
"""用一个固定入口执行 research-idea 的 BSK 阶段验证与转移。"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys
from typing import Any

from bensz_skill_kernel.runtime import EventLog, IdempotencyConflict, KernelError
from bensz_skill_kernel.states import SkillStateDeclaration
from bensz_skill_kernel.verifiers import FilesystemVerifierRegistry
from bensz_skill_kernel.workspace import TaskWorkspace

from start_workflow import StartError, check_interpreter, critical_files

PREFIX = "bensz.research-ideation."
ACTION_TRANSITIONS = {
    "literature": (PREFIX + "literature", PREFIX + "candidates"),
    "candidates": (PREFIX + "candidates", PREFIX + "review"),
    "review": (PREFIX + "review", PREFIX + "reporting"),
    "reporting": (PREFIX + "reporting", PREFIX + "completed"),
}


class PhaseEntryError(ValueError):
    """可供 Agent 稳定判断和恢复的阶段入口错误。"""

    def __init__(self, code: str, message: str, **details: Any):
        super().__init__(message)
        self.code = code
        self.details = details

    def to_dict(self) -> dict[str, Any]:
        return {"status": "rejected", "error_code": self.code, "error": str(self), **self.details}


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


def current_entry_identity(workspace: TaskWorkspace, current_state: str) -> dict[str, str]:
    """从 Kernel 当前投影取得 v2 State visit 与 active attempt。"""
    projection = EventLog(workspace.events).projection()
    current = projection.get("skill_states", {}).get("research-idea")
    if not isinstance(current, dict):
        raise PhaseEntryError(
            "state_identity_missing",
            "当前 State 没有可核对的 BSK 身份投影",
            current_state=current_state,
            recovery="新任务必须通过 start_workflow.py 原子启动；旧现场只读保留",
        )
    if current.get("legacy_identity", True):
        raise PhaseEntryError(
            "legacy_state_identity",
            "当前 State 使用 legacy 身份，不能进入 research-idea 标准业务路径",
            current_state=current_state,
            recovery="保留旧现场只读审计；新任务使用 start_workflow.py 建立 v2 身份",
        )
    if current.get("state") != current_state:
        raise PhaseEntryError(
            "state_projection_mismatch",
            "Kernel 事件投影与领域 State 快照不一致",
            current_state=current_state,
            projected_state=current.get("state"),
            recovery="停止推进并核对 Kernel 事件与 meta-state；不得手工改写旧记录",
        )
    identity = {
        "run_id": current.get("run_id"),
        "state_visit_id": current.get("state_visit_id"),
        "attempt_id": current.get("active_attempt_id"),
        "state_version": current.get("version"),
    }
    if not all(isinstance(value, str) and value for value in identity.values()):
        raise PhaseEntryError(
            "state_identity_missing",
            "当前 v2 State 缺少 run/visit/active attempt/version",
            current_state=current_state,
            recovery="停止标准业务并核对 start_workflow.py 的首次转移结果",
        )
    return identity


def check_claimed_identity(args: argparse.Namespace, *, run_id: str, attempt_id: str, current_state: str) -> None:
    """兼容旧调用参数，但只接受与 Kernel 当前进入身份完全一致的值。"""
    if (args.run_id is None) != (args.attempt_id is None):
        raise PhaseEntryError(
            "identity_arguments_incomplete",
            "--run-id 与 --attempt-id 必须同时提供或同时省略",
            current_state=current_state,
            recovery="省略两项以使用 Kernel 当前进入身份",
        )
    if args.run_id is not None and (args.run_id != run_id or args.attempt_id != attempt_id):
        raise PhaseEntryError(
            "state_identity_mismatch",
            "命令行身份与当前 State 的 BSK active attempt 不一致",
            current_state=current_state,
            active_run_id=run_id,
            active_attempt_id=attempt_id,
            recovery="省略身份参数使用当前 active attempt，或用 retry 模式显式 supersede",
        )


def validate_runtime_snapshot(workspace: TaskWorkspace, skill_root: Path) -> None:
    path = workspace.paths("research-idea").path("log") / "runtime-snapshot.json"
    if not path.is_file():
        raise PhaseEntryError(
            "runtime_snapshot_missing",
            "当前任务缺少原子启动生成的运行快照",
            recovery="新任务使用 start_workflow.py；旧任务只读审计，不补写快照",
        )
    snapshot = load_object(path, "运行快照")
    expected = snapshot.get("skill", {}).get("files")
    actual = critical_files(skill_root)
    if expected != actual:
        raise PhaseEntryError(
            "skill_runtime_drift",
            "当前 Skill 关键文件与启动时快照不一致",
            changed=sorted(set(expected or {}) | set(actual)),
            recovery="停止当前任务；恢复启动时 Skill 副本，或以新任务使用已同步版本",
        )
    try:
        check_interpreter()
    except StartError as exc:
        raise PhaseEntryError(exc.code, str(exc), **exc.details) from exc


def verifier_request(
    input_data: dict[str, Any], *, action: str, run_id: str, state_visit_id: str, attempt_id: str
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
        "state_visit_id": state_visit_id,
        "attempt_id": attempt_id,
        "subject": {"operation": "advance", "source": source, "target": target},
        "context": context,
        "evidence": evidence,
    }


def transition_with_bsk(
    *, task: Path, skill_root: Path, target: str, identity: dict[str, str], target_attempt_id: str
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
        "--run-id", identity["run_id"],
        "--state-visit-id", identity["state_visit_id"],
        "--attempt-id",
        identity["attempt_id"],
        "--target-attempt-id", target_attempt_id,
        "--idempotency-key", f"research-idea:{identity['run_id']}:{identity['state_visit_id']}:{target}:transition",
    ]
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        raise PhaseEntryError(
            "kernel_transition_error",
            result.stderr.strip() or result.stdout.strip() or "bsk transition 执行失败",
            recovery="核对 Python 与 bsk 是否属于同一 Kernel 环境后，从当前 State 恢复",
        )
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise PhaseEntryError(
            "kernel_transition_invalid_output",
            "bsk transition 未返回合法 JSON",
            recovery="核对 Python 与 bsk 是否属于同一 Kernel 环境",
        ) from exc
    if payload.get("status") != "transitioned":
        raise PhaseEntryError(
            "kernel_transition_rejected",
            f"bsk transition 未通过: {payload.get('reason', payload.get('status'))}",
            kernel_result=payload,
            recovery="保持当前 State；不要开展下一阶段业务或手工改写状态",
        )
    return payload


def start_attempt_with_bsk(
    *, task: Path, current: str, identity: dict[str, str], attempt_id: str, reason: str
) -> dict[str, Any]:
    command = [
        sys.executable, "-m", "bensz_skill_kernel.cli", "attempt", "start",
        str(task), "research-idea", "--run-id", identity["run_id"],
        "--state-visit-id", identity["state_visit_id"], "--attempt-id", attempt_id,
        "--reason", reason,
        "--idempotency-key", f"research-idea:{identity['run_id']}:{identity['state_visit_id']}:{attempt_id}:attempt",
    ]
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        raise PhaseEntryError(
            "attempt_supersede_failed",
            result.stderr.strip() or result.stdout.strip() or "BSK attempt start 执行失败",
            current_state=current,
            recovery="保持当前 attempt，核对 v2 State visit 身份后重试",
        )
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise PhaseEntryError("attempt_supersede_invalid_output", "BSK attempt start 未返回合法 JSON") from exc
    if payload.get("status") != "started":
        raise PhaseEntryError("attempt_supersede_rejected", "BSK 未启动新 attempt", kernel_result=payload)
    return payload


def run(args: argparse.Namespace) -> dict[str, Any]:
    project = Path(args.project_root).expanduser().resolve()
    task = resolve_task_root(project, Path(args.task_root))
    skill_root = Path(args.skill_root).expanduser().resolve()
    workspace = TaskWorkspace.open_existing(task)
    source, target = ACTION_TRANSITIONS[args.action]
    current = workspace.read_meta_state("research-idea").get("current_state")
    if current != source:
        raise PhaseEntryError(
            "state_mismatch",
            f"action={args.action} 要求当前 State={source}，实际为 {current or 'unknown'}",
            current_state=current,
            expected_state=source,
            recovery="选择与当前 State 对应的 action；不得跳阶段",
        )

    identity = current_entry_identity(workspace, current)
    validate_runtime_snapshot(workspace, skill_root)
    check_claimed_identity(
        args,
        run_id=identity["run_id"],
        attempt_id=identity["attempt_id"],
        current_state=current,
    )

    log = EventLog(workspace.events)
    if args.mode == "retry":
        if not args.new_attempt_id or not args.reason:
            raise PhaseEntryError("retry_arguments_missing", "retry 需要 --new-attempt-id 与 --reason")
        payload = start_attempt_with_bsk(
            task=task, current=current, identity=identity,
            attempt_id=args.new_attempt_id, reason=args.reason,
        )
        active = payload["active_identity"]
        return {
            "status": "attempt_started", "current_state": current,
            "run_id": active["run_id"], "state_visit_id": active["state_visit_id"],
            "attempt_id": active["attempt_id"], "superseded_attempt_id": identity["attempt_id"],
        }

    if args.mode == "start":
        key = f"research-idea:{identity['run_id']}:{identity['state_visit_id']}:{identity['attempt_id']}:{args.action}"
        grant = log.preflight_action(
            skill="research-idea", action=args.action, state=current,
            state_version=identity["state_version"], run_id=identity["run_id"],
            state_visit_id=identity["state_visit_id"], attempt_id=identity["attempt_id"],
            idempotency_key=key + ":authorize",
        )
        if grant.type != "action.authorization.granted":
            raise PhaseEntryError(
                "action_not_authorized", "BSK 未授权当前阶段 action",
                reason_code=grant.payload.get("reason_code"), recovery=grant.payload.get("recovery"),
            )
        authorization_id = grant.payload["authorization_id"]
        consumed = log.consume_action_authorization(
            authorization_id, skill="research-idea", action=args.action,
            run_id=identity["run_id"], state_visit_id=identity["state_visit_id"],
            attempt_id=identity["attempt_id"], idempotency_key=key + ":consume",
        )
        if consumed.type != "action.authorization.consumed":
            raise PhaseEntryError(
                "action_not_authorized", "阶段 action 授权未成功消费",
                reason_code=consumed.payload.get("reason_code"), recovery=consumed.payload.get("recovery"),
            )
        return {
            "status": "authorized", "action": args.action, "authorization_id": authorization_id,
            "current_state": current, **{key: identity[key] for key in ("run_id", "state_visit_id", "attempt_id")},
        }

    authorizations = log.projection().get("action_authorizations", {})
    if not any(
        item.get("status") == "consumed" and item.get("skill") == "research-idea"
        and item.get("action") == args.action and item.get("run_id") == identity["run_id"]
        and item.get("state_visit_id") == identity["state_visit_id"]
        and item.get("attempt_id") == identity["attempt_id"]
        for item in authorizations.values()
    ):
        raise PhaseEntryError(
            "action_not_authorized", "当前阶段尚未消费 State-bound action authorization",
            recovery=f"先执行 phase_entry.py --mode start --action {args.action}",
        )

    if not args.input:
        raise PhaseEntryError("verifier_input_missing", "finish 模式需要 --input")
    input_path = scoped_input_path(workspace, args.input, "Verifier 输入")
    request = verifier_request(
        load_object(input_path, "Verifier 输入"),
        action=args.action,
        run_id=identity["run_id"],
        state_visit_id=identity["state_visit_id"],
        attempt_id=identity["attempt_id"],
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
                run_id=identity["run_id"],
                state_visit_id=identity["state_visit_id"],
                attempt_id=identity["attempt_id"],
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
            "identity_mode": "state-visit-v2",
            "current_state": current,
            "target_state": target,
            "run_id": identity["run_id"],
            "state_visit_id": identity["state_visit_id"],
            "attempt_id": identity["attempt_id"],
            "request": request,
            "handoffs": handoffs,
        }

    _, gate_event = log.record_verification_batch(
        [execution.to_event_payload() for execution in executions],
        {"decision": "wait"},
        scope="skill",
        actor="research-idea:phase-entry",
        run_id=identity["run_id"], state_visit_id=identity["state_visit_id"],
        attempt_id=identity["attempt_id"],
        idempotency_key=f"research-idea:{identity['run_id']}:{identity['state_visit_id']}:{identity['attempt_id']}:{args.action}:verification",
        requirements=requirements,
    )
    gate = gate_event.payload if gate_event is not None else {"decision": "wait"}
    if gate.get("decision") != "allow":
        return {
            "status": "rejected",
            "reason_code": "business_evidence_rejected",
            "current_state": current,
            "target_state": target,
            "run_id": identity["run_id"], "state_visit_id": identity["state_visit_id"],
            "attempt_id": identity["attempt_id"],
            "gate": gate,
            "recovery": "保留当前 State；使用 --mode retry 显式 supersede attempt 后重新授权和审查",
        }
    import hashlib
    target_attempt_id = "attempt-" + hashlib.sha256(
        f"{identity['run_id']}:{identity['state_visit_id']}:{target}".encode()
    ).hexdigest()[:16]
    transition = transition_with_bsk(
        task=task, skill_root=skill_root, target=target, identity=identity,
        target_attempt_id=target_attempt_id,
    )
    entered = workspace.read_meta_state("research-idea").get("current_state")
    if entered != target:
        raise PhaseEntryError(
            "target_state_not_entered",
            "BSK 返回 transitioned，但领域快照尚未进入目标 State",
            current_state=entered,
            expected_state=target,
            run_id=identity["run_id"], state_visit_id=identity["state_visit_id"],
            attempt_id=identity["attempt_id"],
            recovery="停止下游业务并核对 Kernel 事件与 meta-state",
        )
    return {
        "status": "transitioned",
        "identity_mode": "state-visit-v2",
        "run_id": identity["run_id"],
        "source_state_visit_id": identity["state_visit_id"],
        "source_attempt_id": identity["attempt_id"],
        "target_identity": transition.get("target_identity"),
        "gate": gate,
        "transition": transition,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--task-root", required=True)
    parser.add_argument("--skill-root", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--mode", choices=("start", "finish", "retry"), default="finish")
    parser.add_argument("--action", choices=tuple(ACTION_TRANSITIONS), required=True)
    parser.add_argument("--run-id", help="兼容参数；提供时必须匹配当前 State 的 BSK 进入身份")
    parser.add_argument("--attempt-id", help="兼容参数；提供时必须匹配当前 State 的 BSK 进入身份")
    parser.add_argument("--input", help="finish 模式下包含 context 和 evidence 的 JSON")
    parser.add_argument("--submissions", help="Agent 按 BSK handoff 绑定的 component-result JSON")
    parser.add_argument("--new-attempt-id", help="retry 模式的新 attempt")
    parser.add_argument("--reason", help="retry 模式的 supersede 原因")
    args = parser.parse_args()
    try:
        result = run(args)
    except PhaseEntryError as exc:
        print(json.dumps(exc.to_dict(), ensure_ascii=False, indent=2))
        raise SystemExit(2)
    except IdempotencyConflict as exc:
        print(json.dumps({
            "status": "rejected",
            "error_code": "attempt_supersede_required",
            "error": str(exc),
            "recovery": "保留当前 State；使用 retry 模式 supersede attempt 后重新授权和审查",
        }, ensure_ascii=False, indent=2))
        raise SystemExit(2)
    except (OSError, ValueError, KernelError) as exc:
        print(json.dumps({
            "status": "rejected",
            "error_code": "phase_entry_error",
            "error": str(exc),
            "recovery": "保持当前 State，核对输入、绑定和 Kernel 环境后再决定是否建立新任务",
        }, ensure_ascii=False, indent=2))
        raise SystemExit(2)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if result["status"] == "rejected":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
