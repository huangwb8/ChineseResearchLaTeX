#!/usr/bin/env python3
from __future__ import annotations

import re
import sys
from pathlib import Path

from _yaml_utils import extract_yaml_list_under_block, extract_yaml_value_under_block


def _err(message: str) -> int:
    print(f"ERROR: {message}", file=sys.stderr)
    return 1


def _extract_frontmatter(text: str) -> str:
    if not text.startswith("---"):
        return ""
    parts = text.split("\n---\n", 1)
    if len(parts) != 2:
        return ""
    return parts[0]


def _extract_frontmatter_field(frontmatter: str, key: str) -> str | None:
    match = re.search(rf"(?m)^{re.escape(key)}:\s*(.+?)\s*$", frontmatter)
    if not match:
        return None
    return match.group(1).strip().strip('"').strip("'")


def main() -> int:
    skill_root = Path(__file__).resolve().parents[1]
    repo_root = skill_root.parents[1]
    skill_md = skill_root / "SKILL.md"
    config_yaml = skill_root / "config.yaml"
    templates_dir = skill_root / "templates"
    plans_dir = skill_root / "plans"
    tests_dir = skill_root / "tests"

    required_files = [
        skill_md,
        config_yaml,
        skill_root / "README.md",
        skill_root / "scripts" / "create_test_session.py",
        skill_root / "scripts" / "check_project_outputs.py",
        skill_root / "scripts" / "run_checks.py",
        skill_root / "scripts" / "_yaml_utils.py",
        skill_root / "references" / "info_form.md",
        skill_root / "references" / "dod_checklist.md",
        templates_dir / "OPTIMIZATION_PLAN_TEMPLATE.md",
        templates_dir / "B_ROUND_CHECK_TEMPLATE.md",
        templates_dir / "TEST_PLAN_TEMPLATE.md",
        templates_dir / "TEST_REPORT_TEMPLATE.md",
    ]
    for path in required_files:
        if not path.exists():
            return _err(f"missing required file: {path}")

    for d in [plans_dir, tests_dir, templates_dir]:
        if not d.exists() or not d.is_dir():
            return _err(f"missing required directory: {d}")

    skill_text = skill_md.read_text(encoding="utf-8")
    frontmatter = _extract_frontmatter(skill_text)
    if not frontmatter:
        return _err("SKILL.md missing YAML frontmatter block")

    fm_name = _extract_frontmatter_field(frontmatter, "name")
    fm_version = _extract_frontmatter_field(frontmatter, "version")
    fm_config = _extract_frontmatter_field(frontmatter, "config")
    fm_references = _extract_frontmatter_field(frontmatter, "references")
    if not fm_name or not fm_version or not fm_config or not fm_references:
        return _err("SKILL.md frontmatter missing required fields: name/version/config/references")

    fm_config_path = Path(fm_config)
    resolved_config_path = (
        (repo_root / fm_config_path) if str(fm_config_path).startswith("skills/") else (skill_root / fm_config_path)
    ).resolve()
    if resolved_config_path != config_yaml.resolve():
        return _err(f"config path mismatch: SKILL.md={resolved_config_path} expected={config_yaml.resolve()}")

    fm_refs_path = Path(fm_references)
    resolved_refs_path = (
        (repo_root / fm_refs_path) if str(fm_refs_path).startswith("skills/") else (skill_root / fm_refs_path)
    ).resolve()
    if not resolved_refs_path.exists() or not resolved_refs_path.is_dir():
        return _err(f"references path invalid: {resolved_refs_path}")

    config_lines = config_yaml.read_text(encoding="utf-8").splitlines()
    cfg_name = extract_yaml_value_under_block(config_lines, "skill_info", "name")
    cfg_version = extract_yaml_value_under_block(config_lines, "skill_info", "version")
    cfg_description = extract_yaml_value_under_block(config_lines, "skill_info", "description")
    cfg_category = extract_yaml_value_under_block(config_lines, "skill_info", "category")
    if not cfg_name or not cfg_version:
        return _err("config.yaml missing skill_info.name or skill_info.version")
    if not cfg_description or not cfg_category:
        return _err("config.yaml missing skill_info.description or skill_info.category")

    if fm_name != cfg_name:
        return _err(f"name mismatch: SKILL.md={fm_name} config.yaml={cfg_name}")
    if fm_version != cfg_version:
        return _err(f"version mismatch: SKILL.md={fm_version} config.yaml={cfg_version}")

    targets = [
        extract_yaml_value_under_block(config_lines, "targets", "research_content_tex"),
        extract_yaml_value_under_block(config_lines, "targets", "innovation_tex"),
        extract_yaml_value_under_block(config_lines, "targets", "yearly_plan_tex"),
    ]
    if any(t is None for t in targets):
        return _err("config.yaml missing one of targets.*_tex")

    allowed = extract_yaml_list_under_block(config_lines, "guardrails", "allowed_write_files")
    if not allowed:
        return _err("config.yaml missing guardrails.allowed_write_files")

    if set(allowed) != set(t for t in targets if t is not None):
        return _err("config.yaml mismatch: guardrails.allowed_write_files must equal targets.*_tex values")

    forbidden = extract_yaml_list_under_block(config_lines, "guardrails", "forbidden_write_files") or []
    for must_forbid in ["main.tex", "extraTex/@config.tex"]:
        if must_forbid not in forbidden:
            return _err(f"config.yaml missing guardrails.forbidden_write_files entry: {must_forbid}")

    forbidden_globs = extract_yaml_list_under_block(config_lines, "guardrails", "forbidden_write_globs") or []
    for must_forbid_glob in ["**/*.cls", "**/*.sty"]:
        if must_forbid_glob not in forbidden_globs:
            return _err(f"config.yaml missing guardrails.forbidden_write_globs entry: {must_forbid_glob}")

    required_skill_snippets = [
        "project_root",
        "output_mode",
        "写入安全约束",
        "references/output_skeletons.md",
        "main.tex",
        "extraTex/@config.tex",
        ".cls",
        ".sty",
    ]
    for snippet in required_skill_snippets:
        if snippet not in skill_text:
            return _err(f"SKILL.md missing required snippet: {snippet}")

    for t in targets:
        if t and t not in skill_text:
            return _err(f"SKILL.md missing target path from config.yaml: {t}")

    link_paths = re.findall(r"\((references/[^)]+)\)", skill_text)
    missing_links = []
    for rel in link_paths:
        if not (skill_root / rel).exists():
            missing_links.append(rel)
    if missing_links:
        missing = "\n".join(f"- {p}" for p in missing_links)
        return _err(f"SKILL.md contains missing references links:\n{missing}")

    stray = "（ 二）"
    readme_path = skill_root / "README.md"
    md_files = [skill_md, readme_path, *sorted((skill_root / "references").glob("*.md"))]
    for md in md_files:
        txt = md.read_text(encoding="utf-8")
        if stray in txt:
            return _err(f"found stray title variant '{stray}' in {md}")

    readme_text = readme_path.read_text(encoding="utf-8")
    for required_snippet in [
        "project_root",
        "output_mode",
        "禁止改动",
        "check_project_outputs.py",
        "run_checks.py",
        "--fail-on-risk-phrases",
    ]:
        if required_snippet not in readme_text:
            return _err(f"README.md missing required snippet: {required_snippet}")

    for required_path in [
        "skills/nsfc-research-content-writer/references/info_form.md",
        "skills/nsfc-research-content-writer/references/dod_checklist.md",
        "skills/nsfc-research-content-writer/references/output_skeletons.md",
    ]:
        if required_path not in readme_text:
            return _err(f"README.md missing required reference path: {required_path}")

    print("OK: validate-skill passed")
    print(f"- skill: {fm_name}")
    print(f"- version: {fm_version}")
    print(f"- referenced files: {len(link_paths)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
