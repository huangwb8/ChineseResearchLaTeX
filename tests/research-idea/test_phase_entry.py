"""统一阶段入口的 fail-closed 与 attempt 快照回归。"""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "skills/research-idea/scripts/phase_entry.py"


def make_task(tmp_path: Path, state: str = "bensz.research-ideation.literature") -> Path:
    task = tmp_path / ".bensz-api/task-fixture"
    scoped = task / "research-idea"
    (scoped / "input").mkdir(parents=True)
    (scoped / "log").mkdir(parents=True)
    (task / "log").mkdir(parents=True)
    (task / ".workspace.json").write_text(json.dumps({"protocol": "bensz-api-task-v1"}), encoding="utf-8")
    (scoped / "input/manifest.json").write_text(json.dumps({"skill": "research-idea"}), encoding="utf-8")
    (scoped / "log/meta-state.json").write_text(json.dumps({"current_state": state}), encoding="utf-8")
    (task / "log/events.ndjson").write_text("", encoding="utf-8")
    return task


def run(task: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, str(SCRIPT), *args, "--project-root", str(task.parent.parent), "--task-root", str(task)], capture_output=True, text=True)


def test_downstream_action_is_rejected_before_artifact(tmp_path: Path):
    task = make_task(tmp_path)
    result = run(task, "start", "--action", "candidates", "--artifact", "docs/ideas/candidates.json")
    assert result.returncode != 0
    payload = json.loads(result.stdout)
    assert payload["status"] == "rejected" and "state_mismatch" in payload["error"]
    assert not (task / "docs/ideas/candidates.json").exists()
    rejection = task / "research-idea/log/attempts/rejections.ndjson"
    assert rejection.is_file() and "state_mismatch" in rejection.read_text(encoding="utf-8")


def test_literature_start_creates_handoff_and_resume_detects_stale_manifest(tmp_path: Path):
    task = make_task(tmp_path)
    result = run(task, "start", "--action", "literature", "--artifact", "research-idea/output/map.md", "--attempt-id", "lit-1", "--run-id", "run-1")
    assert result.returncode == 0, result.stderr
    handoff = task / "research-idea/input/attempts/lit-1.json"
    attempt = task / "research-idea/log/attempts/lit-1.json"
    assert handoff.is_file() and attempt.is_file()
    data = json.loads(handoff.read_text(encoding="utf-8"))
    assert data["protocol"] == "research-idea-phase-handoff-v1" and data["handoff_hash"].startswith("sha256:")
    (task / "research-idea/input/manifest.json").write_text('{"changed":true}', encoding="utf-8")
    resumed = run(task, "resume", "--attempt-id", "lit-1", "--run-id", "run-1")
    assert resumed.returncode != 0 and "stale_manifest" in resumed.stdout
