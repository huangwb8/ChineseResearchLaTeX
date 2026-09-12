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
BINDINGS = (
    "pack_id", "pack_version", "package_kind", "component_id",
    "component_type", "contract_hash", "component_hash", "plan_hash",
    "run_id", "attempt_id", "handoff_hash",
)


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
    bsk("workspace", "init", tmp_path, "--task-root", task)
    result = bsk(
        "state", "transition", task, "research-idea",
        "bensz.research-ideation.literature", "--skill-root", SKILL,
    )
    assert result["status"] == "transitioned"
    return TaskWorkspace.open_existing(task)


def input_file(workspace: TaskWorkspace) -> Path:
    path = workspace.paths("research-idea").path("input") / "literature.json"
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
    return subprocess.run(
        [
            sys.executable, str(SCRIPT), "--project-root", str(workspace.task_root.parent.parent),
            "--task-root", str(workspace.task_root), "--run-id", "run-1",
            "--attempt-id", "literature-1", "--input", str(input_path), *extra,
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
