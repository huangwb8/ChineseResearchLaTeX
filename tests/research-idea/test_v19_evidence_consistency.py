"""research-idea v19 领域证据一致性回归。"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
SKILL = ROOT / "skills/research-idea"
sys.path.insert(0, str(SKILL / "scripts"))

from edge_rules import completion_evidence_errors  # noqa: E402


def digest(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def write(path: Path, content: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def evidence_fixture(tmp_path: Path, *, fulltext: bool = False) -> tuple[Path, dict]:
    task = tmp_path / ".bensz-api/task-v19"
    depth = "fulltext" if fulltext else "abstract"
    interpretation = write(
        task / "research-literature-interpretation/output/R1/interpretation.md",
        "---\n"
        "interpretation_contract: research-literature-interpretation-evidence-v1\n"
        "source_id: R1\n"
        f"evidence_depth: {depth}\n"
        f"read_scope: {depth}-only\n"
        "stable_citation: doi:10.0000/fixture\n"
        "---\n\n# Fixture\n",
    )
    result = write(task / "parallel-vibe/output/round1/reviewer1.md", "review\n")
    thread = write(
        task / "parallel-vibe/output/round1/thread.json",
        json.dumps({
            "thread_id": "thread-1",
            "agent_id": "agent-1",
            "agent_label": "novelty-reviewer",
            "model": "fixture-model",
            "input_snapshot_hash": "sha256:input",
            "status": "completed",
        }),
    )
    done = write(
        task / "parallel-vibe/output/round1/done.json",
        json.dumps({
            "status": "completed",
            "exit_code": 0,
            "started_at": "2026-09-20T00:00:00Z",
            "ended_at": "2026-09-20T00:01:00Z",
        }),
    )
    interpretation_record = {
        "path": interpretation.relative_to(task).as_posix(),
        "source_id": "R1",
        "evidence_depth": depth,
        "read_scope": f"{depth}-only",
        "stable_citation": "doi:10.0000/fixture",
        "execution_receipt": {
            "schema": "research-idea-interpretation-receipt-v1",
            "identity_proof": "isolated-task",
            "task_id": "paper-R1",
            "status": "completed",
            "input_snapshot_hash": "sha256:paper-input",
            "output_hash": digest(interpretation),
        },
    }
    if fulltext:
        source = write(task / "research-literature-interpretation/input/R1/fulltext.pdf", "fixture pdf")
        interpretation_record["fulltext_source"] = {
            "path": source.relative_to(task).as_posix(),
            "sha256": digest(source),
        }
    reviewer = {
        "receipt_schema": "research-idea-reviewer-receipt-v1",
        "thread_path": thread.relative_to(task).as_posix(),
        "done_path": done.relative_to(task).as_posix(),
        "path": result.relative_to(task).as_posix(),
        "thread_id": "thread-1",
        "agent_id": "agent-1",
        "agent_label": "novelty-reviewer",
        "model": "fixture-model",
        "input_snapshot_hash": "sha256:input",
        "thread_status": "completed",
        "runner_status": "completed",
        "started_at": "2026-09-20T00:00:00Z",
        "ended_at": "2026-09-20T00:01:00Z",
        "exit_code": 0,
        "output_hash": digest(result),
    }
    index = {
        "schema": "research-idea-completion-v6",
        "dependencies": {"research-literature-interpretation": [interpretation_record]},
        "review": {"rounds": [{"round": 1, "reviewers": [reviewer]}]},
    }
    index_path = write(
        task / "research-idea/output/completion-evidence.json",
        json.dumps(index, ensure_ascii=False),
    )
    return index_path, index


def codes(task: Path, index_path: Path) -> set[str]:
    return {item["code"] for item in completion_evidence_errors(task, index_path)}


def test_v6_evidence_sources_and_receipts_converge(tmp_path: Path):
    index_path, _ = evidence_fixture(tmp_path, fulltext=True)
    assert completion_evidence_errors(index_path.parents[2], index_path) == []


def test_interpretation_depth_cannot_cross_fill_source_metadata(tmp_path: Path):
    index_path, index = evidence_fixture(tmp_path)
    index["dependencies"]["research-literature-interpretation"][0]["evidence_depth"] = "fulltext"
    index_path.write_text(json.dumps(index), encoding="utf-8")
    actual = codes(index_path.parents[2], index_path)
    assert "interpretation_metadata_mismatch" in actual
    assert "fulltext_source_missing" in actual


def test_fulltext_claim_requires_matching_source_hash(tmp_path: Path):
    index_path, index = evidence_fixture(tmp_path, fulltext=True)
    index["dependencies"]["research-literature-interpretation"][0]["fulltext_source"]["sha256"] = "sha256:wrong"
    index_path.write_text(json.dumps(index), encoding="utf-8")
    assert "fulltext_source_hash_mismatch" in codes(index_path.parents[2], index_path)


def test_symlinked_fulltext_source_is_not_accepted(tmp_path: Path):
    index_path, index = evidence_fixture(tmp_path, fulltext=True)
    record = index["dependencies"]["research-literature-interpretation"][0]
    source = index_path.parents[2] / record["fulltext_source"]["path"]
    actual = source.with_name("actual-fulltext.pdf")
    source.rename(actual)
    source.symlink_to(actual)
    assert "fulltext_source_invalid" in codes(index_path.parents[2], index_path)


def test_reviewer_summary_cannot_cross_fill_another_receipt(tmp_path: Path):
    index_path, index = evidence_fixture(tmp_path)
    index["review"]["rounds"][0]["reviewers"][0]["agent_id"] = "agent-2"
    index_path.write_text(json.dumps(index), encoding="utf-8")
    assert "reviewer_receipt_mismatch" in codes(index_path.parents[2], index_path)


def test_host_agent_claim_requires_agent_receipt_identity(tmp_path: Path):
    index_path, index = evidence_fixture(tmp_path)
    receipt = index["dependencies"]["research-literature-interpretation"][0]["execution_receipt"]
    receipt["identity_proof"] = "host-agent"
    index_path.write_text(json.dumps(index), encoding="utf-8")
    assert "interpretation_receipt_invalid" in codes(index_path.parents[2], index_path)
