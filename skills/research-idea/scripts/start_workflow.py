#!/usr/bin/env python3
"""原子启动 research-idea：预检环境、创建工作区、进入 v2 literature 并初始化资料。"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from typing import Any

from bensz_skill_kernel import __version__ as kernel_version
from bensz_skill_kernel.identity import kernel_capabilities
from bensz_skill_kernel.workspace import TaskWorkspace

from check_dependencies import find_skill, load_config

REQUIRED_CAPABILITIES = {
    "state_visit_identity",
    "atomic_target_identity_handoff",
    "attempt_supersede",
    "state_bound_verifier_gate",
    "state_bound_action_authorization",
}
INITIAL_STATE = "bensz.research-ideation.literature"


class StartError(ValueError):
    def __init__(self, code: str, message: str, **details: Any):
        super().__init__(message)
        self.code = code
        self.details = details

    def to_dict(self) -> dict[str, Any]:
        return {"status": "rejected", "error_code": self.code, "error": str(self), **self.details}


def sha256(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def atomic_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    staged: Path | None = None
    try:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
            handle.write(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
            staged = Path(handle.name)
        staged.replace(path)
    finally:
        if staged is not None:
            staged.unlink(missing_ok=True)


def critical_files(skill_root: Path) -> dict[str, str]:
    paths = [
        skill_root / "config.yaml",
        skill_root / "scripts/start_workflow.py",
        skill_root / "scripts/init_workspace.py",
        skill_root / "scripts/phase_entry.py",
        *sorted((skill_root / "references/states").glob("*/STATE.md")),
        *sorted((skill_root / "references/verifiers").glob("*/VERIFIER.md")),
    ]
    return {path.relative_to(skill_root).as_posix(): sha256(path) for path in paths}


def check_interpreter() -> dict[str, Any]:
    executable = Path(sys.executable).resolve()
    bsk = shutil.which("bsk")
    if not bsk:
        raise StartError("kernel_cli_missing", "当前环境找不到 bsk CLI")
    first_line = Path(bsk).read_text(encoding="utf-8", errors="replace").splitlines()[0]
    if not first_line.startswith("#!"):
        raise StartError("kernel_interpreter_mismatch", "bsk 入口没有可核对的解释器声明")
    cli_python = Path(first_line[2:].strip().split()[0]).resolve()
    if cli_python != executable:
        raise StartError(
            "kernel_interpreter_mismatch",
            "当前 Python 与 bsk CLI 不属于同一解释器环境",
            python=executable.name,
            bsk_python=cli_python.name,
        )
    return {
        "implementation": sys.implementation.name,
        "version": ".".join(map(str, sys.version_info[:3])),
        "executable_name": executable.name,
        "bsk_entrypoint_hash": sha256(Path(bsk)),
        "same_environment": True,
    }


def run_kernel(args: list[str], code: str) -> dict[str, Any]:
    result = subprocess.run(
        [sys.executable, "-m", "bensz_skill_kernel.cli", *args],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise StartError(code, result.stderr.strip() or result.stdout.strip() or "BSK 执行失败")
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise StartError(code, "BSK 未返回合法 JSON") from exc
    if payload.get("status") not in {"ready", "transitioned"}:
        raise StartError(code, payload.get("reason") or "BSK 拒绝请求", kernel_result=payload)
    return payload


def validate_task_root(project: Path, raw: str) -> tuple[Path, str]:
    relative = Path(raw)
    if relative.is_absolute():
        task = relative.expanduser().resolve()
        try:
            relative = task.relative_to(project)
        except ValueError as exc:
            raise StartError("task_root_outside_project", "task-root 必须位于项目内") from exc
    else:
        task = (project / relative).resolve()
    if len(relative.parts) != 2 or relative.parts[0] != ".bensz-api" or not relative.name.startswith("task-"):
        raise StartError("task_root_invalid", "task-root 必须为项目内 .bensz-api/task-* 相对路径")
    if not task.is_relative_to(project):
        raise StartError("task_root_outside_project", "task-root 必须位于项目内")
    return task, relative.as_posix()


def run(args: argparse.Namespace) -> dict[str, Any]:
    project = Path(args.project_root).expanduser().resolve()
    skill_root = Path(__file__).resolve().parents[1]
    task, relative_task = validate_task_root(project, args.task_root)
    config = load_config()
    capabilities = kernel_capabilities(version=kernel_version)
    required_capabilities = set(config["runtime"].get("required_capabilities", REQUIRED_CAPABILITIES))
    missing = sorted(required_capabilities - set(capabilities["capabilities"]))
    if missing:
        raise StartError("kernel_capability_missing", "当前 Kernel 缺少 research-idea 必需能力", missing=missing)
    interpreter = check_interpreter()
    if args.expected_skill_version and args.expected_skill_version != config["skill_info"]["version"]:
        raise StartError(
            "skill_runtime_drift",
            "实际执行 Skill 版本与调用者期望不一致",
            expected=args.expected_skill_version,
            actual=config["skill_info"]["version"],
        )
    if not args.skip_dependency_check:
        deps = config["dependencies"]
        for name in deps["required_skills"]:
            names = [name, *deps.get("legacy_skill_aliases", {}).get(name, [])]
            if not any(find_skill(item, deps["search_roots"], project) for item in names):
                raise StartError("dependency_missing", f"缺少必需 Skill: {name}", dependency=name)

    run_kernel(["workspace", "init", str(project), "--task-root", str(task), "--description", "research-idea"], "workspace_init_failed")
    transition = run_kernel([
        "state", "transition", str(task), "research-idea", INITIAL_STATE,
        "--skill-root", str(skill_root), "--run-id", args.run_id,
        "--target-attempt-id", args.initial_attempt_id,
        "--idempotency-key", f"research-idea:{args.run_id}:initialize",
    ], "initial_state_failed")

    init_command = [
        sys.executable, str(skill_root / "scripts/init_workspace.py"),
        "--cwd", str(project), "--task-root", relative_task,
        "--input-label", args.input_label,
    ]
    for option, value in (("--output-dir", args.output_dir), ("--repo-name", args.repo_name), ("--pr-name", args.pr_name), ("--rounds", args.rounds), ("--agents", args.agents)):
        if value is not None:
            init_command.extend([option, str(value)])
    if args.allow_custom_name:
        init_command.append("--allow-custom-name")
    init_command.append("--skip-dependency-check")
    initialized = subprocess.run(init_command, capture_output=True, text=True)
    if initialized.returncode != 0:
        raise StartError(
            "research_data_init_failed",
            initialized.stderr.strip() or initialized.stdout.strip() or "研究资料初始化失败",
            recovery="State 身份已安全建立；修正输入后以相同 run/attempt 重放启动入口",
        )

    workspace = TaskWorkspace.open_existing(task)
    state = workspace.read_meta_state("research-idea")
    files = critical_files(skill_root)
    snapshot = {
        "protocol": "research-idea-runtime-snapshot-v1",
        "skill": {
            "name": "research-idea",
            "version": config["skill_info"]["version"],
            "root_kind": "project" if skill_root.is_relative_to(project) else "installed",
            "files": files,
            "source_hash": "sha256:" + hashlib.sha256(json.dumps(files, sort_keys=True).encode()).hexdigest(),
        },
        "kernel": {
            "version": kernel_version,
            "capabilities": capabilities["capabilities"],
            "identity_protocol": capabilities["state_identity_protocol"],
        },
        "interpreter": interpreter,
        "identity": {
            "run_id": state["run_id"],
            "state_visit_id": state["state_visit_id"],
            "attempt_id": state["active_attempt_id"],
        },
    }
    snapshot_path = workspace.paths("research-idea").path("log") / "runtime-snapshot.json"
    atomic_json(snapshot_path, snapshot)
    manifest_path = workspace.paths("research-idea").path("input") / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest.update({
        "control_contract": "research-idea-control-v4",
        "run_id": state["run_id"],
        "initial_state_visit_id": state["state_visit_id"],
        "initial_attempt_id": state["active_attempt_id"],
        "runtime_snapshot": "research-idea/log/runtime-snapshot.json",
    })
    atomic_json(manifest_path, manifest)
    return {
        "status": "initialized",
        "task_root": relative_task,
        "current_state": state["current_state"],
        "run_id": state["run_id"],
        "state_visit_id": state["state_visit_id"],
        "attempt_id": state["active_attempt_id"],
        "runtime_snapshot": "research-idea/log/runtime-snapshot.json",
        "transition": transition,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--task-root", required=True)
    parser.add_argument("--input-label", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--initial-attempt-id", required=True)
    parser.add_argument("--expected-skill-version")
    parser.add_argument("--output-dir")
    parser.add_argument("--repo-name")
    parser.add_argument("--pr-name")
    parser.add_argument("--rounds", type=int)
    parser.add_argument("--agents", type=int)
    parser.add_argument("--allow-custom-name", action="store_true")
    parser.add_argument("--skip-dependency-check", action="store_true", help="仅开发测试使用")
    args = parser.parse_args()
    try:
        payload = run(args)
    except (OSError, KeyError, ValueError) as exc:
        error = exc if isinstance(exc, StartError) else StartError("startup_error", str(exc))
        print(json.dumps(error.to_dict(), ensure_ascii=False, indent=2))
        raise SystemExit(2)
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
