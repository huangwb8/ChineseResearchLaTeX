"""research-idea 结构与运行协议回归；合成回传不构成科研质量评估。"""
from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "skills/research-idea/scripts"
sys.path.insert(0, str(SCRIPTS))

import idea_runtime
import init_workspace
import phase_evidence
import validate_report


def candidate(heading="C1", *, bold=True):
    values = {
        "科学问题": "环境条件是否改变测量误差的方向？",
        "可证伪科学假设": "控制真实浓度后，湿度改变测量偏差。",
        "关键预测": "相同浓度下，湿度变化引起有方向的误差。",
        "反证路径": "在预设精度范围内无差异将推翻该解释。",
        "价值与非平凡性": "确定既有测量结论的适用边界。",
        "最近工作与实质增量": "最近研究只覆盖干燥条件，湿度效应尚未测量。",
        "最强替代方向": "先改进参照测量；若误差来自参照则改变优先级。",
        "判断可信度与近期投入": "当前有限证据支持小规模鉴别观察。",
        "脉络依据": "[O1](#opportunity-1)，[R1](#reference-1)",
        "查新结论": "部分研究但关键缺口存在；湿度边界缺乏验证。",
    }
    return f"### {heading}：测量边界\n\n" + "\n".join(
        f"**{key}**：{value}" if bold else f"{key}：{value}"
        for key, value in values.items()
    ) + "\n"


def report_text(outcome="recommended", *, novelty=None, body=None):
    novelty = novelty or ("incomplete" if outcome == "insufficient" else "complete")
    state = "incomplete" if outcome == "insufficient" else "complete"
    metadata = (
        "---\nreport_contract: research-idea-report-v2\n"
        f"outcome: {outcome}\nexploration: {state}\nnovelty: {novelty}\n"
        f"review: {state}\n---\n"
    )
    if body is None:
        body = candidate() if outcome == "recommended" else "当前没有可保留候选。\n"
    final_sections = {
        "recommended": "## 推荐与投入排序\n科学价值优先 C1；近期仅投入关键边界的观察。\n",
        "no_qualified": (
            "## 淘汰理由与重启条件\n**评估范围**：当前已读材料覆盖的问题。\n"
            "**淘汰依据**：已知答案足以解释当前现象。\n"
            "**重新探索**：以测量边界为新角度后仍无实质未知。\n"
            "**重启条件**：出现不能由现有解释覆盖的新证据。\n"
        ),
        "insufficient": (
            "## 证据缺口与恢复位置\n**关键缺口**：缺少最近论文全文。\n"
            "**恢复位置**：补齐全文后重新评估查新。\n"
        ),
    }
    return metadata + (
        "## 结论与研究目标\n评估测量边界是否构成有意义的研究问题。\n"
        '## 研究脉络 map 摘要\n<a id="opportunity-1"></a>O1：湿度适用边界。\n'
        '<a id="reference-1"></a>R1：合成测试证据，仅供协议测试。\n'
        f"## 候选评估\n{body}\n"
        "## 查新摘要\nPremium 是合成文本，不证明已执行真实查新。\n"
        + ("**免查新依据**：全部方向已由价值筛选证据淘汰。\n" if novelty == "not_required" else "")
        + "## 风险与下一步\n取得关键证据后重新判断边界。\n"
        + final_sections[outcome]
    )


def write_report(root, text):
    path = root / "docs/ideas/Research-Idea_fixture_manual_20260910.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def validate(root, text):
    return validate_report.validate_report(write_report(root, text), project_root=root)


@pytest.mark.parametrize("heading", ["候选 1", "候选1", "候选 C1", "C1"])
def test_candidate_heading_compatibility(heading):
    text = "## 多个科学问题-科学假设对\n" + candidate(heading)
    assert [item[0] for item in validate_report.candidate_blocks(text)] == ["C1"]


def test_legacy_report_readable_but_never_completion_eligible(tmp_path):
    config = init_workspace.load_config()
    blocks = "\n".join(candidate(f"候选 {i}") for i in range(1, 4))
    sections = {name: "历史说明" for name in config["output"]["required_sections"]}
    sections["多个科学问题-科学假设对"] = blocks
    sections["最佳科学问题-科学假设对"] = "；".join(config["validation"]["required_best_markers"])
    sections["查新摘要"] = "Premium；部分研究但关键缺口存在"
    result = validate(tmp_path, "\n".join(f"## {name}\n{body}" for name, body in sections.items()))
    assert result["passed"], result
    assert result["outcome"] == "legacy"
    assert not result["completion_eligible"]


@pytest.mark.parametrize("outcome,count,eligible", [("recommended", 1, True), ("no_qualified", 0, True), ("insufficient", 0, False)])
def test_three_report_outcomes(tmp_path, outcome, count, eligible):
    result = validate(tmp_path, report_text(outcome))
    assert result["passed"], result
    assert result["pair_count"] == count
    assert result["completion_eligible"] is eligible


@pytest.mark.parametrize("bold", [True, False])
def test_empty_candidate_field_is_rejected(tmp_path, bold):
    body = candidate(bold=bold).replace("环境条件是否改变测量误差的方向？", "")
    result = validate(tmp_path, report_text(body=body))
    assert not result["passed"], "空科学问题不能借用下一字段内容"
    assert any("科学问题" in error for error in result["errors"])


@pytest.mark.parametrize("body", ["### C1\n", candidate() + candidate(), "当前没有候选。"])
def test_empty_duplicate_or_missing_candidate_rejected(tmp_path, body):
    assert not validate(tmp_path, report_text(body=body))["passed"]


def test_unresolvable_candidate_reference_rejected(tmp_path):
    text = report_text().replace('<a id="reference-1"></a>', "")
    result = validate(tmp_path, text)
    assert not result["passed"]
    assert any("引用不可定位" in error for error in result["errors"])


def test_premium_text_cannot_replace_completed_novelty(tmp_path):
    result = validate(tmp_path, report_text(novelty="incomplete"))
    assert not result["passed"]
    assert not result["completion_eligible"]


def test_no_qualified_requires_scope_and_reexploration(tmp_path):
    text = report_text("no_qualified").replace("**重新探索**：以测量边界为新角度后仍无实质未知。\n", "")
    assert not validate(tmp_path, text)["passed"]


def test_no_qualified_can_explain_no_novelty_needed(tmp_path):
    assert validate(tmp_path, report_text("no_qualified", novelty="not_required"))["passed"]


def evidence(root, roles, prefix="fixture"):
    rows = []
    for index, role in enumerate(roles):
        ref = f"{prefix}-{index}"
        relative = f"evidence/{ref}.md"
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"合成协议证据：{ref}，角色 {role}；非真实科研评估。", encoding="utf-8")
        rows.append({"ref": ref, "role": role, "path": relative, "source_type": "synthetic-test", "summary": "仅验证确定性协议边界"})
    return rows


@pytest.fixture
def runtime(tmp_path):
    run = idea_runtime.Runtime(tmp_path, ".bensz-api/task-fixture")
    run.init(rounds=1, agents=1)
    return run


def synthetic_submission(prepared):
    from bensz_skill_kernel.contract_packs import COMPONENT_RESULT_PROTOCOL

    handoff = prepared["handoffs"][0]
    keys = ("pack_id", "pack_version", "package_kind", "component_id", "component_type", "contract_hash", "component_hash", "plan_hash", "run_id", "attempt_id", "handoff_hash")
    return {
        **{key: handoff[key] for key in keys},
        "protocol": COMPONENT_RESULT_PROTOCOL,
        "execution_status": "completed", "verdict": "pass", "findings": [],
        "facts": {"summary": "合成 pass，仅验证运行协议；不证明科研充分性。", "confidence": 0.5, "uncertainties": []},
        "evidence_refs": handoff["evidence_refs"],
        "executor": {"type": "agent", "id": "synthetic-fixture", "model": "synthetic-test-only"},
    }


def prepare_candidates(runtime):
    rows = evidence(runtime.project, ["theme", "radar", "interpretation", "map"])
    prepared = runtime.prepare("candidates", rows)
    assert prepared["gate"] != "allow", "无语义回传不能前进"
    assert len(prepared["handoffs"]) == 1
    return rows, prepared


def test_runtime_settings_and_resume(runtime):
    assert runtime.status()["settings"] == {"rounds": 1, "agents": 1, "allow_custom_name": False}
    resumed = idea_runtime.Runtime(runtime.project, ".bensz-api/task-fixture")
    assert resumed.status() == runtime.status()
    with pytest.raises(ValueError, match="运行已存在"):
        resumed.init()


@pytest.mark.parametrize("field", ["run_id", "attempt_id", "contract_hash", "plan_hash", "component_hash", "handoff_hash"])
def test_bound_result_mismatch_never_advances(runtime, field):
    _, prepared = prepare_candidates(runtime)
    submission = synthetic_submission(prepared)
    submission[field] = "wrong-binding"
    try:
        result = runtime.submit(submission)
    except ValueError:
        pass
    else:
        assert result["gate"] != "allow"
    assert runtime.status()["state"].endswith(".literature")


def test_stale_attempt_cannot_advance_new_attempt(runtime):
    rows, old = prepare_candidates(runtime)
    new = runtime.prepare("candidates", rows)
    assert new["attempt_id"] != old["attempt_id"]
    try:
        result = runtime.submit(synthetic_submission(old))
    except ValueError:
        pass
    else:
        assert result["gate"] != "allow"
    assert runtime.status()["state"].endswith(".literature")


def test_changed_evidence_requires_new_attempt(runtime):
    rows, prepared = prepare_candidates(runtime)
    (runtime.project / rows[0]["path"]).write_text("已变更的证据", encoding="utf-8")
    with pytest.raises(ValueError, match="内容已变化"):
        runtime.submit(synthetic_submission(prepared))
    assert runtime.status()["state"].endswith(".literature")


def test_missing_evidence_role_blocks_even_with_semantic_pass(runtime):
    prepared = runtime.prepare("candidates", evidence(runtime.project, ["theme", "radar", "map"]))
    assert prepared["gate"] != "allow"
    if prepared["handoffs"]:
        assert runtime.submit(synthetic_submission(prepared))["gate"] != "allow"
    assert runtime.status()["state"].endswith(".literature")


def test_rework_invalidates_checkpoint_and_resume(runtime):
    rows, prepared = prepare_candidates(runtime)
    result = runtime.submit(synthetic_submission(prepared))
    assert result["gate"] == "allow", result
    assert runtime.status()["checkpoints"]
    result = runtime.rework("literature", evidence(runtime.project, ["rework"], "reason"))
    assert result["state"].endswith(".literature")
    assert not result["checkpoints"]
    assert result["pending"] is None
    resumed = idea_runtime.Runtime(runtime.project, ".bensz-api/task-fixture")
    assert resumed.status() == runtime.status()
    (runtime.project / rows[0]["path"]).write_text("修复后的证据", encoding="utf-8")
    assert resumed.prepare("candidates", rows)["handoffs"]


def test_cancel_is_terminal(runtime):
    prepare_candidates(runtime)
    assert runtime.cancel()["cancelled"]
    assert runtime.status()["pending"] is None
    with pytest.raises(ValueError, match="终止"):
        runtime.prepare("candidates", evidence(runtime.project, ["theme"]))


def test_insufficient_report_is_rejected_by_completion_stage(tmp_path):
    path = write_report(tmp_path, report_text("insufficient"))
    request = {
        "subject": {"target": "bensz.research-ideation.completed"},
        "context": {"project_root": str(tmp_path), "allow_custom_name": False},
        "evidence": [{"ref": "report", "role": "report", "path": str(path.relative_to(tmp_path)), "source_type": "synthetic-test", "summary": "结构合格的阶段性报告"}],
    }
    result = phase_evidence.check(request)
    assert result["verdict"] == "fail"
    assert any(item["code"] == "incomplete-report" for item in result["findings"])


@pytest.mark.parametrize("value", ["../escape", "/absolute", "evidence/../escape", "evidence\\escape"])
def test_unsafe_evidence_paths_rejected(tmp_path, value):
    with pytest.raises(ValueError):
        phase_evidence.safe_path(tmp_path, value)


def test_initializer_persists_requested_settings(tmp_path):
    result = subprocess.run(
        [sys.executable, str(SCRIPTS / "init_workspace.py"), "--cwd", str(tmp_path), "--task-root", ".bensz-api/task-fixture", "--input-label", "fixture", "--repo-name", "fixture", "--pr-name", "manual", "--skip-dependency-check", "--rounds", "2", "--agents", "1"],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    run = idea_runtime.Runtime(tmp_path, ".bensz-api/task-fixture")
    assert run.status()["settings"]["rounds"] == 2
    assert run.status()["settings"]["agents"] == 1
    assert not (tmp_path / "tests/research-idea").exists()
    schema = json.loads((run.root / "candidates/candidate-schema.json").read_text(encoding="utf-8"))
    assert schema["outcome"] == "insufficient"
    assert schema["candidates"] == []
    assert all(schema[key] == "incomplete" for key in ("exploration", "novelty", "review"))
    assert schema["candidate_example"][0]["novelty_status"] == "未定"


def test_runtime_defaults_come_from_config(tmp_path):
    run = idea_runtime.Runtime(tmp_path, ".bensz-api/task-defaults")
    settings = run.init()["settings"]
    config = init_workspace.load_config()
    assert settings["rounds"] == config["iteration"]["default_rounds"]
    assert settings["agents"] == config["iteration"]["default_independent_agents"]


@pytest.mark.parametrize("outcome,eligible", [("recommended", True), ("no_qualified", True), ("insufficient", False)])
def test_all_stages_preserve_report_completion_boundary(runtime, outcome, eligible):
    _, prepared = prepare_candidates(runtime)
    assert runtime.submit(synthetic_submission(prepared))["gate"] == "allow"
    rows = evidence(runtime.project, ["candidates", "novelty"], "candidate-stage")
    prepared = runtime.prepare("review", rows)
    assert runtime.submit(synthetic_submission(prepared))["gate"] == "allow"
    rows = evidence(runtime.project, ["review", "synthesis"], "review-stage")
    rows[0].update(round=1, reviewer="synthetic-reviewer")
    prepared = runtime.prepare("reporting", rows)
    assert runtime.submit(synthetic_submission(prepared))["gate"] == "allow"
    path = write_report(runtime.project, report_text(outcome))
    rows = [{"ref": "report", "role": "report", "path": str(path.relative_to(runtime.project)), "source_type": "synthetic-test", "summary": "合成报告结构与结论测试"}]
    prepared = runtime.prepare("completed", rows)
    assert prepared["gate"] != "allow", "仅报告格式通过不能认证完成"
    result = runtime.submit(synthetic_submission(prepared))
    assert (result["gate"] == "allow") is eligible
    assert result["state"].endswith(".completed" if eligible else ".reporting")


def test_completed_checkpoint_change_blocks_next_stage(runtime):
    rows, prepared = prepare_candidates(runtime)
    assert runtime.submit(synthetic_submission(prepared))["gate"] == "allow"
    (runtime.project / rows[0]["path"]).write_text("已通过阶段的证据后来被改动", encoding="utf-8")
    with pytest.raises(ValueError, match="内容已变化"):
        runtime.prepare("review", evidence(runtime.project, ["candidates", "novelty"], "next"))


@pytest.mark.parametrize("kind", ["duplicate-content", "missing-round", "missing-reviewer"])
def test_review_requires_distinct_results_for_all_promised_rounds(tmp_path, kind):
    rows = evidence(tmp_path, ["review", "review", "synthesis"])
    rows[0].update(round=1, reviewer="first")
    rows[1].update(round=1, reviewer="second")
    if kind == "duplicate-content":
        (tmp_path / rows[1]["path"]).write_bytes((tmp_path / rows[0]["path"]).read_bytes())
    elif kind == "missing-round":
        rows[1]["round"] = 2
    else:
        rows[1].pop("reviewer")
    request = {"subject": {"target": "bensz.research-ideation.reporting"}, "context": {"project_root": str(tmp_path), "rounds": 1, "agents": 2}, "evidence": rows}
    assert phase_evidence.check(request)["verdict"] == "fail"


def test_rework_cannot_bypass_forward_gate(runtime):
    with pytest.raises(ValueError, match="前向 Gate"):
        runtime.rework("candidates", evidence(runtime.project, ["rework"]))


def test_missing_submission_refs_rejected(runtime):
    _, prepared = prepare_candidates(runtime)
    submission = synthetic_submission(prepared)
    submission["evidence_refs"] = []
    with pytest.raises(ValueError, match="引用实际证据"):
        runtime.submit(submission)


@pytest.mark.parametrize("outcome,wrong_section", [
    ("recommended", "淘汰理由与重启条件"),
    ("recommended", "证据缺口与恢复位置"),
    ("no_qualified", "推荐与投入排序"),
    ("no_qualified", "证据缺口与恢复位置"),
    ("insufficient", "推荐与投入排序"),
    ("insufficient", "淘汰理由与重启条件"),
])
def test_outcome_rejects_other_outcome_sections(tmp_path, outcome, wrong_section):
    result = validate(tmp_path, report_text(outcome) + f"\n## {wrong_section}\n与声明结论冲突。\n")
    assert not result["passed"]
    assert any("业务结论冲突" in error for error in result["errors"])


def test_plain_cli_shows_outcome_and_completion_eligibility(tmp_path):
    path = write_report(tmp_path, report_text("insufficient"))
    result = subprocess.run([sys.executable, str(SCRIPTS / "validate_report.py"), "--report", str(path)], capture_output=True, text=True)
    # CLI 对测试工作区路径的限制仍生效；这里只验证无需 JSON 即可看到结论边界。
    assert "outcome=insufficient\n" in result.stdout
    assert "completion_eligible=false\n" in result.stdout
    assert "Traceback" not in result.stderr


@pytest.mark.parametrize("metadata", [
    "report_contract: research-idea-report-v2\noutcome: unknown",
    "report_contract: research-idea-report-v2",
    "report_contract: research-idea-report-v2\noutcome: [recommended]",
    "report_contract: research-idea-report-v2\noutcome: {name: recommended}",
    "report_contract: research-idea-report-v2\noutcome: true",
    "[recommended, complete]",
    "null",
    "report_contract: [",
])
def test_invalid_frontmatter_fails_cleanly(tmp_path, metadata):
    body = report_text().split("---\n", 2)[2]
    result = validate(tmp_path, f"---\n{metadata}\n---\n{body}")
    assert not result["passed"]
    assert not result["completion_eligible"]


def test_missing_frontmatter_fails_cleanly(tmp_path):
    result = validate(tmp_path, report_text().split("---\n", 2)[2])
    assert not result["passed"]
    assert not result["completion_eligible"]


@pytest.mark.parametrize("placeholder", ["TODO", "TBD", "待填", "待补充", "同上", "{待填写科学问题}", "…"])
def test_placeholder_candidate_field_rejected(tmp_path, placeholder):
    text = report_text().replace("环境条件是否改变测量误差的方向？", placeholder)
    assert not validate(tmp_path, text)["passed"]


@pytest.mark.parametrize("original,replacement", [("[O1](#opportunity-1)", "[O9](#opportunity-1)"), ("[R1](#reference-1)", "[R9](#reference-1)")])
def test_reference_label_must_match_declared_target(tmp_path, original, replacement):
    result = validate(tmp_path, report_text().replace(original, replacement))
    assert not result["passed"], "引用编号不能借用不同编号的已存在锚点"


def test_report_inside_code_fence_is_not_a_report(tmp_path):
    result = validate(tmp_path, "```markdown\n" + report_text() + "```\n")
    assert not result["passed"]
    assert not result["completion_eligible"]


def test_copied_skill_initializer_and_pack_registry_are_relocatable(tmp_path):
    copied = tmp_path / "portable-skills/research-idea"
    shutil.copytree(SCRIPTS.parent, copied, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    project = tmp_path / "portable-project"
    project.mkdir()
    result = subprocess.run([
        sys.executable, str(copied / "scripts/init_workspace.py"), "--cwd", str(project),
        "--task-root", ".bensz-api/task-portable", "--input-label", "portable", "--skip-dependency-check",
        "--repo-name", "fixture", "--pr-name", "manual", "--rounds", "1", "--agents", "1",
    ], capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
    rows = evidence(project, ["theme", "radar", "interpretation", "map"])
    (project / "evidence.json").write_text(json.dumps(rows), encoding="utf-8")
    command = [sys.executable, str(copied / "scripts/idea_runtime.py"), "--project-root", str(project), "--task-root", ".bensz-api/task-portable"]
    prepared = subprocess.run([*command, "prepare", "--target", "candidates", "--evidence", "evidence.json"], capture_output=True, text=True)
    assert prepared.returncode == 2, prepared.stdout + prepared.stderr
    payload = json.loads(prepared.stdout)
    assert len(payload["handoffs"]) == 1
    submission = synthetic_submission(payload)
    (project / "submission.json").write_text(json.dumps(submission), encoding="utf-8")
    submitted = subprocess.run([*command, "submit", "--result", "submission.json"], capture_output=True, text=True)
    assert submitted.returncode == 0, submitted.stdout + submitted.stderr
    assert json.loads(submitted.stdout)["state"].endswith(".candidates")
