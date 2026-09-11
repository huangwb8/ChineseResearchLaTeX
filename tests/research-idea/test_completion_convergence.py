"""research-idea 完成证据收敛检查回归。"""
from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "skills/research-idea/scripts"
sys.path.insert(0, str(SCRIPTS))

import check_completion


PREFIX = "bensz.research-ideation."


def write(path: Path, text: str = "fixture") -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path.as_posix()


def report_text() -> str:
    return """---
report_contract: research-idea-report-v2
outcome: recommended
exploration: complete
novelty: complete
review: complete
---
# 测试研究方向

## 结论与研究目标
评估测量边界是否构成有意义的研究问题。

## 研究脉络 map 摘要
<a id="opportunity-1"></a>O1：湿度适用边界。
<a id="reference-1"></a>R1：合成测试证据，仅供协议测试。

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
**脉络依据**：[O1](#opportunity-1)，[R1](#reference-1)
**查新结论**：部分研究但关键缺口存在；湿度边界缺乏验证。

## 查新摘要
Premium 是合成文本，不证明已执行真实查新。

## 风险与下一步
取得关键证据后重新判断边界。

## 推荐与投入排序
科学价值优先 C1；近期仅投入关键边界的观察。
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
                "attempt_id": "default",
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
    events = [
        {
            "type": "verification.result",
            "run_id": "run-1",
            "attempt_id": "reporting-1",
            "payload": {
                "verifier_id": "bensz.research.stage-readiness",
                "verifier_version": "3.0.0",
                "execution_status": "completed",
                "verdict": "pass",
            },
        },
        {
            "type": "verification.result",
            "run_id": "run-1",
            "attempt_id": "reporting-1",
            "payload": {
                "verifier_id": "bensz.research.hypothesis-merit",
                "verifier_version": "1.0.0",
                "execution_status": "completed",
                "verdict": "pass",
            },
        },
        {
            "type": "verification.gate",
            "run_id": "run-1",
            "attempt_id": "reporting-1",
            "payload": {
                "decision": "allow",
                "computed_by": "kernel",
                "result_refs": [
                    "bensz.research.stage-readiness@3.0.0",
                    "bensz.research.hypothesis-merit@1.0.0",
                ],
            },
        },
        {
            "type": "state.transition",
            "run_id": "run-1",
            "attempt_id": "reporting-1",
            "payload": {
                "skill": "research-idea",
                "from_state": PREFIX + "reporting",
                "to_state": PREFIX + "completed",
            },
        },
    ]
    with (task / "log/events.ndjson").open("a", encoding="utf-8") as handle:
        for event in events:
            handle.write(json.dumps(event) + "\n")
    write(task / "research-idea/log/meta-state.json", json.dumps({"current_state": PREFIX + "completed"}))


def write_evidence_index(task: Path) -> Path:
    dependency_paths = {
        "research-topic-extractor": ["research-topic-extractor/output/theme.json"],
        "research-literature-radar": ["research-literature-radar/output/selection.md"],
        "research-literature-interpretation": ["research-literature-interpretation/output/R1/interpretation.md"],
        "research-literature-review": ["research-literature-review/output/C1/novelty-result.md"],
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


def test_custom_name_uses_manifest_allow_custom_name(tmp_path):
    task, report = make_workspace(tmp_path, custom_name=True)
    result = run_check(tmp_path, task, report)
    assert result["report"]["passed"], result["report"]
    assert result["report"]["completion_eligible"]


def test_missing_dependency_and_review_evidence_fails_even_when_state_completed(tmp_path):
    task, report = make_workspace(tmp_path, state=PREFIX + "completed")
    write_completion_events(task)
    write(task / "research-idea/output/completion-evidence.json", json.dumps({"dependencies": {}, "review": {"rounds": []}}))
    result = run_check(tmp_path, task, report)
    assert not result["passed"]
    assert any("research-literature-review" in error for error in result["errors"])
    assert any("第 1 轮" in error for error in result["errors"])


def test_complete_state_gate_dependency_and_review_evidence_pass(tmp_path):
    task, report = make_workspace(tmp_path, state=PREFIX + "completed")
    write_completion_events(task)
    write_evidence_index(task)
    result = run_check(tmp_path, task, report)
    assert result["passed"], result["errors"]
