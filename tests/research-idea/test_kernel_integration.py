"""直接验证文档的 Kernel 接入；合成回传不证明科研充分性。"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

import pytest
from bensz_skill_kernel.states import SkillStateDeclaration
from bensz_skill_kernel.verifiers import FilesystemVerifierRegistry, builtin_verifier_root
from bensz_skill_kernel.workspace import TaskWorkspace

ROOT = Path(__file__).resolve().parents[2]
SKILL = ROOT / "skills/research-idea"
PREFIX = "bensz.research-ideation."
VERIFIER = "bensz.research.stage-readiness"
MERIT_VERIFIER = "bensz.research.hypothesis-merit"
BINDINGS = ("pack_id", "pack_version", "package_kind", "component_id", "component_type", "contract_hash", "component_hash", "plan_hash", "run_id", "attempt_id", "handoff_hash")
RUN_ID = "fixture-run"
ATTEMPT_ID = "fixture-attempt"


def bsk(*args, cwd=None):
    result = subprocess.run([sys.executable, "-m", "bensz_skill_kernel.cli", *map(str, args)], cwd=cwd, capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
    return json.loads(result.stdout)


@pytest.fixture
def workspace(tmp_path):
    task = tmp_path / ".bensz-api/task-fixture"
    bsk("workspace", "init", tmp_path, "--task-root", task)
    result = bsk(
        "state", "transition", task, "research-idea", PREFIX + "literature",
        "--skill-root", SKILL, "--run-id", RUN_ID, "--attempt-id", ATTEMPT_ID,
    )
    assert result["status"] == "transitioned"
    return TaskWorkspace.open_existing(task)


def request(workspace, source="literature", target="candidates", operation="advance", attempt=ATTEMPT_ID):
    path = workspace.paths("research-idea").path("input") / f"{attempt}.json"
    evidence_path = path.with_suffix(".md")
    evidence_path.write_text("合成证据，只验证接口与绑定。", encoding="utf-8")
    data = {
        "run_id": RUN_ID, "attempt_id": attempt,
        "subject": {"operation": operation, "source": PREFIX + source, "target": PREFIX + target},
        "context": {"rounds": 1, "agents": 1, "sources": {"fixture": {"role": "map", "path": str(evidence_path.relative_to(workspace.task_root.parent.parent))}}},
        "evidence": [{"ref": "fixture", "summary": "合成协议材料", "source_type": "test-only", "content_hash": "sha256:" + hashlib.sha256(evidence_path.read_bytes()).hexdigest()}],
    }
    path.write_text(json.dumps(data), encoding="utf-8")
    return path, data


def run_documented_api(workspace, path, submission=None, skill=SKILL, expect_success=True):
    data = json.loads(path.read_text())
    command = [
        sys.executable,
        str(skill / "scripts/phase_entry.py"),
        "--project-root", str(workspace.task_root.parent.parent),
        "--task-root", str(workspace.task_root),
        "--skill-root", str(skill),
        "--action", data["subject"]["source"].rsplit(".", 1)[-1],
        "--input", str(path),
    ]
    if submission is not None:
        sub_path = path.with_suffix(".result.json")
        items = submission if isinstance(submission, list) else [submission]
        sub_path.write_text(json.dumps({"submissions": items}))
        command.extend(["--submissions", str(sub_path)])
    result = subprocess.run(command, capture_output=True, text=True)
    if not expect_success:
        assert result.returncode != 0
        return result
    payload = json.loads(result.stdout)
    if payload.get("status") != "rejected":
        assert result.returncode == 0, result.stdout + result.stderr
    return payload


def bound_submission(handoff, verdict="pass"):
    return {
        **{key: handoff[key] for key in BINDINGS},
        "protocol": "bensz-contract-component-result-v1",
        "execution_status": verdict if verdict in {"error", "timed_out", "skipped", "unchecked"} else "completed", "verdict": verdict,
        "executor": {"type": "agent", "id": "synthetic-test", "model": "synthetic-only"},
        "evidence_refs": ["fixture"], "findings": [],
        "facts": {"summary": "只测试协议", "confidence": 0.5, "uncertainties": [] if verdict == "pass" else ["合成缺口"]},
    }


def bound_submissions(handoffs, verdict="pass"):
    return [bound_submission(handoff, verdict) for handoff in handoffs]


def transition(workspace, data, target=None, skill=SKILL):
    return bsk("state", "transition", workspace.task_root, "research-idea", target or data["subject"]["target"], "--skill-root", skill, "--run-id", data["run_id"], "--attempt-id", data["attempt_id"])


def test_local_pack_and_initial_state_are_discoverable(workspace):
    declaration = SkillStateDeclaration.from_skill_root(SKILL)
    assert declaration.initial_state == PREFIX + "literature"
    assert len(declaration.states) == 5
    assert len(declaration.verifier_requirements()) == 2
    registry = FilesystemVerifierRegistry(SKILL / "references/verifiers")
    stage_definition = registry.resolve(VERIFIER)
    merit_definition = registry.resolve(MERIT_VERIFIER)
    assert [component.type for component in stage_definition.contract_pack().components] == ["agent"]
    assert [component.id for component in merit_definition.contract_pack().components] == ["merit-review"]
    assert workspace.read_meta_state("research-idea")["current_state"] == PREFIX + "literature"


@pytest.mark.parametrize("verdict", [None, "fail", "uncertain", "unchecked", "error", "timed_out", "skipped"])
def test_required_missing_or_nonpass_never_advances(workspace, verdict):
    path, data = request(workspace)
    if verdict is not None:
        pending = run_documented_api(workspace, path)
        assert pending["status"] == "awaiting_agent"
        submissions = bound_submissions(pending["handoffs"])
        submissions[0] = bound_submission(pending["handoffs"][0], verdict)
        result = run_documented_api(workspace, path, submissions)
        assert result["gate"]["decision"] != "allow"
    rejected = transition(workspace, data)
    assert rejected["status"] == "rejected"  # CLI exit 0 is not a passing transition.
    assert workspace.read_meta_state("research-idea")["current_state"] == PREFIX + "literature"


def test_stage_pass_without_merit_pass_never_advances(workspace):
    path, data = request(workspace)
    pending = run_documented_api(workspace, path)
    result = run_documented_api(workspace, path, bound_submission(pending["handoffs"][0]))
    assert result["status"] == "awaiting_agent"
    rejected = transition(workspace, data)
    assert rejected["status"] == "rejected"


@pytest.mark.parametrize("field", ["run_id", "attempt_id", "contract_hash", "plan_hash", "component_hash", "handoff_hash"])
def test_kernel_rejects_wrong_binding(workspace, field):
    path, data = request(workspace)
    pending = run_documented_api(workspace, path)
    submissions = bound_submissions(pending["handoffs"])
    submissions[0][field] = "wrong"
    run_documented_api(workspace, path, submissions, expect_success=False)
    assert transition(workspace, data)["status"] == "rejected"


def test_changed_request_cannot_reuse_bound_result(workspace):
    path, data = request(workspace)
    pending = run_documented_api(workspace, path)
    data["evidence"][0]["content_hash"] = "sha256:changed"
    path.write_text(json.dumps(data))
    run_documented_api(workspace, path, bound_submissions(pending["handoffs"]), expect_success=False)


def test_same_identity_forward_resume_and_terminal(workspace):
    steps = [
        ("literature", "candidates"),
        ("candidates", "review"),
        ("review", "reporting"),
        ("reporting", "completed"),
    ]
    for source, target in steps:
        path, data = request(workspace, source, target, "advance")
        pending = run_documented_api(workspace, path)
        allowed = run_documented_api(workspace, path, bound_submissions(pending["handoffs"]))
        assert allowed["gate"]["computed_by"] == "kernel"
        assert allowed["gate"]["decision"] == "allow"
        assert allowed["status"] == "transitioned"
        resumed = TaskWorkspace.open_existing(workspace.task_root)
        assert resumed.read_meta_state("research-idea")["current_state"] == PREFIX + target
    assert transition(workspace, data, PREFIX + "literature")["status"] == "rejected"
    bsk("status", workspace.events)
    bsk("rebuild", workspace.events)


def test_jump_and_new_attempt_without_gate_are_rejected(workspace):
    path, data = request(workspace)
    pending = run_documented_api(workspace, path)
    run_documented_api(workspace, path, bound_submissions(pending["handoffs"]))
    assert transition(workspace, data, PREFIX + "completed")["status"] == "rejected"
    data["attempt_id"] = "new-without-review"
    assert transition(workspace, data)["status"] == "rejected"


def test_pending_snapshot_is_not_silently_reinitialized(workspace):
    snapshot = workspace.paths("research-idea").meta_state
    snapshot.with_name(snapshot.name + ".tmp").write_text("{}")
    with pytest.raises(ValueError, match="incomplete commit"):
        workspace.read_meta_state("research-idea")


def init_data(project, task, skill=SKILL, *extra):
    return subprocess.run([sys.executable, str(skill / "scripts/init_workspace.py"), "--cwd", str(project), "--task-root", str(task.relative_to(project)), "--input-label", "fixture", "--repo-name", "fixture", "--pr-name", "manual", "--skip-dependency-check", *extra], capture_output=True, text=True)


def test_initializer_only_writes_research_data(workspace):
    before = workspace.events.read_bytes()
    project = workspace.task_root.parent.parent
    result = init_data(project, workspace.task_root, SKILL, "--rounds", "2", "--agents", "1")
    assert result.returncode == 0, result.stderr
    scoped = workspace.paths("research-idea")
    manifest = json.loads((scoped.path("input") / "manifest.json").read_text())
    assert manifest["settings"] == {"rounds": 2, "agents": 1, "allow_custom_name": False}
    assert manifest["output_path"].startswith("docs/ideas/")
    schema = json.loads((scoped.path("output") / "candidate-schema.json").read_text())
    assert schema["candidates"] == [] and schema["candidate_example"]
    assert schema["outcome"] == "insufficient"
    assert workspace.events.read_bytes() == before
    assert init_data(project, workspace.task_root).returncode != 0


def test_initializer_requires_existing_workspace_and_rejects_invalid_settings(tmp_path, workspace):
    missing = tmp_path / ".bensz-api/task-missing"
    assert init_data(tmp_path, missing).returncode != 0
    assert not missing.exists()
    project = workspace.task_root.parent.parent
    assert init_data(project, workspace.task_root, SKILL, "--rounds", "0").returncode != 0
    assert not (workspace.paths("research-idea").path("input") / "manifest.json").exists()


def test_initializer_rejects_symlink_and_hidden_output(workspace, tmp_path):
    project = workspace.task_root.parent.parent
    assert init_data(project, workspace.task_root, SKILL, "--output-dir", ".hidden").returncode != 0
    input_dir = workspace.paths("research-idea").path("input")
    outside = tmp_path / "outside"
    outside.mkdir()
    (input_dir / "manifest.json").symlink_to(outside / "manifest.json")
    assert init_data(project, workspace.task_root).returncode != 0
    assert not (outside / "manifest.json").exists()


def test_copied_skill_is_relocatable(workspace, tmp_path):
    copied = tmp_path / "portable/research-idea"
    shutil.copytree(SKILL, copied, ignore=shutil.ignore_patterns("__pycache__"))
    declaration = SkillStateDeclaration.from_skill_root(copied)
    assert declaration.initial_state == PREFIX + "literature"
    result = init_data(workspace.task_root.parent.parent, workspace.task_root, copied)
    assert result.returncode == 0, result.stderr
    path, data = request(workspace)
    pending = run_documented_api(workspace, path, skill=copied)
    result = run_documented_api(workspace, path, bound_submissions(pending["handoffs"]), skill=copied)
    assert result["status"] == "transitioned"


def test_native_file_verifier_alias_and_path_scope(tmp_path):
    registry = FilesystemVerifierRegistry(builtin_verifier_root())
    assert registry.resolve("artifact.file-exists").spec.verifier_id == "bensz.artifact.file-existence"
    result = registry.run_contract("bensz.artifact.path-scope", {"subject": {"paths": [str(tmp_path.parent / "outside")]}, "context": {"allowed_paths": [str(tmp_path)]}})
    assert result.aggregate.verdict == "fail"


def test_no_skill_runtime_or_script_pack_remains():
    assert {p.name for p in (SKILL / "scripts").glob("*.py")} == {
        "check_completion.py",
        "init_workspace.py",
        "validate_report.py",
        "check_dependencies.py",
        "phase_entry.py",
    }
    assert not list((SKILL / "references").rglob("*.py"))


@pytest.mark.parametrize("field,value", [("context", []), ("evidence", "invalid")])
def test_kernel_rejects_malformed_request(workspace, field, value):
    path, data = request(workspace)
    data[field] = value
    path.write_text(json.dumps(data))
    before = workspace.events.read_bytes()
    run_documented_api(workspace, path, expect_success=False)
    assert workspace.events.read_bytes() == before
