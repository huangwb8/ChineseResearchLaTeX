"""research-idea 轻量 BSK 阶段入口回归。"""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

import pytest
from bensz_skill_kernel.workspace import TaskWorkspace

ROOT = Path(__file__).resolve().parents[2]
SKILL = ROOT / "skills/research-idea"
SCRIPT = SKILL / "scripts/phase_entry.py"
START = SKILL / "scripts/start_workflow.py"
BINDINGS = (
    "pack_id", "pack_version", "package_kind", "component_id",
    "component_type", "contract_hash", "component_hash", "plan_hash",
    "run_id", "state_visit_id", "attempt_id", "handoff_hash",
)
RUN_ID = "run-1"
ATTEMPT_ID = "run-attempt-1"


def bsk(*args: object) -> dict:
    result = subprocess.run(
        [sys.executable, "-m", "bensz_skill_kernel.cli", *map(str, args)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return json.loads(result.stdout)


@pytest.fixture
def workspace(tmp_path: Path) -> TaskWorkspace:
    task = tmp_path / ".bensz-api/task-fixture"
    result = subprocess.run(
        [
            sys.executable, str(START), "--project-root", str(tmp_path),
            "--task-root", ".bensz-api/task-fixture", "--input-label", "fixture",
            "--repo-name", "fixture", "--pr-name", "manual", "--run-id", RUN_ID,
            "--initial-attempt-id", ATTEMPT_ID, "--skip-dependency-check",
        ], capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return TaskWorkspace.open_existing(task)


def input_file(workspace: TaskWorkspace, action: str = "literature") -> Path:
    path = workspace.paths("research-idea").path("input") / f"{action}.json"
    path.write_text(
        json.dumps({
            "context": {"sources": {"fixture": {"role": "map"}}},
            "evidence": [{
                "ref": "fixture", "source_type": "test-only",
                "summary": "只验证 BSK 编排", "content_hash": "sha256:fixture",
            }],
        }),
        encoding="utf-8",
    )
    return path


def run_entry(workspace: TaskWorkspace, input_path: Path, *extra: str) -> subprocess.CompletedProcess[str]:
    action = extra[extra.index("--action") + 1]
    started = subprocess.run(
        [
            sys.executable, str(SCRIPT), "--project-root", str(workspace.task_root.parent.parent),
            "--task-root", str(workspace.task_root), "--mode", "start", "--action", action,
        ],
        capture_output=True,
        text=True,
    )
    if started.returncode != 0:
        return started
    return subprocess.run(
        [
            sys.executable, str(SCRIPT), "--project-root", str(workspace.task_root.parent.parent),
            "--task-root", str(workspace.task_root), "--mode", "finish", "--input", str(input_path), *extra,
        ],
        capture_output=True,
        text=True,
    )


def bound_result(handoff: dict) -> dict:
    return {
        **{key: handoff[key] for key in BINDINGS},
        "protocol": "bensz-contract-component-result-v1",
        "execution_status": "completed",
        "verdict": "pass",
        "executor": {"type": "agent", "id": "synthetic-test", "model": "synthetic-only"},
        "facts": {"summary": "只测试绑定与阶段编排", "confidence": 0.5, "uncertainties": []},
        "evidence_refs": ["fixture"],
        "findings": [],
    }


def test_wrong_action_is_rejected_without_private_runtime_files(workspace: TaskWorkspace):
    result = run_entry(workspace, input_file(workspace), "--action", "candidates")
    assert result.returncode != 0
    assert "要求当前 State" in json.loads(result.stdout)["error"]
    assert not (workspace.paths("research-idea").path("log") / "attempts").exists()
    assert not (workspace.paths("research-idea").path("input") / "attempts").exists()


def test_entry_returns_native_handoffs_then_kernel_gate_and_transition(workspace: TaskWorkspace):
    input_path = input_file(workspace)
    pending = run_entry(workspace, input_path, "--action", "literature")
    assert pending.returncode == 0, pending.stderr
    payload = json.loads(pending.stdout)
    assert payload["status"] == "awaiting_agent"
    assert len(payload["handoffs"]) == 2
    assert all(item["protocol"] == "bensz-contract-execution-v1" for item in payload["handoffs"])

    submissions = input_path.with_name("submissions.json")
    submissions.write_text(
        json.dumps({"submissions": [bound_result(item) for item in payload["handoffs"]]}),
        encoding="utf-8",
    )
    completed = run_entry(
        workspace, input_path, "--action", "literature", "--submissions", str(submissions)
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    result = json.loads(completed.stdout)
    assert result["status"] == "transitioned"
    assert result["identity_mode"] == "state-visit-v2"
    assert result["run_id"] == RUN_ID
    assert result["gate"]["decision"] == "allow"
    assert result["transition"]["status"] == "transitioned"
    assert workspace.read_meta_state("research-idea")["current_state"] == "bensz.research-ideation.candidates"
    assert not (workspace.paths("research-idea").path("log") / "attempts").exists()


def test_nonpass_submission_does_not_transition(workspace: TaskWorkspace):
    input_path = input_file(workspace)
    pending = json.loads(run_entry(workspace, input_path, "--action", "literature").stdout)
    results = [bound_result(item) for item in pending["handoffs"]]
    results[0]["verdict"] = "fail"
    results[0]["facts"]["uncertainties"] = ["合成缺口"]
    submissions = input_path.with_name("failed-submissions.json")
    submissions.write_text(json.dumps({"submissions": results}), encoding="utf-8")
    rejected = run_entry(
        workspace, input_path, "--action", "literature", "--submissions", str(submissions)
    )
    assert rejected.returncode != 0
    assert json.loads(rejected.stdout)["status"] == "rejected"
    assert workspace.read_meta_state("research-idea")["current_state"] == "bensz.research-ideation.literature"


def test_initial_transition_without_identity_is_rejected_before_handoff(tmp_path: Path):
    task = tmp_path / ".bensz-api/task-no-identity"
    bsk("workspace", "init", tmp_path, "--task-root", task)
    result = bsk(
        "state", "transition", task, "research-idea",
        "bensz.research-ideation.literature", "--skill-root", SKILL,
    )
    assert result["status"] == "transitioned"
    unbound = TaskWorkspace.open_existing(task)
    rejected = run_entry(unbound, input_file(unbound), "--action", "literature")
    payload = json.loads(rejected.stdout)
    assert rejected.returncode != 0
    assert payload["error_code"] == "legacy_state_identity"
    assert "新任务" in payload["recovery"] or "旧记录" in payload["recovery"]


def test_claimed_new_attempt_is_rejected_before_verifier_events(workspace: TaskWorkspace):
    before = workspace.events.read_bytes()
    rejected = run_entry(
        workspace,
        input_file(workspace),
        "--action", "literature",
        "--run-id", RUN_ID,
        "--attempt-id", "retry-2",
    )
    payload = json.loads(rejected.stdout)
    assert rejected.returncode != 0
    assert payload["error_code"] == "state_identity_mismatch"
    assert payload["active_attempt_id"] == ATTEMPT_ID
    new_events = workspace.events.read_bytes()[len(before):]
    assert b"verification.result" not in new_events
    assert b"verification.gate" not in new_events


def test_all_forward_states_create_new_visit_identity(workspace: TaskWorkspace):
    for action, target in (
        ("literature", "candidates"),
        ("candidates", "review"),
        ("review", "reporting"),
        ("reporting", "completed"),
    ):
        path = input_file(workspace, action)
        pending = json.loads(run_entry(workspace, path, "--action", action).stdout)
        assert pending["status"] == "awaiting_agent"
        before_visit = pending["state_visit_id"]
        assert pending["run_id"] == RUN_ID
        submissions = path.with_name(f"{action}-submissions.json")
        submissions.write_text(
            json.dumps({"submissions": [bound_result(item) for item in pending["handoffs"]]}),
            encoding="utf-8",
        )
        completed = run_entry(
            workspace, path, "--action", action, "--submissions", str(submissions)
        )
        assert completed.returncode == 0, completed.stdout + completed.stderr
        assert json.loads(completed.stdout)["status"] == "transitioned"
        assert workspace.read_meta_state("research-idea")["current_state"] == (
            "bensz.research-ideation." + target
        )
        assert workspace.read_meta_state("research-idea")["state_visit_id"] != before_visit


def test_second_state_accepts_explicit_attempt_supersede(workspace: TaskWorkspace):
    path = input_file(workspace)
    pending = json.loads(run_entry(workspace, path, "--action", "literature").stdout)
    submissions = path.with_name("literature-pass.json")
    submissions.write_text(
        json.dumps({"submissions": [bound_result(item) for item in pending["handoffs"]]}),
        encoding="utf-8",
    )
    advanced = run_entry(
        workspace, path, "--action", "literature", "--submissions", str(submissions)
    )
    assert advanced.returncode == 0
    result = subprocess.run(
        [
            sys.executable, str(SCRIPT), "--project-root", str(workspace.task_root.parent.parent),
            "--task-root", str(workspace.task_root), "--mode", "retry", "--action", "candidates",
            "--new-attempt-id", "candidates-2", "--reason", "new evidence",
        ], capture_output=True, text=True,
    )
    payload = json.loads(result.stdout)
    assert result.returncode == 0
    assert payload["attempt_id"] == "candidates-2"


def test_failed_gate_can_retry_with_superseded_attempt(workspace: TaskWorkspace):
    path = input_file(workspace)
    pending = json.loads(run_entry(workspace, path, "--action", "literature").stdout)
    failed_results = [bound_result(item) for item in pending["handoffs"]]
    failed_results[0]["verdict"] = "fail"
    failed_results[0]["facts"]["uncertainties"] = ["合成缺口"]
    failed = path.with_name("literature-failed.json")
    failed.write_text(json.dumps({"submissions": failed_results}), encoding="utf-8")
    rejected = run_entry(
        workspace, path, "--action", "literature", "--submissions", str(failed)
    )
    assert json.loads(rejected.stdout)["reason_code"] == "business_evidence_rejected"

    retried = subprocess.run(
        [
            sys.executable, str(SCRIPT), "--project-root", str(workspace.task_root.parent.parent),
            "--task-root", str(workspace.task_root), "--mode", "retry", "--action", "literature",
            "--new-attempt-id", "literature-2", "--reason", "evidence changed",
        ], capture_output=True, text=True,
    )
    assert retried.returncode == 0, retried.stdout
    data = json.loads(path.read_text(encoding="utf-8"))
    data["evidence"][0]["content_hash"] = "sha256:changed-after-failure"
    path.write_text(json.dumps(data), encoding="utf-8")
    retry = json.loads(run_entry(workspace, path, "--action", "literature").stdout)
    retry_results = path.with_name("literature-retry.json")
    retry_results.write_text(
        json.dumps({"submissions": [bound_result(item) for item in retry["handoffs"]]}),
        encoding="utf-8",
    )
    blocked = run_entry(
        workspace, path, "--action", "literature", "--submissions", str(retry_results)
    )
    assert blocked.returncode == 0, blocked.stdout
    assert json.loads(blocked.stdout)["status"] == "transitioned"
