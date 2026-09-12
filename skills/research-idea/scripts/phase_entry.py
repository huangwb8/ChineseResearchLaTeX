#!/usr/bin/env python3
"""research-idea 的 state-aware 阶段入口。

该入口只负责可确定的编排约束：读取当前 State、创建不可复用的 attempt、
生成带输入快照的 handoff，并在完成前校验产物和 Kernel allow Gate。科学
判断仍由本地 Verifier/Agent 完成；本脚本不实现第二套状态机。
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import uuid

PREFIX = "bensz.research-ideation."

# 下游动作只能在其所属 State 启动。状态转移仍由 bsk 执行，避免 Skill
# 自建状态机；start 产生的 handoff 是下游 Skill 的唯一输入凭证。
ACTION_STATES = {
    "literature": PREFIX + "literature",
    "candidates": PREFIX + "candidates",
    "novelty": PREFIX + "candidates",
    "review": PREFIX + "review",
    "reporting": PREFIX + "reporting",
}
ACTION_TARGETS = {
    "literature": PREFIX + "candidates",
    "candidates": PREFIX + "review",
    "novelty": PREFIX + "review",
    "review": PREFIX + "reporting",
    "reporting": PREFIX + "completed",
}


def audit_rejection(scoped: Path, *, action: str, reason: str, current: object, recovery: str) -> None:
    """记录可恢复的拒绝，不写任何下游产物。"""
    path = scoped / "log/attempts/rejections.ndjson"
    path.parent.mkdir(parents=True, exist_ok=True)
    event = {"occurred_at": utc_now(), "action": action, "reason": reason, "current_state": current, "recovery": recovery}
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False) + "\n")


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")


def digest(path: Path) -> dict[str, object]:
    stat = path.stat()
    return {
        "sha256": "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest(),
        "size": stat.st_size,
        "mtime_ns": stat.st_mtime_ns,
    }


def safe_path(project_root: Path, raw: str, label: str) -> Path:
    candidate = Path(raw)
    if candidate.is_absolute():
        raise ValueError(f"{label} 必须是项目内相对路径")
    resolved = (project_root / candidate).resolve()
    if not resolved.is_relative_to(project_root):
        raise ValueError(f"{label} 超出项目范围: {raw}")
    if any(part == ".." for part in candidate.parts):
        raise ValueError(f"{label} 不允许 ..: {raw}")
    if any(part.is_symlink() for part in (resolved, *resolved.parents) if part != project_root and project_root in part.parents):
        raise ValueError(f"{label} 不得通过符号链接逃逸: {raw}")
    return resolved


def load_json(path: Path, label: str) -> dict:
    if not path.is_file():
        raise ValueError(f"缺少{label}: {path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"{label} 不是合法 JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError(f"{label} 必须是对象")
    return data


def task_paths(project_root: Path, task_root: Path) -> tuple[Path, Path, Path]:
    task_root = task_root.resolve()
    if not task_root.is_relative_to(project_root) or task_root.parent.name != ".bensz-api" or not task_root.name.startswith("task-"):
        raise ValueError("task-root 必须位于项目内 .bensz-api/task-*")
    if load_json(task_root / ".workspace.json", "任务工作区声明").get("protocol") != "bensz-api-task-v1":
        raise ValueError("工作区协议不匹配")
    scoped = task_root / "research-idea"
    return scoped, scoped / "input/manifest.json", scoped / "log/meta-state.json"


def event_gate(events_path: Path, run_id: str, attempt_id: str) -> dict | None:
    if not events_path.is_file():
        return None
    found = None
    for line in events_path.read_text(encoding="utf-8").splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if (
            event.get("type") == "verification.gate"
            and event.get("run_id") == run_id
            and event.get("attempt_id") == attempt_id
            and event.get("payload", {}).get("decision") == "allow"
        ):
            found = event
    return found


def entry_gate(events_path: Path, state: str) -> dict | None:
    """返回进入当前 State 的 allow Gate；literature 可由 workspace.ready 进入。"""
    if state == PREFIX + "literature" or not events_path.is_file():
        return None
    transitions = []
    events = []
    for line in events_path.read_text(encoding="utf-8").splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        events.append(event)
        if event.get("type") == "state.transition" and event.get("payload", {}).get("to_state") == state:
            transitions.append(event)
    if not transitions:
        return None
    transition = transitions[-1]
    run_id, attempt_id = transition.get("run_id"), transition.get("attempt_id")
    if not run_id or not attempt_id:
        return None
    candidates = [
        event for event in events
        if event.get("type") == "verification.gate"
        and event.get("run_id") == run_id
        and event.get("attempt_id") == attempt_id
        and event.get("payload", {}).get("decision") == "allow"
    ]
    return candidates[-1] if candidates else None


def attempt_file(scoped: Path, attempt_id: str) -> Path:
    if not attempt_id or "/" in attempt_id or "\\" in attempt_id or attempt_id in {".", ".."}:
        raise ValueError("attempt-id 只能包含不带路径分隔符的标识")
    return scoped / "log/attempts" / f"{attempt_id}.json"


def start(args: argparse.Namespace) -> dict:
    project = Path(args.project_root).expanduser().resolve()
    task = Path(args.task_root).expanduser()
    if not task.is_absolute():
        task = project / task
    scoped, manifest_path, meta_path = task_paths(project, task)
    manifest = load_json(manifest_path, "research-idea manifest")
    meta = load_json(meta_path, "领域状态快照")
    expected = ACTION_STATES.get(args.action)
    if expected is None:
        raise ValueError(f"未知 action: {args.action}")
    if not args.artifact:
        raise ValueError("artifact_path_required: start 必须声明预期阶段产物相对路径")
    current = meta.get("current_state")
    if current != expected:
        audit_rejection(scoped, action=args.action, reason="state_mismatch", current=current, recovery=f"先通过对应阶段 Gate/transition，或使用 action={next((a for a, s in ACTION_STATES.items() if s == current), 'literature')}")
        raise ValueError(f"阶段入口拒绝 [state_mismatch]: action={args.action} 要求 State={expected}，当前为 {current or 'unknown'}")
    if current != PREFIX + "literature" and entry_gate(task / "log/events.ndjson", current) is None:
        audit_rejection(scoped, action=args.action, reason="missing_gate", current=current, recovery="恢复上一个阶段的 required Verifier、allow Gate 和 state transition")
        raise ValueError("阶段入口拒绝 [missing_gate]: 当前 State 缺少可核验的进入 Gate")
    run_id = args.run_id or f"idea-{dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')}-{uuid.uuid4().hex[:8]}"
    attempt_id = args.attempt_id or f"{args.action}-{dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')}-{uuid.uuid4().hex[:8]}"
    record_path = attempt_file(scoped, attempt_id)
    if record_path.exists():
        raise ValueError(f"attempt 已存在，禁止覆盖或复用: {attempt_id}；续跑请创建新 attempt")
    evidence = []
    for raw in args.evidence:
        path = safe_path(project, raw, "evidence")
        if not path.is_file() or path.stat().st_size == 0:
            raise ValueError(f"evidence 不存在或为空: {raw}")
        evidence.append({"path": path.relative_to(project).as_posix(), "snapshot": digest(path)})
    started = utc_now()
    manifest_snapshot = digest(manifest_path)
    handoff = {
        "protocol": "research-idea-phase-handoff-v1",
        "action": args.action,
        "state": current,
        "run_id": run_id,
        "attempt_id": attempt_id,
        "started_at": started,
        "manifest": {"path": manifest_path.relative_to(project).as_posix(), "snapshot": manifest_snapshot},
        "evidence": evidence,
        "artifact_path": args.artifact,
        "target_state": ACTION_TARGETS[args.action],
        "target": ACTION_TARGETS[args.action],
        "state_version": "3.0.0",
        "snapshot_hash": manifest_snapshot["sha256"],
    }
    handoff["handoff_hash"] = "sha256:" + hashlib.sha256(json.dumps(handoff, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    request_path = scoped / "input/attempts" / f"{attempt_id}.json"
    record_path.parent.mkdir(parents=True, exist_ok=True)
    request_path.parent.mkdir(parents=True, exist_ok=True)
    record = {**handoff, "status": "started", "request_path": request_path.relative_to(task).as_posix()}
    try:
        with record_path.open("x", encoding="utf-8", newline="") as handle:
            handle.write(json.dumps(record, ensure_ascii=False, indent=2) + "\n")
        with request_path.open("x", encoding="utf-8", newline="") as handle:
            handle.write(json.dumps(handoff, ensure_ascii=False, indent=2) + "\n")
    except FileExistsError as exc:
        raise ValueError(f"拒绝覆盖既有 attempt 文件: {exc.filename}") from exc
    return {"status": "started", "handoff": handoff, "attempt_path": record_path.relative_to(task).as_posix(), "request_path": request_path.relative_to(task).as_posix()}


def complete(args: argparse.Namespace) -> dict:
    project = Path(args.project_root).expanduser().resolve()
    task = Path(args.task_root).expanduser()
    if not task.is_absolute():
        task = project / task
    scoped, _, meta_path = task_paths(project, task)
    record_path = attempt_file(scoped, args.attempt_id)
    record = load_json(record_path, "attempt 记录")
    if record.get("run_id") != args.run_id:
        raise ValueError("run_id 与 attempt 不一致")
    expected = ACTION_STATES.get(record.get("action"))
    current = load_json(meta_path, "领域状态快照").get("current_state")
    if current != expected:
        raise ValueError(f"完成入口拒绝：当前 State 已变化为 {current or 'unknown'}，不能完成旧 attempt")
    if record.get("status") != "started":
        raise ValueError("attempt 不是 started 状态，不能重复完成")
    artifact = safe_path(project, args.artifact, "artifact")
    if not artifact.is_file() or artifact.stat().st_size == 0:
        raise ValueError("artifact 必须是非空文件")
    if record.get("artifact_path") != args.artifact:
        raise ValueError("artifact_without_handoff: artifact 路径与 handoff 不一致")
    expected_target = ACTION_TARGETS.get(record.get("action"))
    if args.target and args.target != expected_target:
        raise ValueError(f"target 与 action 不匹配: 需要 {expected_target}")
    provenance_path = artifact.with_name(artifact.name + ".provenance.json")
    if not provenance_path.is_file():
        raise ValueError("artifact_without_handoff: 缺少 artifact.provenance.json")
    provenance = load_json(provenance_path, "artifact provenance")
    for key, value in (("run_id", args.run_id), ("attempt_id", args.attempt_id), ("source_state", record.get("state")), ("handoff_hash", record.get("handoff_hash"))):
        if provenance.get(key) != value:
            raise ValueError(f"artifact_without_handoff: provenance.{key} 不匹配")
    if provenance.get("content_hash") != digest(artifact)["sha256"]:
        raise ValueError("artifact_without_handoff: provenance 内容快照不匹配")
    gate = event_gate(task / "log/events.ndjson", args.run_id, args.attempt_id)
    if gate is None and args.submission:
        # close 可在同一入口完成 required Verifier 的绑定与 Gate 记录；不提供
        # submission 时仍 fail-closed，避免把文件存在误认为阶段通过。
        try:
            from bensz_skill_kernel.runtime import EventLog
            from bensz_skill_kernel.verifiers import FilesystemVerifierRegistry
            request = load_json(task / record["request_path"], "phase handoff")
            submissions = json.loads(Path(args.submission).read_text(encoding="utf-8"))
            if isinstance(submissions, dict):
                submissions = [submissions]
            registry = FilesystemVerifierRegistry(Path(args.skill_root).resolve() / "references/verifiers")
            executions = []
            for verifier_id, version in (("bensz.research.stage-readiness", "3.0.0"), ("bensz.research.hypothesis-merit", "1.0.0")):
                items = [item for item in submissions if isinstance(item, dict) and item.get("pack_id") == verifier_id]
                executions.append(registry.run_contract(verifier_id, request, version=version, run_id=args.run_id, attempt_id=args.attempt_id, submissions=items))
            EventLog(task / "log/events.ndjson").record_verification([item.to_event_payload() for item in executions], {"decision": "wait"}, run_id=args.run_id, attempt_id=args.attempt_id, scope="skill")
            gate = event_gate(task / "log/events.ndjson", args.run_id, args.attempt_id)
        except Exception as exc:
            raise ValueError(f"required Verifier/Gate 记录失败: {exc}") from exc
    if gate is None:
        raise ValueError("缺少当前 run/attempt 的 allow Gate；先完成 required Verifier，再提交阶段产物")
    result = {"status": "completed", "attempt": record}
    if args.target:
        cmd = [sys.executable, "-m", "bensz_skill_kernel.cli", "state", "transition", str(task), "research-idea", args.target, "--skill-root", str(Path(args.skill_root).resolve()), "--run-id", args.run_id, "--attempt-id", args.attempt_id]
        proc = subprocess.run(cmd, cwd=project, capture_output=True, text=True)
        if proc.returncode != 0:
            raise ValueError(proc.stderr.strip() or proc.stdout.strip() or "bsk state transition 失败")
        try:
            transition = json.loads(proc.stdout)
        except json.JSONDecodeError as exc:
            raise ValueError(f"bsk 返回不是 JSON: {proc.stdout[:200]}") from exc
        if transition.get("status") != "transitioned":
            raise ValueError(f"状态未转移: {transition}")
        result["transition"] = transition
    record.update({"status": "completed", "completed_at": utc_now(), "artifact": {"path": artifact.relative_to(project).as_posix(), "snapshot": digest(artifact)}, "gate_event_id": gate.get("event_id")})
    record_path.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="")
    result["attempt"] = record
    return result


def resume(args: argparse.Namespace) -> dict:
    """恢复未关闭 attempt；不生成新身份，也不覆盖 handoff。"""
    project = Path(args.project_root).expanduser().resolve()
    task = Path(args.task_root).expanduser()
    if not task.is_absolute():
        task = project / task
    scoped, _, _ = task_paths(project, task)
    record = load_json(attempt_file(scoped, args.attempt_id), "attempt 记录")
    if record.get("run_id") != args.run_id or record.get("status") != "started":
        raise ValueError("只能恢复同一 run 下仍为 started 的 attempt")
    manifest_path = project / record["manifest"]["path"]
    if digest(manifest_path) != record["manifest"]["snapshot"]:
        raise ValueError("stale_manifest: manifest 内容已变化，必须新建 attempt")
    for item in record.get("evidence", []):
        path = project / item["path"]
        if not path.is_file() or digest(path) != item["snapshot"]:
            raise ValueError("stale_manifest: evidence 内容已变化，必须新建 attempt")
    return {"status": "resumed", "handoff": {key: record[key] for key in ("action", "state", "run_id", "attempt_id", "started_at", "manifest", "evidence", "artifact_path") if key in record}}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    start_parser = sub.add_parser("start", help="校验 State 并创建不可复用 attempt/handoff")
    start_parser.add_argument("--project-root", default=".")
    start_parser.add_argument("--task-root", required=True)
    start_parser.add_argument("--action", choices=sorted(ACTION_STATES), required=True)
    start_parser.add_argument("--run-id")
    start_parser.add_argument("--attempt-id")
    start_parser.add_argument("--artifact")
    start_parser.add_argument("--evidence", action="append", default=[])
    start_parser.set_defaults(func=start)
    resume_parser = sub.add_parser("resume", help="恢复同一 attempt；证据变化时必须新建 attempt")
    resume_parser.add_argument("--project-root", default=".")
    resume_parser.add_argument("--task-root", required=True)
    resume_parser.add_argument("--run-id", required=True)
    resume_parser.add_argument("--attempt-id", required=True)
    resume_parser.set_defaults(func=resume)
    done = sub.add_parser("complete", aliases=["close"], help="校验产物和 allow Gate，可选执行状态转移")
    done.add_argument("--project-root", default=".")
    done.add_argument("--task-root", required=True)
    done.add_argument("--run-id", required=True)
    done.add_argument("--attempt-id", required=True)
    done.add_argument("--artifact", required=True)
    done.add_argument("--target", help="目标 canonical State；提供后调用 bsk transition")
    done.add_argument("--submission", help="required Verifier component-result JSON（可选；由 close 内部记录 Gate）")
    done.add_argument("--skill-root", default=str(Path(__file__).resolve().parents[1]))
    done.set_defaults(func=complete)
    args = parser.parse_args()
    try:
        print(json.dumps(args.func(args), ensure_ascii=False, indent=2))
    except (OSError, ValueError) as exc:
        print(json.dumps({"status": "rejected", "error": str(exc)}, ensure_ascii=False, indent=2))
        raise SystemExit(2)


if __name__ == "__main__":
    main()
