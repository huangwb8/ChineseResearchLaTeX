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
    _validate_parallel_review(cfg, skill_root, errors)
    _validate_scripts(skill_root, errors)
    _validate_references(skill_root, errors)
    _validate_docs_consistency(skill_md_text, _read_text(readme_path) if readme_path.exists() else "", errors)

    return _finish(errors)


def _validate_parallel_review(cfg: dict, skill_root: Path, errors: list[str]) -> None:
    pr = cfg.get("parallel_review") if isinstance(cfg, dict) else None
    if not isinstance(pr, dict):
        errors.append("config.yaml: missing parallel_review (dict)")
        return

    for k in ["default_panel_count", "max_panel_count", "panel_output_filename", "runner", "runner_profile", "timeout_seconds"]:
        if k not in pr:
            errors.append(f"config.yaml: parallel_review missing {k}")

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
    if not isinstance(personas, list) or len(personas) != 5:
        errors.append("config.yaml: parallel_review.reviewer_personas must be a list of 5 personas")
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


def _validate_docs_consistency(skill_md_text: str, readme_text: str, errors: list[str]) -> None:
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
