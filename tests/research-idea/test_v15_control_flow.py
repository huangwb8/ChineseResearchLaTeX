"""bac-v15 原子启动与 latest BSK 阶段门控回归。"""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import os
import shutil

from bensz_skill_kernel.runtime import EventLog
from bensz_skill_kernel.workspace import TaskWorkspace
from bensz_skill_kernel import __version__ as kernel_version

ROOT = Path(__file__).resolve().parents[2]
SKILL = ROOT / "skills/research-idea"
sys.path.insert(0, str(SKILL / "scripts"))
START = SKILL / "scripts/start_workflow.py"
PHASE = SKILL / "scripts/phase_entry.py"
RUN_ID = "v15-fixture-run"
BINDINGS = (
    "pack_id", "pack_version", "package_kind", "component_id", "component_type",
    "contract_hash", "component_hash", "plan_hash", "run_id", "state_visit_id",
    "attempt_id", "handoff_hash",
)


def run_json(*args: object) -> tuple[subprocess.CompletedProcess[str], dict]:
    result = subprocess.run([sys.executable, *map(str, args)], capture_output=True, text=True)
    payload = json.loads(result.stdout) if result.stdout.strip() else {}
    return result, payload


def start(tmp_path: Path) -> tuple[TaskWorkspace, dict]:
    task = tmp_path / ".bensz-api/task-v15"
    result, payload = run_json(
        START,
        "--project-root", tmp_path,
        "--task-root", ".bensz-api/task-v15",
        "--input-label", "fixture",
        "--repo-name", "fixture",
        "--pr-name", "manual",
        "--run-id", RUN_ID,
        "--initial-attempt-id", "literature-a1",
        "--skip-dependency-check",
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return TaskWorkspace.open_existing(task), payload


def test_single_start_entry_creates_v2_identity_and_runtime_snapshot(tmp_path: Path):
    workspace, payload = start(tmp_path)
    state = workspace.read_meta_state("research-idea")
    assert payload["status"] == "initialized"
    assert state["identity_protocol"] == "bensz-state-identity-v2"
    assert state["run_id"] == RUN_ID
    assert state["state_visit_id"]
    assert state["active_attempt_id"] == "literature-a1"
    snapshot = json.loads(
        (workspace.paths("research-idea").path("log") / "runtime-snapshot.json").read_text()
    )
    assert snapshot["skill"]["version"] == "0.12.0"
    assert snapshot["kernel"]["version"] == kernel_version
    assert "state_bound_action_authorization" in snapshot["kernel"]["capabilities"]
    assert all(not value.startswith("/") for value in snapshot["skill"]["files"])


def test_phase_start_consumes_state_bound_authorization(tmp_path: Path):
    workspace, _ = start(tmp_path)
    result, payload = run_json(
        PHASE,
        "--project-root", tmp_path,
        "--task-root", workspace.task_root,
        "--mode", "start",
        "--action", "literature",
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert payload["status"] == "authorized"
    projection = EventLog(workspace.events).projection()
    authorization = projection["action_authorizations"][payload["authorization_id"]]
    assert authorization["status"] == "consumed"
    assert authorization["state_visit_id"] == payload["state_visit_id"]
    assert authorization["attempt_id"] == "literature-a1"


def test_supersede_attempt_invalidates_old_authorization(tmp_path: Path):
    workspace, _ = start(tmp_path)
    _, authorized = run_json(
        PHASE, "--project-root", tmp_path, "--task-root", workspace.task_root,
        "--mode", "start", "--action", "literature",
    )
    pending = EventLog(workspace.events).preflight_action(
        skill="research-idea", action="literature", state="bensz.research-ideation.literature",
        state_version="4.0.0", run_id=RUN_ID,
        state_visit_id=authorized["state_visit_id"], attempt_id="literature-a1",
        idempotency_key="fixture:pending-before-retry",
    )
    result, payload = run_json(
        PHASE, "--project-root", tmp_path, "--task-root", workspace.task_root,
        "--mode", "retry", "--action", "literature",
        "--new-attempt-id", "literature-a2", "--reason", "evidence changed",
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert payload["status"] == "attempt_started"
    assert payload["attempt_id"] == "literature-a2"
    projection = EventLog(workspace.events).projection()
    assert projection["skill_states"]["research-idea"]["active_attempt_id"] == "literature-a2"
    denied = EventLog(workspace.events).consume_action_authorization(
        pending.payload["authorization_id"], skill="research-idea", action="literature",
        run_id=RUN_ID, state_visit_id=authorized["state_visit_id"], attempt_id="literature-a1",
    )
    assert denied.type == "action.authorization.denied"
    assert denied.payload["reason_code"] == "authorization_expired"


def test_legacy_initial_state_is_rejected_before_new_control_events(tmp_path: Path):
    task = tmp_path / ".bensz-api/task-legacy"
    result, _ = run_json(
        "-m", "bensz_skill_kernel.cli", "workspace", "init", tmp_path,
        "--task-root", task,
    )
    assert result.returncode == 0
    result, _ = run_json(
        "-m", "bensz_skill_kernel.cli", "state", "transition", task,
        "research-idea", "bensz.research-ideation.literature",
        "--skill-root", SKILL,
    )
    assert result.returncode == 0
    before = (task / "log/events.ndjson").read_bytes()
    rejected, payload = run_json(
        PHASE, "--project-root", tmp_path, "--task-root", task,
        "--mode", "start", "--action", "literature",
    )
    assert rejected.returncode != 0
    assert payload["error_code"] == "legacy_state_identity"
    assert (task / "log/events.ndjson").read_bytes() == before


def test_expected_skill_version_drift_fails_before_workspace_creation(tmp_path: Path):
    task = tmp_path / ".bensz-api/task-drift"
    result, payload = run_json(
        START, "--project-root", tmp_path, "--task-root", ".bensz-api/task-drift",
        "--input-label", "fixture", "--run-id", RUN_ID,
        "--initial-attempt-id", "literature-a1", "--expected-skill-version", "0.9.1",
        "--skip-dependency-check",
    )
    assert result.returncode != 0
    assert payload["error_code"] == "skill_runtime_drift"
    assert not task.exists()


def test_five_stage_v2_chain_has_no_control_break(tmp_path: Path):
    workspace, _ = start(tmp_path)
    for action in ("literature", "candidates", "review", "reporting"):
        started, authorized = run_json(
            PHASE, "--project-root", tmp_path, "--task-root", workspace.task_root,
            "--mode", "start", "--action", action,
        )
        assert started.returncode == 0, started.stdout + started.stderr
        input_path = workspace.paths("research-idea").path("input") / f"{action}.json"
        input_path.write_text(json.dumps({
            "context": {"sources": {"fixture": {"role": action}}},
            "evidence": [{"ref": "fixture", "source_type": "test-only", "summary": action, "content_hash": "sha256:fixture"}],
        }))
        pending_result, pending = run_json(
            PHASE, "--project-root", tmp_path, "--task-root", workspace.task_root,
            "--mode", "finish", "--action", action, "--input", input_path,
        )
        assert pending_result.returncode == 0, pending_result.stdout + pending_result.stderr
        submissions = []
        for handoff in pending["handoffs"]:
            submissions.append({
                **{key: handoff[key] for key in BINDINGS},
                "protocol": "bensz-contract-component-result-v1",
                "execution_status": "completed", "verdict": "pass",
                "executor": {"type": "agent", "id": "synthetic-test", "model": "synthetic-only"},
                "facts": {"summary": "synthetic binding test", "confidence": 0.5, "uncertainties": []},
                "evidence_refs": ["fixture"], "findings": [],
            })
        submission_path = input_path.with_name(f"{action}-submissions.json")
        submission_path.write_text(json.dumps({"submissions": submissions}))
        advanced, payload = run_json(
            PHASE, "--project-root", tmp_path, "--task-root", workspace.task_root,
            "--mode", "finish", "--action", action, "--input", input_path,
            "--submissions", submission_path,
        )
        assert advanced.returncode == 0, advanced.stdout + advanced.stderr
        assert payload["status"] == "transitioned"
        assert payload["target_identity"]["state_visit_id"] != authorized["state_visit_id"]

    import check_completion
    events = [json.loads(line) for line in workspace.events.read_text().splitlines() if line]
    required = [
        "bensz.research.stage-readiness@4.0.0",
        "bensz.research.hypothesis-merit@1.1.0",
    ]
    assert check_completion.first_control_break(
        events, "bensz.research-ideation.completed", required
    ) is None


def test_phase_rejects_skill_files_changed_after_start(tmp_path: Path):
    copied = tmp_path / "portable/research-idea"
    shutil.copytree(SKILL, copied)
    task = tmp_path / ".bensz-api/task-copy"
    result, _ = run_json(
        copied / "scripts/start_workflow.py", "--project-root", tmp_path,
        "--task-root", ".bensz-api/task-copy", "--input-label", "fixture",
        "--repo-name", "fixture", "--pr-name", "manual", "--run-id", RUN_ID,
        "--initial-attempt-id", "literature-a1", "--skip-dependency-check",
    )
    assert result.returncode == 0, result.stdout + result.stderr
    config = copied / "config.yaml"
    config.write_text(config.read_text().replace('version: "0.12.0"', 'version: "0.12.1"', 1))
    rejected, payload = run_json(
        copied / "scripts/phase_entry.py", "--project-root", tmp_path,
        "--task-root", task, "--mode", "start", "--action", "literature",
    )
    assert rejected.returncode != 0
    assert payload["error_code"] == "skill_runtime_drift"


def test_interpreter_mismatch_fails_before_workspace_creation(tmp_path: Path):
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    fake_bsk = fake_bin / "bsk"
    fake_bsk.write_text("#!/usr/bin/python3\n")
    fake_bsk.chmod(0o755)
    task = tmp_path / ".bensz-api/task-interpreter"
    env = {**os.environ, "PATH": str(fake_bin) + os.pathsep + os.environ.get("PATH", "")}
    result = subprocess.run([
        sys.executable, str(START), "--project-root", str(tmp_path),
        "--task-root", ".bensz-api/task-interpreter", "--input-label", "fixture",
        "--run-id", RUN_ID, "--initial-attempt-id", "literature-a1",
        "--skip-dependency-check",
    ], capture_output=True, text=True, env=env)
    payload = json.loads(result.stdout)
    assert result.returncode != 0
    assert payload["error_code"] == "kernel_interpreter_mismatch"
    assert not task.exists()
