"""research-idea 完成证据收敛检查回归。"""
from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "skills/research-idea/scripts"
sys.path.insert(0, str(SCRIPTS))

import check_completion  # noqa: E402
from bensz_skill_kernel.runtime import EventLog  # noqa: E402


PREFIX = "bensz.research-ideation."
RUN_ID = "run-1"
ATTEMPT_ID = "run-attempt-1"


def test_completed_semantics_separate_pipeline_readiness_from_claim_eligibility():
    results = [
        {
            "verifier_id": "bensz.research.stage-readiness",
            "facts": {
                "pipeline_ready": True,
                "scientific_evidence_sufficient": False,
                "claim_eligible": False,
            },
        },
        {
            "verifier_id": "bensz.research.hypothesis-merit",
            "facts": {"applicability": "not_applicable"},
        },
    ]
    errors = check_completion.completion_verifier_semantic_errors(results)
    assert any("scientific_evidence_sufficient" in error for error in errors)
    assert any("claim_eligible" in error for error in errors)
    assert any("不适用回执" in error for error in errors)


def test_completed_semantics_accept_applicable_scientifically_sufficient_results():
    results = [
        {
            "verifier_id": "bensz.research.stage-readiness",
            "facts": {
                "pipeline_ready": True,
                "scientific_evidence_sufficient": True,
                "claim_eligible": True,
            },
        },
        {
            "verifier_id": "bensz.research.hypothesis-merit",
            "facts": {"applicability": "applicable"},
        },
    ]
    assert check_completion.completion_verifier_semantic_errors(results) == []


def write(path: Path, text: str = "fixture") -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path.as_posix()


def report_text() -> str:
    return """---
report_contract: research-idea-report-v3
citation_style: gb-t-7714-2025-numeric
reference_map:
  R1: 1
outcome: recommended
exploration: complete
novelty: complete
review: complete
---
# 测试研究方向

## 结论与研究目标
评估测量边界是否构成有意义的研究问题。

## 研究脉络 map 摘要
<a id="opportunity-1"></a>O1：湿度适用边界[1](#ref-1)。

## 候选评估
### C1：测量边界

**科学问题**：环境条件是否改变测量误差的方向？
**可证伪科学假设**：控制真实浓度后，湿度改变测量偏差。
**关键预测**：相同浓度下，湿度变化引起有方向的误差。
**反证路径**：在预设精度范围内无差异将推翻该解释。
**价值与非平凡性**：确定既有测量结论的适用边界。
**创新性与颠覆潜力**：若成立将改写干燥条件外推到湿润环境的测量框架；若失败可排除湿度是主要偏差来源。
**最近工作与实质增量**：最近研究只覆盖干燥条件，湿度效应尚未测量。
**最强替代方向**：先改进参照测量；若误差来自参照则改变优先级。
**判断可信度与近期投入**：当前有限证据支持小规模鉴别观察。
**脉络依据**：[O1](#opportunity-1)，[1](#ref-1)
**查新结论**：部分研究但关键缺口存在；湿度边界缺乏验证。

## 查新摘要
候选级多查询与 canonical 覆盖是合成文本，不证明已执行真实查新。

## 风险与下一步
取得关键证据后重新判断边界。

## 推荐与投入排序
科学价值优先 C1；近期仅投入关键边界的观察。

## References
<a id="ref-1"></a>[1] 测试机构. 测量边界研究[J]. 测试期刊, 2024, 1(1): 1-5. DOI: 10.0000/example.
"""


def make_workspace(tmp_path: Path, *, state: str = PREFIX + "literature", custom_name: bool = True) -> tuple[Path, Path]:
    task = tmp_path / ".bensz-api/task-fixture"
    write(task / ".workspace.json", json.dumps({"protocol": "bensz-api-task-v1"}))
    write(
        task / "research-idea/input/manifest.json",
        json.dumps(
            {
                "skill": "research-idea",
                "settings": {"rounds": 3, "agents": 3, "allow_custom_name": custom_name},
                "output_path": "docs/ideas/Research-Idea_fixture_manual_20260911.md",
            }
        ),
    )
    write(task / "research-idea/log/meta-state.json", json.dumps({"current_state": state}))
    write(
        task / "log/events.ndjson",
        json.dumps(
            {
                "type": "state.transition",
                "event_id": "state-entry-literature",
                "run_id": RUN_ID,
                "attempt_id": ATTEMPT_ID,
                "payload": {
                    "skill": "research-idea",
                    "from_state": "bensz.workspace.ready",
                    "to_state": PREFIX + "literature",
                },
            }
        )
        + "\n",
    )
    report = tmp_path / "docs/ideas/v11.md"
    write(report, report_text())
    return task, report


def write_completion_events(task: Path) -> None:
    events = []
    for source, target in (
        ("literature", "candidates"),
        ("candidates", "review"),
        ("review", "reporting"),
        ("reporting", "completed"),
    ):
        for verifier_id, verifier_version in (
            ("bensz.research.stage-readiness", "4.1.0"),
            ("bensz.research.hypothesis-merit", "1.1.0"),
        ):
            events.append({
                "type": "verification.result",
                "run_id": RUN_ID,
                "attempt_id": ATTEMPT_ID,
                "payload": {
                    "verifier_id": verifier_id,
                    "verifier_version": verifier_version,
                    "execution_status": "completed",
                    "verdict": "pass",
                },
            })
        events.extend([
            {
                "type": "verification.gate",
                "event_id": f"gate-{source}",
                "run_id": RUN_ID,
                "attempt_id": ATTEMPT_ID,
                "payload": {
                    "decision": "allow",
                    "computed_by": "kernel",
                    "result_refs": [
                        "bensz.research.stage-readiness@4.1.0",
                        "bensz.research.hypothesis-merit@1.1.0",
                    ],
                },
            },
            {
                "type": "state.transition",
                "event_id": f"state-entry-{target}",
                "run_id": RUN_ID,
                "attempt_id": ATTEMPT_ID,
                "payload": {
                    "skill": "research-idea",
                    "from_state": PREFIX + source,
                    "to_state": PREFIX + target,
                },
            },
        ])
    with (task / "log/events.ndjson").open("a", encoding="utf-8") as handle:
        for event in events:
            handle.write(json.dumps(event) + "\n")
    write(task / "research-idea/log/meta-state.json", json.dumps({"current_state": PREFIX + "completed"}))


def write_evidence_index(task: Path) -> Path:
    dependency_paths = {
        "research-topic-extractor": ["research-topic-extractor/output/theme.json"],
        "research-literature-radar": ["research-literature-radar/output/selection.md"],
        "research-literature-interpretation": ["research-literature-interpretation/output/R1/interpretation.md"],
        "research-literature-search": ["research-literature-search/output/C1/manifest.json"],
    }
    for paths in dependency_paths.values():
        for path in paths:
            write(task / path, "fixture evidence")
    rounds = []
    for round_no in range(1, 4):
        reviewers = []
        for reviewer_no in range(1, 4):
            path = f"parallel-vibe/output/round{round_no}/reviewer{reviewer_no}.md"
            write(task / path, "review")
            reviewers.append({"id": f"r{round_no}-{reviewer_no}", "path": path})
        summary_path = f"parallel-vibe/output/round{round_no}/summary.md"
        write(task / summary_path, "summary")
        rounds.append({"round": round_no, "reviewers": reviewers, "summary_path": summary_path})
    write(task / "research-idea/output/review-synthesis.md", "synthesis")
    data = {
        "dependencies": {
            skill: [{"path": path, "status": "complete"} for path in paths]
            for skill, paths in dependency_paths.items()
        },
        "review": {
            "rounds": rounds,
            "synthesis_path": "research-idea/output/review-synthesis.md",
        },
    }
    index = task / "research-idea/output/completion-evidence.json"
    write(index, json.dumps(data))
    return index


def run_check(tmp_path: Path, task: Path, report: Path) -> dict:
    return check_completion.check_completion(tmp_path, task, report)


def test_recommended_report_without_completed_state_fails(tmp_path):
    task, report = make_workspace(tmp_path)
    result = run_check(tmp_path, task, report)
    assert not result["passed"]
    assert any("运行状态未到 completed" in error for error in result["errors"])
    assert any("事件日志缺少 reporting -> completed" in error for error in result["errors"])
    assert result["state"]["first_control_break"]["code"] == "legacy_state_identity"


def test_v14_style_gate_identity_mismatch_is_reported_as_first_break(tmp_path):
    task, report = make_workspace(tmp_path)
    with (task / "log/events.ndjson").open("a", encoding="utf-8") as handle:
        handle.write(json.dumps({
            "type": "verification.gate",
            "event_id": "gate-wrong-attempt",
            "run_id": RUN_ID,
            "attempt_id": "literature-2",
            "payload": {"decision": "allow"},
        }) + "\n")
    result = run_check(tmp_path, task, report)
    assert not result["passed"]
    assert result["state"]["first_control_break"]["code"] == "legacy_state_identity"
    assert any("legacy_state_identity" in error for error in result["errors"])


def test_custom_name_uses_manifest_allow_custom_name(tmp_path):
    task, report = make_workspace(tmp_path, custom_name=True)
    result = run_check(tmp_path, task, report)
    assert result["report"]["passed"], result["report"]
    assert result["report"]["completion_eligible"]


def test_missing_search_dependency_and_review_evidence_fails_even_when_state_completed(tmp_path):
    task, report = make_workspace(tmp_path, state=PREFIX + "completed")
    write_completion_events(task)
    write(task / "research-idea/output/completion-evidence.json", json.dumps({"dependencies": {}, "review": {"rounds": []}}))
    result = run_check(tmp_path, task, report)
    assert not result["passed"]
    assert any("research-literature-search" in error for error in result["errors"])
    assert any("第 1 轮" in error for error in result["errors"])


def test_legacy_complete_state_cannot_gain_new_completion_eligibility(tmp_path):
    task, report = make_workspace(tmp_path, state=PREFIX + "completed")
    write_completion_events(task)
    write_evidence_index(task)
    result = run_check(tmp_path, task, report)
    assert not result["passed"]
    assert result["state"]["first_control_break"]["code"] == "legacy_state_identity"


def test_unbound_completed_transition_is_explicitly_legacy_and_fails_closed(tmp_path):
    task = tmp_path / ".bensz-api/task-unbound"
    write(task / ".workspace.json", json.dumps({"protocol": "bensz-api-task-v1"}))
    source = {"run_id": RUN_ID, "state_visit_id": "visit-reporting", "attempt_id": ATTEMPT_ID}
    target = {"run_id": RUN_ID, "state_visit_id": "visit-completed", "attempt_id": "completed-a1"}
    log = EventLog(task / "log/events.ndjson")
    transition = log.append(
        "state.transition",
        scope="skill",
        run_id=RUN_ID,
        state_visit_id="visit-reporting",
        attempt_id=ATTEMPT_ID,
        payload={
            "skill": "research-idea",
            "from_state": PREFIX + "reporting",
            "to_state": PREFIX + "completed",
            "source_identity": source,
            "target_identity": target,
        },
    )
    binding = log.query_transition_bindings(skill="research-idea")[0]
    assert binding["transition_event_id"] == transition.event_id
    assert binding["status"] == "legacy_unbound"


def test_strict_review_requires_thread_and_runner_completion(tmp_path):
    reviewer_path = tmp_path / "parallel-vibe/output/reviewer.md"
    summary_path = tmp_path / "parallel-vibe/output/summary.md"
    synthesis_path = tmp_path / "research-idea/output/review-synthesis.md"
    for path in (reviewer_path, summary_path, synthesis_path):
        write(path, "review evidence")
    reviewer = {
        "id": "reviewer-1", "path": reviewer_path.relative_to(tmp_path).as_posix(),
        "thread_id": "thread-1", "model": "synthetic", "input_snapshot_hash": "sha256:input",
        "output_hash": check_completion.file_snapshot(reviewer_path)["sha256"],
        "started_at": "2026-09-13T00:00:00Z", "ended_at": "2026-09-13T00:01:00Z",
        "independent": True, "run_id": RUN_ID, "attempt_id": ATTEMPT_ID,
    }
    index = {
        "schema": "research-idea-completion-v4", "dependencies": {},
        "review": {
            "rounds": [{
                "round": 1, "reviewers": [reviewer],
                "summary_path": summary_path.relative_to(tmp_path).as_posix(),
            }],
            "synthesis_path": synthesis_path.relative_to(tmp_path).as_posix(),
            "synthesis": {}, "run_id": RUN_ID, "attempt_id": ATTEMPT_ID,
        },
    }
    errors: list[str] = []
    check_completion.check_dependency_index(
        index, tmp_path, {"settings": {"rounds": 1, "agents": 1}},
        {"execution_statuses": {"review": "complete"}}, errors,
        run_id=RUN_ID, attempt_id=None,
    )
    assert any("thread_status 未完成" in item for item in errors)
    assert any("runner_status 未完成" in item for item in errors)


def test_v5_novelty_requires_valid_search_bundle_metadata(tmp_path):
    manifest_path = tmp_path / "research-literature-search/output/C1/manifest.json"
    write(manifest_path, json.dumps({"contract_version": "rls.v1", "status": "success"}))
    item = {
        "path": manifest_path.relative_to(tmp_path).as_posix(),
        "status": "complete",
        "snapshot": check_completion.file_snapshot(manifest_path),
        "source_id": "search-C1",
        "contract_version": "rls.v1",
        "search_status": "success",
        "query_sha256": "sha256:queries",
        "canonical_candidates_sha256": "sha256:candidates",
        "canonical_count": 3,
        "canonical_coverage_complete": True,
    }
    index = {
        "schema": "research-idea-completion-v5",
        "dependencies": {"research-literature-search": [item]},
    }
    errors: list[str] = []
    check_completion.check_dependency_index(
        index,
        tmp_path,
        {},
        {"execution_statuses": {"exploration": "incomplete", "novelty": "complete", "review": "incomplete"}},
        errors,
    )
    assert errors == []

    item["canonical_coverage_complete"] = False
    errors = []
    check_completion.check_dependency_index(
        index,
        tmp_path,
        {},
        {"execution_statuses": {"exploration": "incomplete", "novelty": "complete", "review": "incomplete"}},
        errors,
    )
    assert any("全量消费" in error for error in errors)
