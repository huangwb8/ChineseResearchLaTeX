#!/usr/bin/env python3
from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml


def _read_text(p: Path) -> str:
    return p.read_text(encoding="utf-8")


def _parse_frontmatter(md_text: str) -> dict:
    if not md_text.startswith("---\n"):
        raise ValueError("SKILL.md must start with YAML frontmatter ('---')")
    m = re.match(r"\A---\n(.*?)\n---\n", md_text, flags=re.DOTALL)
    if not m:
        raise ValueError("SKILL.md YAML frontmatter must be closed by a second '---' line")
    return yaml.safe_load(m.group(1)) or {}


def main() -> int:
    # scripts/*.py -> skill root
    skill_root = Path(__file__).resolve().parents[1]
    config_path = skill_root / "config.yaml"
    skill_md_path = skill_root / "SKILL.md"
    readme_path = skill_root / "README.md"

    errors: list[str] = []

    if not config_path.exists():
        errors.append(f"Missing {config_path}")
        return _finish(errors)
    if not skill_md_path.exists():
        errors.append(f"Missing {skill_md_path}")
        return _finish(errors)

    cfg = yaml.safe_load(_read_text(config_path)) or {}
    cfg_skill = (cfg.get("skill_info") or {}) if isinstance(cfg, dict) else {}
    cfg_name = cfg_skill.get("name")
    cfg_ver = cfg_skill.get("version")

    if cfg_name != "nsfc-reviewers":
        errors.append(f"config.yaml: skill_info.name expected 'nsfc-reviewers', got {cfg_name!r}")
    if not cfg_ver:
        errors.append("config.yaml: missing skill_info.version")

    _validate_skill_info(cfg, errors)

    skill_md_text = _read_text(skill_md_path)
    fm = _parse_frontmatter(skill_md_text)
    fm_name = fm.get("name")
    if fm_name != cfg_name:
        errors.append(
            f"SKILL.md frontmatter: name {fm_name!r} does not match config.yaml skill_info.name {cfg_name!r}"
        )

    kw = ((fm.get("metadata") or {}).get("keywords") or []) if isinstance(fm, dict) else []
    if not isinstance(kw, list):
        errors.append("SKILL.md frontmatter: metadata.keywords must be a list")
    else:
        if not (3 <= len(kw) <= 5):
            errors.append(f"SKILL.md frontmatter: metadata.keywords should be 3-5 items, got {len(kw)}")

    # Generality checks for user-facing docs
    for p in [skill_md_path, readme_path]:
        if not p.exists():
            continue
        t = _read_text(p)
        if "/Users/" in t:
            errors.append(f"{p.name}: contains a personal path '/Users/'")
        if re.search(r"\b20\d{2}-\d{2}-\d{2}\b", t):
            errors.append(f"{p.name}: contains a concrete date (use placeholders like YYYY-MM-DD in examples)")

    # SKILL.md length guardrail
    skill_lines = skill_md_text.count("\n") + 1
    if skill_lines > 500:
        errors.append(f"SKILL.md too long: {skill_lines} lines (> 500)")

    # Version should not be hardcoded in SKILL/README
    if cfg_ver:
        for p in [skill_md_path, readme_path]:
            if p.exists() and str(cfg_ver) in _read_text(p):
                errors.append(f"{p.name}: hardcodes version {cfg_ver} (should only live in config.yaml)")

    _validate_output_settings(cfg, errors)
    _validate_stage_assessment(cfg, errors)
    _validate_funding_context(cfg, errors)
    _validate_parallel_review(cfg, skill_root, errors)
    _validate_scripts(skill_root, errors)
    _validate_references(skill_root, errors)
    _validate_docs_consistency(cfg, skill_md_text, _read_text(readme_path) if readme_path.exists() else "", errors)

    return _finish(errors)


def _validate_skill_info(cfg: dict, errors: list[str]) -> None:
    skill = cfg.get("skill_info") if isinstance(cfg, dict) else None
    if not isinstance(skill, dict):
        errors.append("config.yaml: missing skill_info (dict)")
        return

    category = str(skill.get("category") or "").strip()
    if category not in {"writing", "development", "normal"}:
        errors.append("config.yaml: skill_info.category must be one of writing|development|normal")

    description = str(skill.get("description") or "")
    if not description:
        errors.append("config.yaml: skill_info.description is empty")


def _validate_parallel_review(cfg: dict, skill_root: Path, errors: list[str]) -> None:
    pr = cfg.get("parallel_review") if isinstance(cfg, dict) else None
    if not isinstance(pr, dict):
        errors.append("config.yaml: missing parallel_review (dict)")
        return

    for k in ["default_panel_count", "max_panel_count", "panel_output_filename", "runner", "runner_profile", "timeout_seconds"]:
        if k not in pr:
            errors.append(f"config.yaml: parallel_review missing {k}")

    default_panel_count = pr.get("default_panel_count")
    max_panel_count = pr.get("max_panel_count")
    if not isinstance(default_panel_count, int) or default_panel_count < 1:
        errors.append("config.yaml: parallel_review.default_panel_count must be an integer >= 1")
    if not isinstance(max_panel_count, int) or max_panel_count < 1:
        errors.append("config.yaml: parallel_review.max_panel_count must be an integer >= 1")
    if isinstance(default_panel_count, int) and isinstance(max_panel_count, int) and default_panel_count > max_panel_count:
        errors.append("config.yaml: parallel_review.default_panel_count must be <= max_panel_count")

    if "default_reviewer_count" in pr or "max_reviewer_count" in pr or "thread_output_filename" in pr:
        errors.append("config.yaml: parallel_review still contains old reviewer_count/thread_output_filename fields")

    rp = str(pr.get("runner_profile") or "").strip().lower()
    if rp and rp not in {"default", "fast", "deep"}:
        errors.append("config.yaml: parallel_review.runner_profile must be one of default|fast|deep")

    agg = pr.get("aggregation")
    if not isinstance(agg, dict):
        errors.append("config.yaml: parallel_review.aggregation missing (dict)")
    else:
        ct = agg.get("consensus_threshold")
        if not isinstance(ct, (int, float)) or not (0.0 < float(ct) <= 1.0):
            errors.append("config.yaml: parallel_review.aggregation.consensus_threshold must be in (0, 1]")

    personas = pr.get("reviewer_personas")
    if not isinstance(personas, list) or len(personas) != 7:
        errors.append("config.yaml: parallel_review.reviewer_personas must be a list of 7 personas")
        return

    for i, persona in enumerate(personas):
        if not isinstance(persona, dict):
            errors.append(f"config.yaml: reviewer_personas[{i}] must be a dict")
            continue
        if "style" in persona:
            errors.append(f"config.yaml: reviewer_personas[{i}] must not contain inline prompt field 'style'")
        pf = persona.get("prompt_file")
        if not pf or not isinstance(pf, str):
            errors.append(f"config.yaml: reviewer_personas[{i}] missing prompt_file")
            continue
        p = (skill_root / pf).resolve()
        try:
            p.relative_to(skill_root.resolve())
        except Exception:
            errors.append(f"config.yaml: reviewer_personas[{i}].prompt_file points outside skill root: {pf!r}")
            continue
        if not p.exists():
            errors.append(f"config.yaml: reviewer_personas[{i}].prompt_file not found: {pf!r}")


def _validate_output_settings(cfg: dict, errors: list[str]) -> None:
    os_cfg = cfg.get("output_settings") if isinstance(cfg, dict) else None
    if not isinstance(os_cfg, dict):
        errors.append("config.yaml: missing output_settings (dict)")
        return

    for k in ["default_filename", "panel_dir", "hide_intermediate", "intermediate_dir"]:
        if k not in os_cfg:
            errors.append(f"config.yaml: output_settings missing {k}")
    if not str(os_cfg.get("default_filename") or "").strip():
        errors.append("config.yaml: output_settings.default_filename is empty")
    panel_dir = str(os_cfg.get("panel_dir") or "").strip()
    if not panel_dir:
        errors.append("config.yaml: output_settings.panel_dir is empty")
    intermediate_dir = str(os_cfg.get("intermediate_dir") or "").strip()
    if not intermediate_dir:
        errors.append("config.yaml: output_settings.intermediate_dir is empty")

    # Keep these as simple directory names to avoid path surprises.
    for label, val in [("panel_dir", panel_dir), ("intermediate_dir", intermediate_dir)]:
        if not val:
            continue
        if Path(val).is_absolute():
            errors.append(f"config.yaml: output_settings.{label} must be a relative name, got an absolute path: {val!r}")
            continue
        if ".." in Path(val).parts:
            errors.append(f"config.yaml: output_settings.{label} must not contain '..': {val!r}")
            continue
        if len(Path(val).parts) != 1:
            errors.append(f"config.yaml: output_settings.{label} should be a single directory name (no slashes): {val!r}")

    # Optional-but-recommended validation knobs for deterministic output finalization.
    if "enforce_output_finalization" in os_cfg and not isinstance(os_cfg.get("enforce_output_finalization"), bool):
        errors.append("config.yaml: output_settings.enforce_output_finalization must be a bool")
    if "warn_missing_intermediate" in os_cfg and not isinstance(os_cfg.get("warn_missing_intermediate"), bool):
        errors.append("config.yaml: output_settings.warn_missing_intermediate must be a bool")
    if "validation_level" in os_cfg:
        vl = str(os_cfg.get("validation_level") or "").strip().lower()
        if vl and vl not in {"warn", "error"}:
            errors.append("config.yaml: output_settings.validation_level must be warn|error")


def _validate_stage_assessment(cfg: dict, errors: list[str]) -> None:
    sa = cfg.get("stage_assessment") if isinstance(cfg, dict) else None
    if not isinstance(sa, dict):
        errors.append("config.yaml: missing stage_assessment (dict)")
        return

    for k in ["enabled", "include_in_report", "judge_current_draft_only", "require_binary_verdict", "confidence_levels", "stages"]:
        if k not in sa:
            errors.append(f"config.yaml: stage_assessment missing {k}")

    for k in ["enabled", "include_in_report", "judge_current_draft_only", "require_binary_verdict"]:
        if k in sa and not isinstance(sa.get(k), bool):
            errors.append(f"config.yaml: stage_assessment.{k} must be a bool")

    cls = sa.get("confidence_levels")
    if not isinstance(cls, list) or [str(x) for x in cls] != ["高", "中", "低"]:
        errors.append("config.yaml: stage_assessment.confidence_levels must be ['高', '中', '低']")

    stages = sa.get("stages")
    if not isinstance(stages, dict):
        errors.append("config.yaml: stage_assessment.stages must be a dict")
        return

    for stage_id in ["letter_review", "panel_review"]:
        stage = stages.get(stage_id)
        if not isinstance(stage, dict):
            errors.append(f"config.yaml: stage_assessment.stages.{stage_id} must be a dict")
            continue
        for k in ["name", "pass_label", "fail_label", "key_checks"]:
            if k not in stage:
                errors.append(f"config.yaml: stage_assessment.stages.{stage_id} missing {k}")
        if stage.get("pass_label") != "给过" or stage.get("fail_label") != "不给过":
            errors.append(f"config.yaml: stage_assessment.stages.{stage_id} must use pass_label=给过 and fail_label=不给过")
        kc = stage.get("key_checks")
        if not isinstance(kc, list) or len(kc) < 2:
            errors.append(f"config.yaml: stage_assessment.stages.{stage_id}.key_checks must be a list with at least 2 items")


def _validate_funding_context(cfg: dict, errors: list[str]) -> None:
    fc = cfg.get("funding_context") if isinstance(cfg, dict) else None
    if not isinstance(fc, dict):
        errors.append("config.yaml: missing funding_context (dict)")
        return

    for k in ["enabled", "require_contextualized_judgement", "unknown_policy", "project_types", "report_requirements"]:
        if k not in fc:
            errors.append(f"config.yaml: funding_context missing {k}")

    for k in ["enabled", "require_contextualized_judgement"]:
        if k in fc and not isinstance(fc.get(k), bool):
            errors.append(f"config.yaml: funding_context.{k} must be a bool")

    unknown_policy = str(fc.get("unknown_policy") or "").strip().lower()
    if unknown_policy and unknown_policy not in {"conservative"}:
        errors.append("config.yaml: funding_context.unknown_policy must be conservative")

    project_types = fc.get("project_types")
    if not isinstance(project_types, dict):
        errors.append("config.yaml: funding_context.project_types must be a dict")
        return

    for project_type in ["youth", "general"]:
        item = project_types.get(project_type)
        if not isinstance(item, dict):
            errors.append(f"config.yaml: funding_context.project_types.{project_type} must be a dict")
            continue
        labels = item.get("labels")
        budget_range = item.get("typical_budget_wan_range")
        interpretation = str(item.get("interpretation") or "").strip()
        if not isinstance(labels, list) or not labels:
            errors.append(f"config.yaml: funding_context.project_types.{project_type}.labels must be a non-empty list")
        if not isinstance(budget_range, list) or len(budget_range) != 2:
            errors.append(
                f"config.yaml: funding_context.project_types.{project_type}.typical_budget_wan_range must be a 2-item list"
            )
        elif not all(isinstance(x, (int, float)) for x in budget_range) or float(budget_range[0]) > float(budget_range[1]):
            errors.append(
                f"config.yaml: funding_context.project_types.{project_type}.typical_budget_wan_range must be ascending numbers"
            )
        if not interpretation:
            errors.append(f"config.yaml: funding_context.project_types.{project_type}.interpretation is empty")

    report_requirements = fc.get("report_requirements")
    if not isinstance(report_requirements, list) or len(report_requirements) < 3:
        errors.append("config.yaml: funding_context.report_requirements must be a list with at least 3 items")


def _validate_scripts(skill_root: Path, errors: list[str]) -> None:
    required = [
        "scripts/build_parallel_vibe_plan.py",
        "scripts/cleanup_intermediate.py",
        "scripts/finalize_output.py",
        "scripts/list_proposal_files.py",
        "scripts/validate_skill.py",
    ]
    for rel in required:
        if not (skill_root / rel).exists():
            errors.append(f"Missing {rel}")


def _validate_references(skill_root: Path, errors: list[str]) -> None:
    refs = skill_root / "references"
    required = [
        "expert_01_innovation.md",
        "expert_02_methodology.md",
        "expert_03_foundation.md",
        "expert_04_critical.md",
        "expert_05_constructive.md",
        "expert_06_significance.md",
        "expert_07_clarity.md",
        "master_prompt_template.md",
        "aggregation_rules.md",
    ]
    if not refs.exists():
        errors.append("Missing references/ directory")
        return
    for f in required:
        p = refs / f
        if not p.exists():
            errors.append(f"Missing references/{f}")

    # Ensure master prompt template can stay consistent with config.yaml.
    tmpl = refs / "master_prompt_template.md"
    if tmpl.exists():
        t = _read_text(tmpl)
        if "{panel_output_filename}" not in t:
            errors.append("references/master_prompt_template.md: missing placeholder {panel_output_filename}")


def _extract_doc_number(text: str, pattern: str) -> int | None:
    m = re.search(pattern, text)
    if not m:
        return None
    try:
        return int(m.group(1))
    except Exception:
        return None


def _validate_docs_consistency(cfg: dict, skill_md_text: str, readme_text: str, errors: list[str]) -> None:
    for label, t in [("SKILL.md", skill_md_text), ("README.md", readme_text)]:
        if "reviewer_count" in t:
            errors.append(f"{label}: still mentions old parameter reviewer_count (should use panel_count)")
        if "thread_output_filename" in t:
            errors.append(f"{label}: still mentions old thread_output_filename (should use panel_output_filename)")
        if "--runner" in t:
            errors.append(f"{label}: still mentions old parallel-vibe flag --runner (should use --plan-file)")
        if "--workdir" in t:
            errors.append(f"{label}: mentions parallel-vibe --workdir (prefer --out-dir/--src-dir)")

    # parallel-vibe major updates: ensure SKILL.md documents the plan-file workflow.
    if "--plan-file" not in skill_md_text:
        errors.append("SKILL.md: missing parallel-vibe --plan-file workflow (required for parallel panels)")

    for label, t in [("SKILL.md", skill_md_text), ("README.md", readme_text)]:
        if "## 阶段判断（基于当前版本直接送审）" not in t:
            errors.append(f"{label}: missing default 函评/会评 stage assessment section")
        if "给过 / 不给过" not in t:
            errors.append(f"{label}: missing explicit binary verdict wording '给过 / 不给过'")
        if "资助额度" not in t:
            errors.append(f"{label}: missing funding-constraint guidance")

    pr = cfg.get("parallel_review") if isinstance(cfg, dict) else None
    pr = pr if isinstance(pr, dict) else {}
    expected_reviewer_count = len(pr.get("reviewer_personas") or []) if isinstance(pr.get("reviewer_personas"), list) else None
    expected_default_panels = pr.get("default_panel_count") if isinstance(pr.get("default_panel_count"), int) else None
    expected_max_panels = pr.get("max_panel_count") if isinstance(pr.get("max_panel_count"), int) else None

    readme_checks = [
        (r"每组专家：\s*(\d+)\s*位", expected_reviewer_count, "README.md: 每组专家数量与 config.yaml:parallel_review.reviewer_personas 不一致"),
        (r"总专家人次：N×\s*(\d+)\s*人次", expected_reviewer_count, "README.md: 总专家人次公式与每组专家数不一致"),
        (r"默认组数[^\n]*?(\d+)\s*组", expected_default_panels, "README.md: 默认组数与 config.yaml:parallel_review.default_panel_count 不一致"),
        (r"最大组数[^\n]*?(\d+)\s*组", expected_max_panels, "README.md: 最大组数与 config.yaml:parallel_review.max_panel_count 不一致"),
        (r"最多\s*(\d+)\s*组", expected_max_panels, "README.md: 最多组数与 config.yaml:parallel_review.max_panel_count 不一致"),
    ]
    for pattern, expected, message in readme_checks:
        if expected is None:
            continue
        found = _extract_doc_number(readme_text, pattern)
        if found is not None and found != expected:
            errors.append(f"{message}（文档={found}，配置={expected}）")


def _finish(errors: list[str]) -> int:
    if errors:
        print("FAIL")
        for e in errors:
            print(f"- {e}")
        return 1
    print("PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
