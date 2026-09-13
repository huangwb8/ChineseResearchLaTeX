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


def current_entry_identity(workspace: TaskWorkspace, current_state: str) -> tuple[str, str]:
    """从 Kernel 事件投影取得当前 State 的进入身份。

    Kernel 2.1.0 尚未提供 visit/attempt 轮换接口；这里仅消费其公开投影，
    不另建身份文件或推断新的 attempt。
    """
    projection = EventLog(workspace.events).projection()
    transitions = projection.get("skill_state_transitions")
    if not isinstance(transitions, list):
        raise PhaseEntryError(
            "kernel_incompatible",
            "当前 Kernel 未提供 skill_state_transitions 投影；无法核对 State 进入身份",
            current_state=current_state,
            recovery="切换到与 bsk CLI 相同且满足 config.yaml 要求的 Python/Kernel 环境",
        )
    skill_transitions = [
        item for item in transitions
        if isinstance(item, dict) and item.get("skill") == "research-idea"
    ]
    if not skill_transitions:
        raise PhaseEntryError(
            "state_identity_missing",
            "当前 State 没有可核对的 BSK 进入事件",
            current_state=current_state,
            recovery="新任务须用非空 run_id/attempt_id 执行首次 BSK transition；旧现场只读保留",
        )
    entry = skill_transitions[-1]
    if entry.get("to_state") != current_state:
        raise PhaseEntryError(
            "state_projection_mismatch",
            "Kernel 事件投影与领域 State 快照不一致",
            current_state=current_state,
            projected_state=entry.get("to_state"),
            entry_event_id=entry.get("event_id"),
            recovery="停止推进并核对 Kernel 事件与 meta-state；不得手工改写旧记录",
        )
    run_id = entry.get("run_id")
    attempt_id = entry.get("attempt_id")
    if not isinstance(run_id, str) or not run_id or not isinstance(attempt_id, str) or not attempt_id or attempt_id == "default":
        raise PhaseEntryError(
            "state_identity_missing",
            "当前 State 的 BSK 进入事件缺少非空 run_id/attempt_id",
            current_state=current_state,
            entry_event_id=entry.get("event_id"),
            recovery="该现场不能在兼容模式续跑；保留旧记录并用带身份的新任务重新核验",
        )
    return run_id, attempt_id


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
            "命令行身份与当前 State 的 BSK 进入身份不一致",
            current_state=current_state,
            active_run_id=run_id,
            active_attempt_id=attempt_id,
            recovery="Kernel 2.1.0 兼容模式不支持轮换 attempt、失败重试或回退；停止并保留当前现场",
        )


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

    run_id, attempt_id = current_entry_identity(workspace, current)
    check_claimed_identity(
        args,
        run_id=run_id,
        attempt_id=attempt_id,
        current_state=current,
    )

    input_path = scoped_input_path(workspace, args.input, "Verifier 输入")
    request = verifier_request(
        load_object(input_path, "Verifier 输入"),
        action=args.action,
        run_id=run_id,
        attempt_id=attempt_id,
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
                run_id=run_id,
                attempt_id=attempt_id,
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
            "identity_mode": "state-entry-single-attempt-compat",
            "current_state": current,
            "target_state": target,
            "run_id": run_id,
            "attempt_id": attempt_id,
            "request": request,
            "handoffs": handoffs,
        }

    _, gate_event = EventLog(workspace.events).record_verification(
        [execution.to_event_payload() for execution in executions],
        {"decision": "wait"},
        scope="skill",
        actor="research-idea:phase-entry",
        run_id=run_id,
        attempt_id=attempt_id,
        idempotency_key=f"research-idea:{run_id}:{attempt_id}:{args.action}:verification",
        requirements=requirements,
    )
    gate = gate_event.payload if gate_event is not None else {"decision": "wait"}
    if gate.get("decision") != "allow":
        return {
            "status": "rejected",
            "reason_code": "business_evidence_rejected",
            "current_state": current,
            "target_state": target,
            "run_id": run_id,
            "attempt_id": attempt_id,
            "gate": gate,
            "recovery": "保留当前 State；Kernel 2.1.0 兼容模式不支持在该现场轮换 attempt 重试",
        }
    transition = transition_with_bsk(
        task=task,
        skill_root=skill_root,
        target=target,
        run_id=run_id,
        attempt_id=attempt_id,
    )
    entered = workspace.read_meta_state("research-idea").get("current_state")
    if entered != target:
        raise PhaseEntryError(
            "target_state_not_entered",
            "BSK 返回 transitioned，但领域快照尚未进入目标 State",
            current_state=entered,
            expected_state=target,
            run_id=run_id,
            attempt_id=attempt_id,
            recovery="停止下游业务并核对 Kernel 事件与 meta-state",
        )
    return {
        "status": "transitioned",
        "identity_mode": "state-entry-single-attempt-compat",
        "run_id": run_id,
        "attempt_id": attempt_id,
        "gate": gate,
        "transition": transition,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--task-root", required=True)
    parser.add_argument("--skill-root", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--action", choices=tuple(ACTION_TRANSITIONS), required=True)
    parser.add_argument("--run-id", help="兼容参数；提供时必须匹配当前 State 的 BSK 进入身份")
    parser.add_argument("--attempt-id", help="兼容参数；提供时必须匹配当前 State 的 BSK 进入身份")
    parser.add_argument("--input", required=True, help="包含 context 和 evidence 的 JSON")
    parser.add_argument("--submissions", help="Agent 按 BSK handoff 绑定的 component-result JSON")
    args = parser.parse_args()
    try:
        result = run(args)
    except PhaseEntryError as exc:
        print(json.dumps(exc.to_dict(), ensure_ascii=False, indent=2))
        raise SystemExit(2)
    except IdempotencyConflict as exc:
        print(json.dumps({
            "status": "rejected",
            "error_code": "retry_not_supported",
            "error": str(exc),
            "recovery": "当前兼容模式不能替换已记录 Gate；保留当前 State 与失败证据",
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
